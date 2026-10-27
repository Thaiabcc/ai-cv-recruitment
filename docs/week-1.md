# Yêu cầu và thiết kế — Tuần 1

## Mục tiêu

Xây dựng hệ thống AI hỗ trợ tạo lập hồ sơ ứng viên, tự động tìm kiếm và đánh giá mức độ phù hợp với các vị trí tuyển dụng. Thời gian: 8 tuần. Hoàn thành các chức năng trong tuần 5; tuần 6 kiểm thử và tối ưu; tuần 7 hoàn thiện báo cáo đồ án và poster; tuần 8 kiểm tra đạo văn, chỉnh sửa và chuẩn bị slide, demo bảo vệ. Kế hoạch chi tiết được cập nhật trong README.md.

## Phạm vi chức năng

Người dùng đăng ký/đăng nhập, nhập học vấn, kỹ năng, kinh nghiệm, dự án và mong muốn về vị trí, địa điểm, lương. Hệ thống hỗ trợ tạo CV, tự tìm tin từ danh sách nguồn tuyển dụng cấu hình sẵn, đọc yêu cầu, đối chiếu và xếp hạng. Người dùng không phải nhập link hoặc mô tả công việc.

Kết quả mỗi công việc gồm tên vị trí, công ty, link tin gốc, mức độ phù hợp, yêu cầu đáp ứng, yêu cầu còn thiếu/chưa rõ, giải thích và gợi ý cải thiện. Có chỉnh sửa hồ sơ, xuất PDF/DOCX và lịch sử kết quả.

## Use case

| Vai trò | Chức năng |
|---|---|
| Khách | Đăng ký, đăng nhập |
| Ứng viên | Đăng xuất; quản lý hồ sơ; tạo/chỉnh sửa/xuất CV; bắt đầu tìm việc; xem tiến độ, kết quả và lịch sử |
| Quản trị viên | Quản lý nguồn tuyển dụng, bật/tắt nguồn và xem lỗi thu thập |

Quản trị viên là lựa chọn thiết kế để quản lý nguồn; giao diện quản trị có thể giản lược nếu thời gian hạn chế.

## Luồng xử lý dự kiến

1. Xác thực và kiểm tra hồ sơ đủ thông tin để tìm việc.
2. Tạo phiên bản CV; cho người dùng kiểm tra nội dung, không tự thêm kinh nghiệm không có trong hồ sơ.
3. Tạo lượt tìm việc và lưu ảnh chụp hồ sơ/CV tại thời điểm chạy.
4. Sinh từ khóa tìm kiếm từ kỹ năng và vị trí mong muốn; áp dụng bộ lọc địa điểm/lương khi nguồn hỗ trợ.
5. Gọi adapter của từng nguồn được bật; lấy link tin và nội dung công việc, chuẩn hóa và loại trùng.
6. Đối chiếu từng yêu cầu với bằng chứng trong hồ sơ, lưu kết quả.
7. Xếp hạng điểm giảm dần, dùng mức bao phủ thông tin làm tiêu chí phụ khi đồng điểm.
8. Hiển thị kết quả, link gốc, giải thích, gợi ý và trạng thái các nguồn.

Nếu một nguồn lỗi, tiếp tục các nguồn còn lại và hiển thị lượt tìm kiếm chưa đầy đủ. Không tìm thấy tin thì hiển thị trạng thái rỗng. Không tạo điểm khi không đọc được yêu cầu. Có trạng thái queued/running/completed/partial/failed và retry có giới hạn. Thu thập và AI sẽ chạy trong worker để không khóa yêu cầu web.

## Nguồn tuyển dụng

TopCV là nguồn dự kiến đầu tiên, chưa tích hợp. Chọn thêm nguồn sau khi kiểm tra cơ chế truy cập, điều kiện sử dụng, robots và khả năng lấy nội dung. Ưu tiên API hoặc dữ liệu được phép truy cập; không cam kết mọi trang đều có thể thu thập. Không vượt CAPTCHA hoặc đăng nhập bắt buộc. Adapter tách riêng theo nguồn; cấu hình giới hạn tốc độ, timeout và cache. Chỉ xử lý URL từ nguồn được cho phép, kiểm tra chuyển hướng để tránh truy cập mạng nội bộ.

## Đánh giá dự kiến

Rubric ban đầu: kỹ năng 50%, kinh nghiệm 30%, học vấn 20%; cần hiệu chỉnh bằng tập hồ sơ/tin mẫu. Từng tiêu chí có trạng thái đáp ứng, đáp ứng một phần, chưa đáp ứng hoặc chưa đủ thông tin. Phân biệt không thấy bằng chứng với thực sự không đạt. Nếu tin không nêu một nhóm tiêu chí, bỏ nhóm đó và chuẩn hóa trọng số còn lại. Nếu thiếu bằng chứng, hiển thị độ đầy đủ thông tin, không khẳng định ứng viên không có kỹ năng.

AI trích xuất yêu cầu, bằng chứng và gợi ý theo cấu trúc JSON; backend xác thực kết quả và tính điểm theo rubric để có thể kiểm tra lại. Không dùng giới tính, tuổi, dân tộc, tôn giáo hoặc thông tin cá nhân không liên quan để tính điểm. Kết quả phục vụ gợi ý cho ứng viên, không tự quyết định tuyển dụng. Rubric trên là đề xuất thiết kế, chưa triển khai hay được xác nhận chất lượng.

## Kiến trúc

HTML/CSS/JavaScript → FastAPI → dịch vụ hồ sơ/CV/tìm việc/đánh giá → MySQL. Worker gọi adapter nguồn tuyển dụng và Gemini. Pandas hỗ trợ chuẩn hóa, phân tích dữ liệu; module riêng xuất PDF/DOCX.

API dự kiến: /api/auth/register, /api/auth/login, /api/auth/logout; /api/profile; /api/cvs; /api/search-runs; /api/search-runs/{id}/results; /api/cvs/{id}/export. Định nghĩa này là thiết kế, chưa phải endpoint hoạt động.

Mật khẩu phải được băm; phiên đăng nhập có thời hạn, cookie HttpOnly, Secure khi triển khai HTTPS và bảo vệ CSRF nếu dùng cookie. Mọi hồ sơ, CV, lượt tìm kiếm phải kiểm tra quyền sở hữu. Không ghi khóa API hoặc toàn bộ hồ sơ vào log. Khóa Gemini chỉ nằm ở backend.

## Mô hình dữ liệu

- users: tài khoản, email duy nhất, password_hash.
- profiles: hồ sơ thuộc một user, học vấn/kỹ năng/kinh nghiệm/dự án và mong muốn.
- cvs: phiên bản CV và ảnh chụp hồ sơ, thuộc user.
- recruitment_sources: nguồn, tên miền, trạng thái bật/tắt; tuần 1 chưa bật nguồn thật.
- jobs: tin chuẩn hóa, URL, yêu cầu, thời điểm lấy dữ liệu; URL được loại trùng bằng SHA-256.
- search_runs: lượt chạy, CV được sử dụng, trạng thái, thông tin nguồn lỗi.
- evaluations: kết quả cho từng job trong mỗi lượt, điểm, rubric, bằng chứng, thiếu sót và gợi ý.

Quan hệ: users 1–1 profiles; users 1–N cvs/search_runs; recruitment_sources 1–N jobs; search_runs N–N jobs qua evaluations. Xem database/schema.sql. JSON dùng cho danh sách thông tin và snapshots trong giai đoạn đầu; có thể tách bảng khi yêu cầu truy vấn mở rộng.

## Tiêu chí nghiệm thu tuần 1

- Xác định luồng nghiệp vụ, chức năng tài khoản và dữ liệu cần lưu.
- Có thiết kế cơ sở dữ liệu, kiến trúc và kế hoạch 8 tuần.
- Giao diện chạy được, có form hồ sơ và kết quả minh họa sắp xếp giảm dần.
- API health và demo hoạt động; giao diện thể hiện rõ giới hạn demo.
- Chạy bằng run.bat; cấu hình bí mật không được đưa lên Git.

Tuần 1 chưa triển khai xác thực, lưu hồ sơ, tìm tin thật, AI hoặc xuất CV.
