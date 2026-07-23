"""
Cross-file retrieval for the review agent (Phase 3, Step B)
-----------------------------------------------------------
The diff says what changed and the full file says what it changed in the
context of — but neither shows a helper defined in *another* file. This module
indexes the repo's other source files and pulls back the few chunks most
related to the change.

Design choices, kept deliberately small:
- **Chroma, in-process.** No server, no separate container.
- **Fresh index per run.** No incremental sync infra to maintain or invalidate.
  For a repo of this size the rebuild is cheap.
- **Chunked by function/class**, not fixed line counts, so a retrieved chunk is
  a complete, readable unit. Each chunk carries its module preamble (imports
  and module-level constants) so it can be understood on its own — a validator
  is meaningless without the whitelist it checks against.
"""

import ast
import os
import threading

# chromadb's in-process client is NOT thread-safe: two threads constructing one
# concurrently race on its shared System registry and raise
# ("'RustBindingsAPI' object has no attribute 'bindings'" / KeyError 'ephemeral').
# One shared client, created and mutated under a lock, avoids it entirely.
_client = None
_client_lock = threading.Lock()

# Chunks are prefixed with their file's imports/constants so a retrieved
# function is self-contained. Capped so the preamble can't dominate.
MAX_PREAMBLE_CHARS = 600
MAX_CHUNK_CHARS = 4_000
MAX_INDEX_FILES = 40
MAX_SOURCE_CHARS = 100_000

EMBED_MODEL = "text-embedding-3-small"
DEFAULT_TOP_K = 3

INDEXABLE_EXTENSIONS = (".py",)


# ---------- Chunking ----------

def _module_preamble(tree, lines) -> str:
    """Imports and module-level assignments — the context a chunk needs."""
    parts = []
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign)):
            start = node.lineno
            end = getattr(node, "end_lineno", start) or start
            parts.append("\n".join(lines[start - 1:end]))
    preamble = "\n".join(parts)
    return preamble[:MAX_PREAMBLE_CHARS]


def chunk_source(path: str, source: str) -> list:
    """Split a source file into function/class chunks.

    Falls back to a single whole-file chunk for non-Python files and for
    Python that doesn't parse (a PR can legitimately contain broken syntax).
    """
    if not path.endswith(".py"):
        return [{"path": path, "start": 1, "text": source[:MAX_CHUNK_CHARS]}]

    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return [{"path": path, "start": 1, "text": source[:MAX_CHUNK_CHARS]}]

    lines = source.splitlines()
    preamble = _module_preamble(tree, lines)
    chunks = []

    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        start = node.lineno
        end = getattr(node, "end_lineno", start) or start
        body = "\n".join(lines[start - 1:end])
        text = f"{preamble}\n\n{body}" if preamble else body
        chunks.append({"path": path, "start": start, "text": text[:MAX_CHUNK_CHARS]})

    if not chunks:
        # Module with no functions/classes (e.g. a settings or constants file).
        chunks.append({"path": path, "start": 1, "text": source[:MAX_CHUNK_CHARS]})
    return chunks


# ---------- Index ----------

def build_index(sources: dict, collection_name: str = "repo"):
    """Embed the given {path: source} map into a fresh in-memory collection.

    Returns None if retrieval isn't usable (no sources, no API key, or chromadb
    unavailable) — retrieval is an enhancement and must never break a review.
    """
    if not sources:
        return None
    if not os.environ.get("OPENAI_API_KEY"):
        return None

    try:
        import chromadb
        from chromadb.config import Settings
        from chromadb.utils import embedding_functions
    except ImportError:
        print("  [info] chromadb not installed — skipping cross-file retrieval")
        return None

    chunks = []
    for path, source in sources.items():
        if not source or len(source) > MAX_SOURCE_CHARS:
            continue
        chunks.extend(chunk_source(path, source))
    if not chunks:
        return None

    global _client
    try:
        embedder = embedding_functions.OpenAIEmbeddingFunction(
            api_key=os.environ["OPENAI_API_KEY"], model_name=EMBED_MODEL
        )
        # Serialize client and collection setup — see the note on _client_lock.
        with _client_lock:
            if _client is None:
                # anonymized_telemetry off: a security tool should not phone home.
                _client = chromadb.EphemeralClient(Settings(anonymized_telemetry=False))
            try:
                _client.delete_collection(collection_name)
            except Exception:
                pass  # didn't exist; that's the normal case
            collection = _client.create_collection(
                name=collection_name, embedding_function=embedder
            )
            collection.add(
                ids=[f"{c['path']}:{c['start']}:{i}" for i, c in enumerate(chunks)],
                documents=[c["text"] for c in chunks],
                metadatas=[{"path": c["path"], "start": c["start"]} for c in chunks],
            )
    except Exception as e:
        print(f"  [info] could not build retrieval index ({e}) — continuing without it")
        return None

    return collection


def retrieve(collection, query_text: str, exclude_path: str = None,
             top_k: int = DEFAULT_TOP_K) -> list:
    """Top-k chunks related to `query_text`, excluding the file under review.

    The reviewed file is already supplied in full, so retrieving its own chunks
    would just burn tokens repeating it.
    """
    if collection is None or not query_text:
        return []
    try:
        # Over-fetch, then drop same-file chunks in Python — simpler and more
        # portable than relying on metadata filter syntax.
        raw = collection.query(query_texts=[query_text], n_results=top_k * 4)
    except Exception as e:
        print(f"  [info] retrieval query failed ({e}) — continuing without it")
        return []

    docs = (raw.get("documents") or [[]])[0]
    metas = (raw.get("metadatas") or [[]])[0]

    hits = []
    for doc, meta in zip(docs, metas):
        if exclude_path and meta.get("path") == exclude_path:
            continue
        hits.append({"path": meta.get("path"), "start": meta.get("start"), "text": doc})
        if len(hits) >= top_k:
            break
    return hits


# ---------- Collecting repo sources ----------

def collect_sources_from_github(repo, ref: str, skip_path: str = None,
                                limit: int = MAX_INDEX_FILES) -> dict:
    """Fetch indexable source files from the repo at a given commit."""
    try:
        tree = repo.get_git_tree(ref, recursive=True)
    except Exception as e:
        print(f"  [info] could not list repo tree ({e}) — skipping retrieval")
        return {}

    paths = [
        el.path for el in tree.tree
        if el.type == "blob"
        and el.path.endswith(INDEXABLE_EXTENSIONS)
        and el.path != skip_path
    ][:limit]

    sources = {}
    for path in paths:
        try:
            contents = repo.get_contents(path, ref=ref)
            sources[path] = contents.decoded_content.decode("utf-8")
        except Exception:
            continue  # binary, too large, or vanished — just skip it
    return sources
