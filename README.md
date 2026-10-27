# AI CV Recruitment

Hệ thống AI hỗ trợ tạo hồ sơ ứng viên, tìm kiếm và đánh giá mức độ phù hợp với vị trí tuyển dụng. Đồ án triển khai theo kế hoạch 8 tuần.

**Tuần 5 đã chốt bàn giao ngày 28/10/2026 — tag `week-5`. Bước tiếp theo: tuần 6, kiểm thử tích hợp, đo chất lượng AI và tối ưu.**

## Đã triển khai

- Tuần 1: phân tích yêu cầu, kiến trúc, thiết kế database, khung FastAPI và giao diện minh họa.
- Tuần 2: đăng ký, đăng nhập, đăng xuất; băm mật khẩu Argon2; phiên đăng nhập trong database; nhập, xem, chỉnh sửa và lưu hồ sơ cá nhân.
- Hồ sơ gồm họ tên, điện thoại, địa chỉ, học vấn, kỹ năng, kinh nghiệm, dự án và nguyện vọng nghề nghiệp.
- Mỗi tài khoản chỉ truy cập hồ sơ của chính mình; tải lại trang hoặc đăng nhập lại vẫn đọc được dữ liệu đã lưu.

Đã có tạo/sửa CV bằng **Ollama local (`qwen2.5:7b`, ngữ cảnh 8192 token)**, lưu phiên bản, bốn mẫu PDF và xuất DOCX. Gemini giữ như lựa chọn chủ động qua cấu hình, không tự fallback lên cloud. PDF là đầu ra chính đã kiểm tra bố cục; DOCX là đầu ra bổ sung có thể chỉnh sửa.

Tuần 4 đã có **CareerViet và TopDev cho việc làm Việt Nam**, thêm Arbeitnow cho Đức/quốc tế; chuẩn hóa/loại trùng, lọc từ khóa và địa điểm, hàng đợi MySQL, worker và kết quả/lịch sử riêng từng tài khoản. Mặc định chọn hai nguồn Việt Nam; mỗi nguồn Việt Nam đọc tối đa 2 từ khóa, 6 tin chi tiết mỗi lượt. **Chưa lọc lương**. Tuần 5 bổ sung đánh giá/xếp hạng riêng bằng Ollama sau khi chọn lượt tìm đã hoàn thành. Phần minh họa cũ vẫn được gắn nhãn dữ liệu mẫu.

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
4. `database/week-4.sql` — bổ sung hàng đợi, liên kết tin theo lượt và bật nguồn Arbeitnow; chạy một lần.
5. `database/week-4-vietnam.sql` — thêm CareerViet/TopDev; có thể chạy lại, giữ trạng thái bật/tắt nguồn đã có.
6. `database/week-5.sql` — thêm lượt đánh giá, tiến độ và lịch sử nhiều phiên bản; chạy một lần sau tuần 4.

Nếu đã có database, chỉ chạy các migration còn thiếu theo thứ tự trên; bỏ qua migration đã áp dụng. Ứng dụng không tự chạy migration.

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
| 3 | AI tạo/chỉnh sửa CV, lưu phiên bản, xuất PDF/DOCX | Hoàn thành luồng CV/PDF chính bằng Ollama local; DOCX là tùy chọn |
| 4 | Khảo sát nguồn tuyển dụng, tìm/thu thập/chuẩn hóa dữ liệu, tác vụ nền | Hoàn thành phạm vi bàn giao: CareerViet/TopDev, Arbeitnow tùy chọn, worker, chọn nguồn và lịch sử; tag `week-4` |
| 5 | Đánh giá, giải thích, xếp hạng và lịch sử; hoàn thiện chức năng | Hoàn thành phạm vi chức năng; 62/62 ca MySQL/SQLite qua, đã thử Ollama thật; tag `week-5` |
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

## Ollama local và worker tìm việc

Cài/mở Ollama, tải model nếu chưa có: `ollama pull qwen2.5:7b`. Trong `.env`:

```dotenv
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_TIMEOUT_SECONDS=180
```

Ứng dụng dùng `/api/chat`, JSON schema, `num_ctx=8192`, `num_predict=3072`. Nội dung quá dài được từ chối có thông báo, không tự cắt dữ kiện. Ollama cần đang chạy trên chính máy chạy backend; không cần API key. Đổi `.env` cần khởi động lại ứng dụng.

Chạy `run.bat` cho web và **mở thêm `run-worker.bat`** cho tác vụ tìm việc. Worker không mở cổng HTTP. Dừng cả hai bằng Ctrl+C khi xong. Nếu chưa chạy worker, lượt tìm việc giữ trạng thái chờ; khởi động worker sẽ tiếp tục xử lý. Muốn xử lý một lượt rồi thoát: `run-worker.bat --once`.

Đăng nhập → lưu hồ sơ → tạo CV → ở phần **Tìm việc từ CV của bạn**, chọn CV, tùy chọn từ khóa/địa điểm rồi tìm. Mặc định chọn CareerViet và TopDev; có thể bật thêm Arbeitnow. Để trống địa điểm để tìm toàn nguồn; hỗ trợ Hà Nội/Hanoi, TP.HCM/Hồ Chí Minh, Đà Nẵng/Da Nang. Nhập `remote` chỉ lọc cờ remote được nguồn xác nhận, không bảo đảm được làm từ Việt Nam. TopCV đang trả 403 khi lấy tin trực tiếp; VietnamWorks chưa có adapter đọc đủ nội dung. Hai nguồn này chưa được bật. **Làm mới lịch sử** cũng cập nhật danh sách 30 CV mới nhất để chọn.

Chi tiết nguồn, giới hạn và kiểm thử: [tuần 4](docs/week-4.md). Database và `.env` vẫn phải chuyển riêng khi đổi máy.

## Đánh giá và xếp hạng tuần 5

Mở lịch sử tìm việc, chọn lượt đã hoàn thành có tin → **Đánh giá & xếp hạng bằng Ollama**. Dùng cùng `run-worker.bat`; mỗi tin được xử lý và lưu tiến độ riêng. Có thể dừng, xem lại lịch sử hoặc tạo lượt đánh giá mới mà không sửa kết quả cũ.

Dữ liệu dùng là hồ sơ/CV đã lưu ở lượt tìm, không tự lấy hồ sơ vừa chỉnh sau đó. Kỹ năng 50%, kinh nghiệm 30%, học vấn 20%; nhóm không có yêu cầu được bỏ và chuẩn hóa lại trọng số. Đầu ra nêu trích dẫn yêu cầu, bằng chứng, phần đáp ứng/một phần/chưa đủ thông tin và gợi ý. Điểm phản ánh bằng chứng, không phải xác suất trúng tuyển. AI trích xuất có thể sai; cần xem trích dẫn và tin gốc.

Xem [cách tính, API, kiểm thử và giới hạn tuần 5](docs/week-5.md). Nếu cập nhật từ tag week-4, áp dụng migration tuần 5 và khởi động lại web cùng worker; không chạy lại migration tuần 4 đã áp dụng.

Báo cáo kiểm thử tuần 5: [kết quả và lỗi trước/sau sửa](docs/week-5-test-report.md).
