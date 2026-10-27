# Tuần 5 — Đánh giá bằng chứng và xếp hạng công việc

**Đã chốt bàn giao phạm vi chức năng ngày 28/10/2026, tag `week-5`.** Các giới hạn chất lượng AI ở cuối tài liệu tiếp tục được kiểm chứng trong tuần 6.

## Phạm vi đã triển khai

Chọn lượt tìm việc hoàn thành → tạo lượt đánh giá → worker gọi Ollama local theo từng tin → kiểm tra trích dẫn → backend tính điểm → lưu và xếp hạng → xem lại lịch sử. Có tiến độ, dừng lượt, đánh giá lại bằng lượt mới và xử lý nguồn AI lỗi. Kết quả cũ không bị ghi đè.

Đây là công cụ gợi ý cho ứng viên, chưa phải rubric đã được hiệu chỉnh trên tập dữ liệu lớn hoặc quyết định tuyển dụng. Tuần 6 tiếp tục kiểm thử tích hợp, đo chất lượng và tối ưu.

## Dữ liệu và mô hình

- Chỉ dùng snapshot hồ sơ/CV và tin đã lưu tại lượt tìm. Sửa hồ sơ sau khi tìm không thay đổi cơ sở của các lượt đánh giá cũ; muốn dùng hồ sơ mới, tạo lượt tìm mới.
- Gửi bốn nhóm văn bản nghề nghiệp: học vấn, kỹ năng, kinh nghiệm, dự án. Không đưa trường họ tên, email, điện thoại, địa chỉ, ảnh hoặc giới tính vào payload. Nội dung nghề nghiệp là văn bản người dùng nhập, không phải dữ liệu đã được xác minh ngoài đời.
- Dùng Ollama trên localhost, model ghi theo từng lượt (mặc định `qwen2.5:7b`), ngữ cảnh 8192 token, đầu ra tối đa 3072 token, temperature 0. Không tự fallback lên cloud. CV vẫn có thể dùng provider khác nhưng chức năng đánh giá tuần 5 yêu cầu `AI_PROVIDER=ollama`.
- JSON schema giới hạn 12 tiêu chí mỗi tin. Ngân sách đầu vào bảo thủ là 12.000 byte UTF-8 gồm prompt và dữ liệu; quá dài trả lỗi riêng cho tin, không âm thầm cắt nội dung rồi chấm thiếu.
- API chính thức tham chiếu: [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs), [Chat API](https://docs.ollama.com/api/chat).

## Trích dẫn và kiểm tra

AI trả category, requirement_quote, status, evidence_field và candidate_quote. Backend kiểm tra schema, yêu cầu phải xuất hiện trong tin gốc và bằng chứng phải nằm trong đúng trường hồ sơ/CV. Chuẩn hóa Unicode, hoa/thường và khoảng trắng để đối chiếu; có kiểm tra ranh giới từ để không coi `Python` là `Pythonista`.

- Yêu cầu không khớp tin gốc: tin đánh giá thất bại, không tạo điểm.
- Bằng chứng không khớp hồ sơ: chuyển tiêu chí thành unknown, không cộng điểm.
- Lặp cùng đoạn yêu cầu: chỉ giữ một tiêu chí; phân loại mâu thuẫn giữa các bản lặp chuyển unknown.
- Không chấm tiêu chí chứa các yếu tố nhạy cảm đã nhận diện (giới tính, tuổi, dân tộc, tôn giáo, hôn nhân, khuyết tật…). Bộ nhận diện là bộ lọc quy tắc, không bảo đảm nhận biết mọi cách diễn đạt.
- Chưa thấy bằng chứng không được tự coi là unmet. Unmet cần trích dẫn phủ định rõ hoặc tổng số năm kinh nghiệm được khai báo rõ ràng thấp hơn yêu cầu; một công việc riêng lẻ không tự coi là tổng kinh nghiệm.
- Sinh viên đang học không được nhận điểm đáp ứng đầy đủ yêu cầu đã có bằng. Một công cụ không được coi là đáp ứng đầy đủ một danh sách nhiều công cụ đã nhận diện.
- Danh sách công nghệ không được dùng làm bằng chứng cho một số nhóm kỹ năng mềm đã nhận diện (tư duy hệ thống, giải quyết vấn đề, làm việc nhóm/độc lập, giao tiếp). Chỉ có bằng chứng một phần thì không nhận matched đầy đủ.
- Với câu yêu cầu kỹ năng cơ bản và tên công nghệ rõ ràng, backend có thể tìm lại trích dẫn trực tiếp trong trường kỹ năng để khắc phục AI bỏ sót. Không suy diễn kỹ năng từ tên dự án, không nâng thành trình độ chuyên sâu/số năm kinh nghiệm.

Kiểm tra trích dẫn xác nhận vị trí văn bản, không bảo đảm AI hiểu đúng ngữ nghĩa. Danh sách công nghệ/quy tắc chưa bao phủ mọi ngành nghề, điều kiện thay thế, chứng chỉ hoặc yêu cầu phức tạp; người dùng cần kiểm tra giải thích và tin gốc.

## Cách tính điểm evidence-v1

Trọng số gốc: kỹ năng 50%, kinh nghiệm 30%, học vấn 20%. Chỉ các nhóm có tiêu chí trích được mới tham gia mẫu số, trọng số được chuẩn hóa lại. Trong mỗi nhóm, các tiêu chí có trọng lượng bằng nhau.

| Trạng thái | Ý nghĩa | Điểm tiêu chí |
| --- | --- | --- |
| matched | Có bằng chứng đáp ứng | 1 |
| partial | Có bằng chứng đáp ứng một phần | 0,5 |
| unmet | Có bằng chứng rõ chưa đáp ứng | 0 |
| unknown | Chưa đủ thông tin để đối chiếu | Không cộng điểm, vẫn nằm trong mẫu số |

Điểm nhóm là trung bình điểm tiêu chí. Tổng điểm là tổng điểm nhóm nhân trọng số đã chuẩn hóa, quy đổi về 100. Đây là điểm từ bằng chứng có được, không phải xác suất trúng tuyển hay kết luận về toàn bộ năng lực ứng viên.

Độ bao phủ thông tin được tính bằng tỷ lệ tiêu chí khác unknown trong từng nhóm rồi áp dụng cùng trọng số. Nhóm/tin không có bằng chứng không được hiển thị 0 như thể đã xác định không đạt: tổng điểm để null, trạng thái insufficient. Không có yêu cầu trích được cũng không tạo điểm. Metadata giữ thêm cận trên khi các unknown được làm rõ, nhưng đây không phải dự đoán năng lực.

Ví dụ: kỹ năng đáp ứng toàn bộ, kinh nghiệm đáp ứng một phần, học vấn chưa rõ → điểm 65/100, độ bao phủ 80%. Nếu tin chỉ yêu cầu kỹ năng, nhóm kỹ năng có trọng số 100%.

Xếp hạng theo điểm giảm dần; đồng điểm ưu tiên độ bao phủ cao hơn, cuối cùng theo job_id để thứ tự ổn định. Tin chưa có điểm được đưa sau các tin có điểm và không gán thứ hạng số. Gợi ý cải thiện được dựng từ các yêu cầu partial/unmet/unknown, không bịa thành tích để thêm vào CV.

## Worker và lịch sử

Một tài khoản tối đa một lượt đánh giá queued/running, giãn cách 30 giây giữa hai lượt. Mỗi tin được commit riêng; API web không chờ AI. Dùng chung `run-worker.bat` với hàng đợi tìm việc. `--once` xử lý tối đa một lượt tìm và một lượt đánh giá rồi thoát.

Worker đánh dấu heartbeat và token sở hữu. Lượt running mất heartbeat trên 6 phút được đưa lại hàng đợi; một tin gián đoạn hai lần dừng thử lại. Token ngăn worker cũ ghi đè sau khi đã được thay thế hoặc sau khi người dùng dừng. Kết quả hoàn thành được giữ khi phục hồi; không chạy lại các tin đó.

JSON sai, hết token, trích dẫn sai hoặc timeout tạo kết quả failed với score null. Một số tin lỗi → partial, tất cả lỗi → failed. Ollama không sẵn sàng sẽ không lặp lại cùng request lỗi cho mọi tin còn lại. Insufficient là xử lý hợp lệ nhưng không đủ cơ sở tạo điểm, khác lỗi dịch vụ.

Dừng lượt giữ kết quả đã xong, đánh dấu các tin pending/running là cancelled; không ghi kết quả AI đến sau. Request Ollama đã gửi có thể tiếp tục đến khi trả về/timeout, nhưng worker không lưu kết quả đó và không đánh giá tin tiếp theo.

Mỗi lần đánh giá lại tạo batch mới với model, rubric_version và thời gian riêng. API lịch sử phân trang 20 lượt; kết quả chỉ đọc được bởi chủ sở hữu. Metadata kết quả lưu hash payload đầu vào. Bảng evaluations từ thiết kế tuần 1 được mở rộng để có batch_id; dữ liệu cũ batch_id null được giữ, không dùng để giả lập kết quả mới.

## Chạy và API

1. Áp dụng `database/week-5.sql` một lần sau các migration tuần 4. Máy hiện tại đã áp dụng.
2. Mở Ollama với model đã cấu hình; chạy lại `run.bat` và `run-worker.bat` để nạp code mới.
3. Mở lịch sử tìm việc, chọn lượt completed/partial có tin, bấm **Đánh giá & xếp hạng bằng Ollama**.
4. Xem tiến độ và trích dẫn; có thể dừng, mở lượt cũ hoặc tạo lượt mới.

| Phương thức | Endpoint | Chức năng |
| --- | --- | --- |
| POST | `/api/searches/{id}/evaluations` | Tạo lượt đánh giá, trả 202 |
| GET | `/api/searches/{id}/evaluations?before_id=...` | Lịch sử đánh giá của lượt tìm |
| GET | `/api/evaluations/{id}` | Tiến độ và danh sách đã xếp hạng |
| POST | `/api/evaluations/{id}/cancel` | Dừng lượt, giữ kết quả đã xong |

Mọi API kiểm tra chủ sở hữu; mutation dùng cơ chế chống yêu cầu khác nguồn sẵn có. Không nhận user_id, điểm số hoặc kết quả đánh giá từ trình duyệt.

Kết nối MySQL của ứng dụng đã đặt session time_zone UTC, đồng bộ với thời gian ứng dụng. Sửa lỗi session MySQL +07:00 khiến cooldown bị tính sai và thời gian TIMESTAMP bị hiển thị cộng thêm múi giờ. Không thay múi giờ toàn server MySQL; không dịch chuyển dữ liệu CV/hồ sơ/tìm việc đã lưu. Bảng batch mới dùng TIMESTAMP cho created_at.

## Nghiệm thu

- Bộ kiểm thử bao phủ quyền/CSRF, trọng số, unknown, trích dẫn giả, điều kiện nhạy cảm, suy diễn bằng cấp/kinh nghiệm/kỹ năng nhóm, đồng điểm, lịch sử/phân trang, dừng khi đang xử lý, lỗi Ollama và phục hồi worker. **62/62 ca qua trên MySQL và 62/62 ca qua trên SQLite** ở lần kiểm tra cuối; JavaScript hợp lệ và kiểm tra whitespace không có lỗi.
- Ollama thật đã đối chiếu hồ sơ giả với các tin kiểm thử và một tin CareerViet công khai. Các đầu ra sai phát hiện trong lượt thử đã dẫn tới bổ sung các kiểm tra bảo thủ phía backend, không phải bằng chứng mô hình luôn đúng.
- Luồng giao diện → worker → Ollama → MySQL với ba tin giả: 100/100, 33,33/100 và không tạo điểm cho tin chỉ có quyền lợi. Mở được trích dẫn yêu cầu/bằng chứng; reload vẫn giữ kết quả. Tạo lượt mới, dừng và mở lại lượt cũ thành công sau sửa UTC.
- Ảnh bên dưới dùng dữ liệu giả để kiểm thử, không phải tin tuyển dụng thật hoặc hồ sơ người dùng.

![Giải thích điểm và trích dẫn bằng chứng](week-5-evaluation.png)

## Giới hạn cần tiếp tục đánh giá ở tuần 6

Rubric và mức matched/partial do AI hỗ trợ vẫn cần hiệu chỉnh bằng tập mẫu có người chấm; chưa có số đo precision/recall, độ đúng ngữ nghĩa hoặc độ công bằng theo nhóm. Chưa xử lý chia đoạn cho hồ sơ/tin vượt ngân sách 8192; các trường hợp đó hiển thị lỗi không có điểm. Tối đa 12 tiêu chí có thể bỏ sót yêu cầu. Worker đánh giá tuần tự trong một batch, có thể chậm với nhiều tin; chưa kiểm tra tải lớn. Nguồn tuyển dụng vẫn theo giới hạn tuần 4. PDF là đầu ra CV chính, DOCX là tùy chọn bổ sung.

## Báo cáo kiểm thử ngày 28/10/2026

Đã chạy lại 62 ca trên MySQL và SQLite; phát hiện, sửa và kiểm tra hồi quy lỗi cộng điểm kỹ năng mềm từ danh sách công nghệ. Xem [báo cáo chi tiết](week-5-test-report.md) và [kết quả từng ca](week-5-test-results.json).

## Bàn giao

Bản bàn giao gồm API, worker, giao diện, migration `week-5.sql`, bộ kiểm thử, ảnh nghiệm thu và báo cáo có kết quả trước/sau sửa lỗi. Database máy hiện tại đã nâng cấp; máy khác cập nhật từ week-4 cần áp dụng migration tuần 5 và khởi động lại web/worker. `.env`, database và hồ sơ thật không nằm trong Git. Không để lại server kiểm thử chạy nền.
