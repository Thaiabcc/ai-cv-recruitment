from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.config import ROOT_DIR, settings

app = FastAPI(title=settings.app_name, version="0.1.0-week1")
app.mount("/static", StaticFiles(directory=ROOT_DIR / "static"), name="static")

@app.get("/", include_in_schema=False)
def home():
    return FileResponse(ROOT_DIR / "static" / "index.html")

@app.get("/api/health", tags=["System"])
def health():
    """Application health only; does not check MySQL or Gemini."""
    return {"status": "ok", "app": settings.app_name, "version": "0.1.0-week1"}

@app.get("/api/demo/recommendations", tags=["Week 1 demo"])
def demo_recommendations():
    """Fictional fixed examples, no crawling or AI scoring."""
    jobs = [
        {"title": "Python Backend Intern", "company": "Công ty mẫu A", "score": 85,
         "matched": ["Python", "FastAPI", "MySQL"], "missing": ["Chưa có thông tin về Docker"],
         "suggestion": "Bổ sung dự án backend và cách sử dụng cơ sở dữ liệu."},
        {"title": "Junior Web Developer", "company": "Công ty mẫu B", "score": 72,
         "matched": ["HTML, CSS, JavaScript", "Git"], "missing": ["Chưa có thông tin về React"],
         "suggestion": "Bổ sung liên kết sản phẩm web và kết quả thực hiện."},
        {"title": "Data Intern", "company": "Công ty mẫu C", "score": 61,
         "matched": ["Python", "Pandas"], "missing": ["Chưa có thông tin về thống kê"],
         "suggestion": "Bổ sung dự án phân tích dữ liệu có biểu đồ và kết luận."},
    ]
    return {"demo": True, "message": "Dữ liệu và điểm minh họa cố định, không phải tin tuyển dụng thật.",
            "jobs": sorted(jobs, key=lambda job: job["score"], reverse=True)}
