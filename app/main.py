from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import ROOT_DIR, settings

app = FastAPI(title=settings.app_name, version="0.1.0")
app.mount("/static", StaticFiles(directory=ROOT_DIR / "static"), name="static")


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(ROOT_DIR / "static" / "index.html")


@app.get("/api/health", tags=["System"])
def health():
    """Check application availability; does not test MySQL or Gemini connectivity."""
    return {"status": "ok", "app": settings.app_name, "version": "0.1.0"}
