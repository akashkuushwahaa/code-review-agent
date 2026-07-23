import subprocess

ALLOWED_FORMATS = ("png", "jpg", "webp")

def _validated_format(fmt):
    if fmt not in ALLOWED_FORMATS:
        raise ValueError("unsupported output format")
    return fmt

def probe(src):
    return subprocess.run(["identify", src], capture_output=True, check=True).stdout

def convert(src, fmt):
    safe_fmt = _validated_format(fmt)
    subprocess.run(["convert", src, f"out.{safe_fmt}"], check=True)
