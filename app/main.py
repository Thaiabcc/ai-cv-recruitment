from fastapi import FastAPI, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from app.accounts import router, current_user
from app.cvs import router as cv_router
from app.searches import router as search_router
from app.evaluations import router as evaluation_router
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.config import ROOT_DIR, settings

app = FastAPI(title=settings.app_name, version="0.5.0-week5")
app.include_router(router)
app.include_router(cv_router)
app.include_router(search_router)
app.include_router(evaluation_router)


@app.middleware('http')
async def private_responses(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, exc: SQLAlchemyError):
    return JSONResponse(status_code=503, content={'detail': 'Chưa thể truy cập cơ sở dữ liệu. Vui lòng thử lại sau.'})
app.mount("/static", StaticFiles(directory=ROOT_DIR / "static"), name="static")

@app.get("/", include_in_schema=False)
def home():
    return FileResponse(ROOT_DIR / "static" / "index.html")

@app.get("/api/health", tags=["System"])
def health():
    """Application health only; does not check MySQL or AI providers."""
    return {"status": "ok", "app": settings.app_name, "version": "0.5.0-week5"}

@app.get("/api/demo/recommendations", tags=["Demo"], dependencies=[Depends(current_user)])
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
