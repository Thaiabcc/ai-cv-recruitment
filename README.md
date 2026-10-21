# AI CV Recruitment

Hệ thống AI hỗ trợ tạo hồ sơ ứng viên, tìm kiếm và đánh giá mức độ phù hợp với vị trí tuyển dụng. Đồ án triển khai theo kế hoạch 8 tuần.

**Giai đoạn hiện tại: Tuần 3 — CV, Gemini và xuất PDF/DOCX; đang kiểm thử và nghiệm thu.**

## Đã triển khai

- Tuần 1: phân tích yêu cầu, kiến trúc, thiết kế database, khung FastAPI và giao diện minh họa.
- Tuần 2: đăng ký, đăng nhập, đăng xuất; băm mật khẩu Argon2; phiên đăng nhập trong database; nhập, xem, chỉnh sửa và lưu hồ sơ cá nhân.
- Hồ sơ gồm họ tên, điện thoại, địa chỉ, học vấn, kỹ năng, kinh nghiệm, dự án và nguyện vọng nghề nghiệp.
- Mỗi tài khoản chỉ truy cập hồ sơ của chính mình; tải lại trang hoặc đăng nhập lại vẫn đọc được dữ liệu đã lưu.

Đã bổ sung tạo bản nháp CV, tích hợp Gemini biên soạn/chỉnh sửa, lưu phiên bản và xuất PDF/DOCX. Đã cấu hình khóa và thử gọi Gemini, hiện Google trả lỗi 503 quá tải; DOCX còn chờ kiểm tra trực quan bằng Word/LibreOffice. Thu thập tin thật, chấm điểm phù hợp và lịch sử tìm việc **chưa triển khai**. Màn hình công việc hiện dùng dữ liệu mẫu cố định, yêu cầu đăng nhập.

## Cài đặt và chạy trên Windows

Python 3.10 trở lên, MySQL 8.0.16 trở lên (đã kiểm thử với MySQL 8.4.9).

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Điền thông tin kết nối MySQL trong `.env`. Không đưa mật khẩu, khóa API hoặc hồ sơ thực tế lên Git.

Với database mới, mở MySQL Workbench và chạy lần lượt:

1. `database/schema.sql` — tạo database và 7 bảng nghiệp vụ, chỉ chạy trên database phát triển mới.
2. `database/week-2.sql` — thêm bảng phiên đăng nhập; có thể chạy lại, giữ dữ liệu hiện có.
3. `database/week-3-photos.sql` — thêm bảng lưu ảnh chân dung trong MySQL.

Nếu đã có database tuần 1, chạy các migration tuần 2 và ảnh tuần 3; bỏ qua migration đã áp dụng. Ứng dụng không tự chạy migration.

```powershell
.\run.bat
```

- Giao diện: http://127.0.0.1:8001
- Tài liệu API: http://127.0.0.1:8001/docs
- Kiểm tra ứng dụng: http://127.0.0.1:8001/api/health (không xác nhận kết nối database).

Đăng ký bằng email và mật khẩu 8–128 ký tự; đăng ký thành công sẽ tự đăng nhập. Điền hồ sơ rồi chọn **Lưu hồ sơ**. Khi chạy qua HTTPS, cấu hình `COOKIE_SECURE=true`. Mặc định dùng HTTP cho localhost, thời hạn phiên `SESSION_HOURS=24`.

## API tuần 2

| Phương thức | Đường dẫn | Chức năng |
| --- | --- | --- |
| POST | `/api/auth/register` | Đăng ký và tạo phiên |
| POST | `/api/auth/login` | Đăng nhập |
| POST | `/api/auth/logout` | Xóa phiên ở server và cookie |
| GET | `/api/auth/me` | Tài khoản đang đăng nhập |
| GET | `/api/profile` | Hồ sơ của tài khoản hiện tại; `null` nếu chưa tạo |
| PUT | `/api/profile` | Tạo hoặc thay thế toàn bộ hồ sơ hiện tại |

Các yêu cầu thay đổi dữ liệu phải có header `X-Requested-With: cv-app`; Origin nếu có phải trùng nguồn. Khi thử API ngoài giao diện, cần giữ cookie giữa các yêu cầu và gửi header trên. API không cho truyền `user_id` để chọn chủ hồ sơ. Không bật CORS.

## Kiểm thử

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Mặc định dùng SQLite trong bộ nhớ, không tác động database dự án. Kiểm thử tích hợp trên MySQL đã áp dụng migration:

```powershell
$env:TEST_MYSQL='1'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
Remove-Item Env:TEST_MYSQL
```

Bộ kiểm thử MySQL dùng kết nối trong một giao dịch ngoài, các yêu cầu dùng savepoint; rollback sau mỗi ca để không lưu tài khoản và hồ sơ thử nghiệm. Bao phủ xác thực, trùng email, dữ liệu không hợp lệ, băm mật khẩu, cookie, chống yêu cầu khác nguồn, hết hạn phiên, đăng xuất, lưu/chỉnh sửa và tách biệt hai tài khoản. Chi tiết tại [tài liệu tuần 2](docs/week-2.md).

## Kế hoạch 8 tuần

| Tuần | Nội dung | Tiến độ |
| --- | --- | --- |
| 1 | Phân tích, thiết kế, nguyên mẫu | Hoàn thành, tag `week-1` |
| 2 | Tài khoản, phân quyền, lưu hồ sơ MySQL | Hoàn thành, đã nghiệm thu giao diện; tag `week-2` |
| 3 | Gemini tạo/chỉnh sửa CV, lưu phiên bản, xuất PDF/DOCX | Đã triển khai; chờ kiểm thử Gemini thật và kiểm tra trực quan DOCX |
| 4 | Khảo sát nguồn tuyển dụng, tìm/thu thập/chuẩn hóa dữ liệu, tác vụ nền | Chưa thực hiện |
| 5 | Đánh giá, giải thích, xếp hạng và lịch sử; hoàn thiện chức năng | Chưa thực hiện |
| 6 | Kiểm thử tích hợp, đánh giá chất lượng và tối ưu | Chưa thực hiện |
| 7 | Báo cáo và poster | Chưa thực hiện |
| 8 | Kiểm tra đạo văn, chỉnh sửa, slide và demo bảo vệ | Chưa thực hiện |

## Tài liệu và mã nguồn

- [Thiết kế tuần 1](docs/week-1.md)
- [Triển khai và kiểm thử tuần 2](docs/week-2.md)
- [Triển khai, cấu hình Gemini và kiểm thử tuần 3](docs/week-3.md)
- [Thiết kế database](database/schema.sql), [migration tuần 2](database/week-2.sql)
- `app/accounts.py`: xác thực và hồ sơ; `app/models.py`: ánh xạ database.
- `static/`: giao diện HTML/CSS/JavaScript; `tests/`: kiểm thử API.
- [Repository](https://github.com/Thaiabcc/ai-cv-recruitment), [mốc tuần 1](https://github.com/Thaiabcc/ai-cv-recruitment/tree/week-1), [mốc tuần 2](https://github.com/Thaiabcc/ai-cv-recruitment/tree/week-2).

Trước khi triển khai Internet cần bổ sung giới hạn thử đăng nhập ở ứng dụng/proxy, xác minh email và khôi phục mật khẩu; sử dụng tài khoản database có quyền giới hạn và HTTPS. Phiên bản hiện tại phục vụ phát triển và nghiệm thu đồ án trên localhost.
