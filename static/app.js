async function checkServer() {
  const status = document.getElementById("status");
  try {
    const response = await fetch("/api/health");
    if (!response.ok) throw new Error("Server unavailable");
    const result = await response.json();
    status.textContent = result.status === "ok" ? "Máy chủ đang hoạt động · Bản tuần 1" : "Máy chủ chưa sẵn sàng.";
  } catch { status.textContent = "Không thể kết nối máy chủ. Hãy thử tải lại trang."; }
}
function appendText(parent, tag, value) {
  const element = document.createElement(tag);
  element.textContent = value;
  parent.append(element);
}
document.getElementById("profile-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const results = document.getElementById("results");
  const status = document.getElementById("result-status");
  const list = document.getElementById("job-list");
  const button = document.getElementById("preview-button");
  results.hidden = false;
  list.replaceChildren();
  button.disabled = true;
  status.textContent = "Đang tải ví dụ minh họa…";
  try {
    const response = await fetch("/api/demo/recommendations");
    if (!response.ok) throw new Error("Demo unavailable");
    const result = await response.json();
    for (const job of result.jobs) {
      const card = document.createElement("article");
      appendText(card, "span", `Mức phù hợp minh họa: ${job.score}/100`);
      appendText(card, "h3", job.title);
      appendText(card, "p", job.company);
      appendText(card, "p", `Đáp ứng: ${job.matched.join(", ")}`);
      appendText(card, "p", `Còn thiếu / chưa rõ: ${job.missing.join(", ")}`);
      appendText(card, "p", `Gợi ý: ${job.suggestion}`);
      appendText(card, "small", "Tin giả lập — chưa có link công việc thật.");
      list.append(card);
    }
    status.textContent = result.message;
  } catch { status.textContent = "Chưa tải được ví dụ. Hãy thử lại khi máy chủ hoạt động."; }
  finally { button.disabled = false; }
  results.scrollIntoView({ behavior: "smooth", block: "start" });
});
checkServer();
