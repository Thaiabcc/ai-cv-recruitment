# AI CV Recruitment

Đồ án xây dựng hệ thống hỗ trợ ứng viên quản lý hồ sơ, tạo CV và tìm kiếm công việc. Hệ thống sử dụng mô hình ngôn ngữ chạy cục bộ để đối chiếu yêu cầu tuyển dụng với bằng chứng trong hồ sơ, giải thích kết quả và sắp xếp danh sách công việc.

## Chức năng

- Đăng ký, đăng nhập, đăng xuất; băm mật khẩu bằng Argon2 và quản lý phiên đăng nhập.
- Quản lý thông tin cá nhân, học vấn, kỹ năng, kinh nghiệm, dự án và nguyện vọng trên MySQL.
- Tạo, chỉnh sửa và lưu phiên bản CV; chọn mẫu trình bày và ảnh chân dung.
- Xem trước và xuất CV dạng PDF A4; hỗ trợ thêm DOCX để chỉnh sửa.
- Tìm tin từ CareerViet, TopDev và Arbeitnow; chuẩn hóa, loại trùng, lọc theo từ khóa và địa điểm.
- Đánh giá theo kỹ năng, kinh nghiệm, học vấn; trình bày trích dẫn, thông tin còn thiếu và gợi ý cải thiện hồ sơ.
- Xử lý tác vụ bằng worker, theo dõi tiến độ và lưu lịch sử riêng theo tài khoản.

Luồng sử dụng: **Tài khoản → Hồ sơ → CV → Tìm việc → Đánh giá → Xếp hạng và lịch sử**.

## Công nghệ và kiến trúc

| Thành phần | Công nghệ |
| --- | --- |
| Backend | Python, FastAPI, SQLAlchemy |
| Cơ sở dữ liệu | MySQL |
| Giao diện | HTML, CSS, JavaScript |
| Mô hình ngôn ngữ | Ollama, mặc định `qwen2.5:7b` |
| Xuất tài liệu | ReportLab, python-docx, PyMuPDF |
| Kiểm thử | unittest, FastAPI TestClient, MySQL và SQLite trong bộ nhớ |

Giao diện giao tiếp với FastAPI qua API sử dụng cookie phiên. Backend lưu hồ sơ, phiên bản CV, lượt tìm và kết quả đánh giá trong MySQL. Worker lấy tác vụ từ hàng đợi database, gọi nguồn tuyển dụng hoặc Ollama và lưu kết quả.

## Cài đặt

Yêu cầu: Python 3.10 trở lên, MySQL 8.0.16 trở lên và Ollama. Môi trường MySQL đã kiểm thử: phiên bản 8.4.9.

### Thiết lập Python

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Cấu hình kết nối MySQL trong `.env`. File này không được quản lý bằng Git; thông tin đăng nhập, khóa API và dữ liệu ứng viên không được đưa vào repository.

### Khởi tạo cơ sở dữ liệu

Với database mới, chạy các tập lệnh trong MySQL Workbench theo thứ tự:

1. `database/schema.sql` — cấu trúc dữ liệu ban đầu.
2. `database/week-2.sql` — phiên đăng nhập.
3. `database/week-3-photos.sql` — ảnh chân dung.
4. `database/week-4.sql` — hàng đợi tìm việc và liên kết kết quả.
5. `database/week-4-vietnam.sql` — nguồn tuyển dụng Việt Nam.
6. `database/week-5.sql` — lượt đánh giá và lịch sử kết quả.

Với database đã tồn tại, chỉ chạy các migration còn thiếu theo đúng thứ tự. Ứng dụng không tự động áp dụng migration. Khi chuyển môi trường, cần chuyển dữ liệu MySQL riêng nếu muốn giữ tài khoản và hồ sơ hiện có.

### Cấu hình Ollama

```powershell
ollama pull qwen2.5:7b
```

Ollama cần hoạt động trên máy chạy backend. Cấu hình mặc định trong `.env`:

```dotenv
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_TIMEOUT_SECONDS=180
```

Ứng dụng sử dụng ngữ cảnh 8192 token và đầu ra tối đa 3072 token. Nội dung vượt ngân sách được thông báo lỗi, không tự động cắt dữ kiện. Backend kiểm tra cấu trúc JSON trước khi lưu kết quả. Gemini là cấu hình tùy chọn cho chức năng CV; chức năng đánh giá hiện sử dụng Ollama local.

### Khởi động

Chạy web và worker trong hai terminal:

```powershell
.\run.bat
```

```powershell
.\run-worker.bat
```

- Giao diện: <http://127.0.0.1:8001>
- Tài liệu API: <http://127.0.0.1:8001/docs>
- Trạng thái ứng dụng: <http://127.0.0.1:8001/api/health>

Worker xử lý cả tìm việc và đánh giá; tác vụ giữ trạng thái chờ nếu worker chưa hoạt động. Dùng `Ctrl+C` để dừng. Sau khi cập nhật code hoặc cấu hình, cần khởi động lại web và worker.

## Sử dụng

1. Đăng ký hoặc đăng nhập, nhập và lưu hồ sơ.
2. Tạo bản nháp hoặc sử dụng AI biên soạn CV; kiểm tra nội dung, chọn mẫu và lưu phiên bản.
3. Xuất PDF từ phiên bản đã lưu.
4. Chọn CV, nguồn tuyển dụng và bộ lọc để tìm việc. CareerViet và TopDev được ưu tiên mặc định.
5. Mở lượt tìm đã hoàn thành, chọn **Đánh giá & xếp hạng bằng Ollama**.
6. Xem điểm, trích dẫn, bằng chứng và thông tin còn thiếu; truy cập tin gốc hoặc mở lại lịch sử.

Đánh giá sử dụng hồ sơ/CV được lưu tại thời điểm tạo lượt tìm. Mỗi lượt đánh giá mới được lưu riêng để bảo toàn kết quả trước đó.

## Phương pháp đánh giá và giới hạn

Trọng số ban đầu: kỹ năng 50%, kinh nghiệm 30%, học vấn 20%. Nhóm không có yêu cầu được bỏ và phân bổ lại trọng số. Tiêu chí được phân loại thành đáp ứng, đáp ứng một phần, chưa đáp ứng có bằng chứng hoặc chưa đủ thông tin. Backend kiểm tra trích dẫn và tính điểm; AI không trực tiếp quyết định điểm số.

Điểm phản ánh bằng chứng trong dữ liệu đã cung cấp, không phải xác suất trúng tuyển. Trích dẫn đúng vị trí chưa bảo đảm AI hiểu đúng ngữ nghĩa. Rubric cần tiếp tục được hiệu chỉnh trên tập mẫu có người chấm.

- Mỗi nguồn Việt Nam hiện xử lý tối đa hai từ khóa và sáu tin chi tiết mỗi lượt. Chưa tích hợp TopCV/VietnamWorks và chưa lọc mức lương.
- Tối đa 12 tiêu chí đánh giá mỗi tin; chưa hỗ trợ chia đoạn cho nội dung vượt ngân sách ngữ cảnh.
- Worker đánh giá tuần tự trong một lượt; chưa đánh giá tải lớn hoặc chất lượng trên tập dữ liệu quy mô lớn.
- PDF là đầu ra CV chính. DOCX là định dạng bổ sung; bố cục có thể khác PDF và phụ thuộc phần mềm mở tài liệu.

## Kiểm thử

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Mặc định sử dụng SQLite trong bộ nhớ cho kiểm thử độc lập. Kiểm thử tích hợp trên MySQL yêu cầu database đã áp dụng các migration:

```powershell
$env:TEST_MYSQL='1'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
Remove-Item Env:TEST_MYSQL
```

Kết quả kiểm thử tuần 5: **62/62 ca trên MySQL và 62/62 ca trên SQLite**, bao gồm 22 ca trực tiếp cho chức năng đánh giá và 40 ca hồi quy. Các kiểm thử MySQL sử dụng giao dịch/savepoint và rollback dữ liệu thử nghiệm. Kết quả này xác nhận các tình huống chức năng đã kiểm tra, không đại diện cho độ chính xác tổng quát của AI.

Chi tiết: [báo cáo kiểm thử](docs/week-5-test-report.md), [số liệu từng ca](docs/week-5-test-results.json).

## Cấu trúc mã nguồn

| Thư mục hoặc module | Nội dung |
| --- | --- |
| `app/accounts.py`, `app/models.py` | Tài khoản, hồ sơ và ánh xạ dữ liệu |
| `app/cvs.py`, `app/cv_export.py`, `app/cv_templates.py` | Phiên bản CV, xem trước và xuất tài liệu |
| `app/ai.py`, `app/gemini.py` | Tích hợp mô hình cho chức năng CV |
| `app/searches.py`, `app/job_sources.py`, `app/vietnam_sources.py` | Tìm kiếm và chuẩn hóa tin |
| `app/evaluations.py`, `app/evaluation_ai.py`, `app/evaluation_worker.py` | Đánh giá bằng chứng, điểm và lịch sử |
| `app/worker.py` | Tiến trình xử lý tác vụ nền |
| `database/`, `static/`, `tests/`, `docs/` | Migration, giao diện, kiểm thử và tài liệu |

## Kế hoạch thực hiện

| Tuần | Nội dung | Trạng thái |
| --- | --- | --- |
| 1 | Phân tích yêu cầu, thiết kế, nguyên mẫu | Đã thực hiện |
| 2 | Tài khoản, phân quyền, hồ sơ MySQL | Đã triển khai và kiểm thử |
| 3 | Tạo/chỉnh sửa CV, lưu phiên bản, xuất tài liệu | Đã triển khai và kiểm thử luồng PDF chính |
| 4 | Thu thập, chuẩn hóa tin tuyển dụng và tác vụ nền | Đã triển khai trong phạm vi nguồn và giới hạn nêu trên |
| 5 | Đánh giá, giải thích, xếp hạng và lịch sử | Đã triển khai và kiểm thử chức năng |
| 6 | Kiểm thử tích hợp, đo chất lượng và tối ưu | Kế hoạch tiếp theo |
| 7 | Báo cáo và poster | Kế hoạch |
| 8 | Rà soát báo cáo, chuẩn bị slide và trình diễn | Kế hoạch |

## Tài liệu kỹ thuật

- [Phân tích và thiết kế](docs/week-1.md)
- [Tài khoản và hồ sơ](docs/week-2.md)
- [CV và xuất tài liệu](docs/week-3.md)
- [Nguồn tuyển dụng và tìm việc](docs/week-4.md)
- [Đánh giá và xếp hạng](docs/week-5.md)

Phiên bản hiện tại phục vụ phát triển và đánh giá đồ án trên localhost. Triển khai công khai cần bổ sung HTTPS, tài khoản database có quyền giới hạn, giới hạn thử đăng nhập, xác minh email và khôi phục mật khẩu.
