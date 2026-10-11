# AI CV Recruitment — Week 1

Đồ án 9 tuần: hệ thống AI hỗ trợ tạo lập hồ sơ ứng viên, tự động tìm kiếm và đánh giá mức độ phù hợp với vị trí tuyển dụng.

## Luồng đã chốt

Đăng ký/đăng nhập → nhập hồ sơ và mong muốn công việc → AI hỗ trợ tạo CV → tự tìm tin từ các nguồn cấu hình sẵn → đối chiếu yêu cầu → xếp hạng công việc. Kết quả gồm link tin gốc, mức độ phù hợp, điểm đáp ứng, điểm thiếu/chưa rõ và gợi ý cải thiện.

Chức năng nền: đăng xuất, quản lý/chỉnh sửa hồ sơ, xuất PDF/DOCX, lưu lịch sử. Người dùng không phải nhập link hay mô tả công việc.

## Bản tuần 1 có gì?

- Giao diện nhập hồ sơ và xem kết quả giả lập, có nhãn minh họa.
- API /api/health và /api/demo/recommendations.
- Thiết kế yêu cầu, kiến trúc, use case tại [docs/week-1.md](docs/week-1.md).
- Thiết kế SQL tại [database/schema.sql](database/schema.sql).
- FastAPI, cấu hình MySQL/Gemini và lệnh khởi động ngắn.

Thông tin nhập trong demo không được gửi/lưu. Điểm cố định, công việc hư cấu, không có link tin thật. Chưa có đăng nhập thật, tạo CV, kết nối tuyển dụng, gọi Gemini hoặc xuất tài liệu. Health chỉ kiểm tra ứng dụng, không kiểm tra MySQL/Gemini.

## Chạy trên Windows

Yêu cầu Python 3.11+. Lần đầu, trong thư mục repo:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Nếu đã cài trên máy thì chỉ cần:

```powershell
.\run.bat
```

Mở http://127.0.0.1:8000 và http://127.0.0.1:8000/docs. Dừng bằng Ctrl+C. Nếu cổng bận: `.\run.bat --port 8001`, rồi mở http://127.0.0.1:8001.

Bản tuần 1 chạy được khi chưa có MySQL hoặc khóa Gemini. Khi phát triển lưu dữ liệu, điền cấu hình DB trong .env và áp dụng schema.sql vào database phát triển mới. Script này là thiết kế khởi tạo, chưa phải migration và không được ứng dụng tự chạy. Chưa kiểm tra schema trên MySQL thật.

Không commit .env, mật khẩu, khóa API hoặc hồ sơ thật.

## Công nghệ

Python/FastAPI; HTML/CSS/JavaScript; MySQL; dự kiến Gemini API, Pandas, web scraping và xuất PDF/DOCX. TopCV là nguồn dự kiến, chưa kết nối; nguồn thực tế phải được xác minh khả năng truy cập dữ liệu trước khi tích hợp.

## Kế hoạch 9 tuần

1. Tuần 1: chốt yêu cầu, use case, dữ liệu, kiến trúc và giao diện minh họa.
2. Tuần 2: đăng ký/đăng nhập/đăng xuất, quyền truy cập và lưu hồ sơ MySQL.
3. Tuần 3: tích hợp Gemini để hỗ trợ tạo/chỉnh sửa CV, lưu phiên bản.
4. Tuần 4: khảo sát và tích hợp nguồn tuyển dụng, tìm tin từ hồ sơ.
5. Tuần 5: chuẩn hóa, loại trùng, worker và xử lý lỗi nguồn.
6. Tuần 6: đối chiếu, tính điểm có bằng chứng, xếp hạng và lịch sử.
7. Tuần 7: xuất PDF/DOCX và hoàn thiện luồng tự động.
8. Tuần 8: kiểm thử tích hợp, đánh giá chất lượng và hoàn thiện giao diện.
9. Tuần 9: báo cáo, demo và chuẩn bị bảo vệ.
