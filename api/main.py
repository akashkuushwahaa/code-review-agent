"""Dashboard API — read-only views over the agent's findings + eval results.

No auth, no writes: a single-operator reporting surface (per Phase 7 scope).
Routes are sync `def` so FastAPI runs them in a threadpool, which keeps the
synchronous SQLite reads off the event loop.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from api import service
from api.config import settings
from api.schemas import EvalResponse, ReviewDetail, ReviewListResponse

app = FastAPI(title=settings.app_name, version=settings.app_version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/reviews", response_model=ReviewListResponse)
def list_reviews() -> ReviewListResponse:
    items = service.list_reviews()
    return ReviewListResponse(total=len(items), items=items)


# pr_url is a full URL (slashes + colon), so it's a query param rather than a
# path param — cleaner than URL-encoding it into the path.
@app.get("/api/reviews/detail", response_model=ReviewDetail)
def review_detail(pr_url: str = Query(..., description="Full PR URL")) -> ReviewDetail:
    detail = service.review_detail(pr_url)
    if detail is None:
        raise HTTPException(status_code=404, detail="No findings recorded for that PR")
    return detail


@app.get("/api/eval", response_model=EvalResponse)
def eval_results() -> EvalResponse:
    data = service.load_eval()
    if data is None:
        raise HTTPException(status_code=404, detail="No eval snapshot available")
    return data
