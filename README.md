# AI CV Recruitment

Đồ án 9 tuần: xây dựng hệ thống AI hỗ trợ tạo lập hồ sơ ứng viên và tự động đánh giá mức độ phù hợp với vị trí tuyển dụng.

## Công nghệ

- Backend: Python, FastAPI.
- Giao diện: HTML, CSS, JavaScript.
- Cơ sở dữ liệu: MySQL.
- Dự kiến tích hợp: Google Gemini API, Pandas, web scraping, xuất PDF/DOCX.

## Trạng thái hiện tại

Đã có giao diện khởi đầu, API kiểm tra hoạt động và cấu hình kết nối MySQL. Chưa có chức năng tạo CV, đánh giá ứng viên, gọi Gemini, thu thập dữ liệu hoặc xuất tài liệu. API health chỉ kiểm tra ứng dụng, không kiểm tra kết nối MySQL/Gemini.

## Chạy trên Windows

Yêu cầu Python 3.11 trở lên. Mở terminal trong thư mục repo:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Mở http://127.0.0.1:8000 để xem giao diện hoặc http://127.0.0.1:8000/docs để xem API. Bộ khung có thể khởi động khi chưa cài MySQL và chưa có khóa Gemini.

## Cấu hình MySQL và Gemini

Khi triển khai chức năng lưu hồ sơ, cài MySQL và tạo database:

```sql
CREATE DATABASE ai_cv_recruitment CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Điền DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD và GEMINI_API_KEY trong `.env`. Dự án chưa có bảng dữ liệu hoặc migration; module `app/database.py` chuẩn bị kết nối và session cho bước phát triển tiếp theo.

Không đưa `.env`, khóa API, mật khẩu hoặc hồ sơ ứng viên thật lên GitHub. `.env.example` chỉ chứa cấu hình mẫu không có thông tin bí mật.

## Lộ trình dự kiến

1. Tuần 1: chốt yêu cầu, use case và mô hình dữ liệu.
2. Tuần 2: quản lý thông tin ứng viên.
3. Tuần 3: quản lý vị trí tuyển dụng và mô tả công việc.
4. Tuần 4: hỗ trợ tạo nội dung CV bằng Gemini.
5. Tuần 5: đối chiếu hồ sơ với yêu cầu tuyển dụng, giải thích kết quả.
6. Tuần 6: xuất PDF/DOCX.
7. Tuần 7: tích hợp xử lý và thu thập dữ liệu theo phạm vi đã chốt.
8. Tuần 8: kiểm thử và hoàn thiện giao diện.
9. Tuần 9: hoàn thiện báo cáo, demo và chuẩn bị bảo vệ.
