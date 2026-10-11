async function checkServer() {
  const status = document.getElementById("status");
  try {
    const response = await fetch("/api/health");
    if (!response.ok) throw new Error("Server unavailable");
    const result = await response.json();
    status.textContent = result.status === "ok" ? "Máy chủ đang hoạt động." : "Máy chủ chưa sẵn sàng.";
  } catch {
    status.textContent = "Không thể kết nối máy chủ. Hãy thử tải lại trang.";
  }
}
checkServer();
