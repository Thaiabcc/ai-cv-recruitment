const $ = (id) => document.getElementById(id);
let registering = false;
let busy = false;
function updateCompletion() {
  const inputs = [...$('profile-form').elements].filter((input) => input.name);
  const completed = inputs.filter((input) => input.value.trim()).length;
  $('completion-count').textContent = `${completed}/${inputs.length}`;
  $('completion-progress').max = inputs.length;
  $('completion-progress').value = completed;
}
function resetPasswordVisibility() {
  $('auth-form').elements.password.type = 'password';
  $('password-toggle').textContent = 'Hiện';
  $('password-toggle').setAttribute('aria-label', 'Hiện mật khẩu');
  $('password-toggle').setAttribute('aria-pressed', 'false');
}
$('password-toggle').addEventListener('click', () => {
  const input = $('auth-form').elements.password;
  const reveal = input.type === 'password';
  input.type = reveal ? 'text' : 'password';
  $('password-toggle').textContent = reveal ? 'Ẩn' : 'Hiện';
  $('password-toggle').setAttribute('aria-label', reveal ? 'Ẩn mật khẩu' : 'Hiện mật khẩu');
  $('password-toggle').setAttribute('aria-pressed', String(reveal));
});
$('profile-form').addEventListener('input', () => {
  updateCompletion();
  $('save-status').textContent = 'Có thay đổi chưa lưu';
});
const sectionObserver = new IntersectionObserver((entries) => {
  for (const entry of entries) {
    if (!entry.isIntersecting) continue;
    document.querySelectorAll('.section-link').forEach((link) => {
      const active = link.getAttribute('href') === `#${entry.target.id}`;
      link.classList.toggle('active', active);
      if (active) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    });
  }
}, { rootMargin: '-5% 0px -60% 0px' });
document.querySelectorAll('.form-card').forEach((card) => sectionObserver.observe(card));
async function api(path, options = {}) {
  const response = await fetch(`/api${path}`, {
    ...options, headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'cv-app' },
  });
  const data = response.status === 204 ? null : await response.json();
  if (!response.ok) {
    if (response.status === 401 && !path.startsWith('/auth/login')) showGuest();
    const error = new Error(typeof data?.detail === 'string' ? data.detail : 'Thông tin chưa hợp lệ. Kiểm tra email và độ dài các trường.');
    error.status = response.status;
    throw error;
  }
  return data;
}
function showGuest() {
  $('auth-section').hidden = false;
  $('account-section').hidden = true;
  $('profile-section').hidden = true;
  $('results').hidden = true;
  $('profile-form').reset();
  $('job-list').replaceChildren();
  $('save-status').textContent = '';
  $('account-email').textContent = '';
  updateCompletion();
  resetPasswordVisibility();
}
async function showAccount(user) {
  $('auth-section').hidden = true;
  $('account-section').hidden = false;
  $('profile-section').hidden = true;
  $('account-email').textContent = user.email;
  $('account-avatar').textContent = user.email.slice(0, 2).toUpperCase();
  $('profile-form').reset();
  const profile = await api('/profile');
  if (profile) {
    for (const input of $('profile-form').elements) {
      if (input.name && Object.hasOwn(profile, input.name)) input.value = profile[input.name];
    }
  }
  $('profile-section').hidden = false;
  updateCompletion();
  $('save-status').textContent = profile ? 'Đã tải hồ sơ đã lưu.' : 'Bạn chưa có hồ sơ. Hãy nhập và lưu thông tin.';
  $('message').textContent = '';
}
$('auth-switch').addEventListener('click', () => {
  registering = !registering;
  $('auth-title').textContent = registering ? 'Đăng ký tài khoản' : 'Đăng nhập';
  $('auth-description').textContent = registering ? 'Tạo tài khoản để bắt đầu xây dựng hồ sơ của riêng bạn.' : 'Tiếp tục xây dựng hồ sơ và lưu lại hành trình của bạn.';
  $('auth-submit').textContent = registering ? 'Đăng ký' : 'Đăng nhập';
  $('auth-switch').textContent = registering ? 'Đã có tài khoản? Đăng nhập' : 'Chưa có tài khoản? Đăng ký';
  $('auth-form').elements.password.autocomplete = registering ? 'new-password' : 'current-password';
  $('auth-form').elements.password.value = '';
  resetPasswordVisibility();
  $('message').textContent = '';
});
$('auth-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  if (busy) return;
  busy = true;
  $('auth-submit').disabled = $('auth-switch').disabled = true;
  $('message').textContent = 'Đang xử lý…';
  try {
    const values = Object.fromEntries(new FormData(event.target));
    values.email = values.email.trim();
    const user = await api(registering ? '/auth/register' : '/auth/login', { method: 'POST', body: JSON.stringify(values) });
    event.target.reset();
    resetPasswordVisibility();
    await showAccount(user);
  } catch (error) { $('message').textContent = error.message; }
  finally { busy = false; $('auth-submit').disabled = $('auth-switch').disabled = false; }
});
$('logout').addEventListener('click', async () => {
  $('logout').disabled = true;
  try { await api('/auth/logout', { method: 'POST' }); showGuest(); $('message').textContent = 'Đã đăng xuất.'; }
  catch (error) { $('message').textContent = error.message; }
  finally { $('logout').disabled = false; }
});
$('profile-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  $('save-button').disabled = true;
  $('save-status').textContent = 'Đang lưu…';
  try {
    await api('/profile', { method: 'PUT', body: JSON.stringify(Object.fromEntries(new FormData(event.target))) });
    $('save-status').textContent = 'Đã lưu hồ sơ thành công.';
  } catch (error) { $('save-status').textContent = error.message; }
  finally { $('save-button').disabled = false; }
});
$('preview-button').addEventListener('click', async () => {
  $('preview-button').disabled = true;
  try {
    const result = await api('/demo/recommendations');
    $('job-list').replaceChildren();
    for (const job of result.jobs) {
      const card = document.createElement('article');
      for (const [tag, value] of [['span', `Mức phù hợp minh họa: ${job.score}/100`], ['h3', job.title], ['p', job.company], ['p', `Đáp ứng: ${job.matched.join(', ')}`], ['p', `Còn thiếu / chưa rõ: ${job.missing.join(', ')}`], ['p', job.suggestion]]) {
        const element = document.createElement(tag); element.textContent = value; card.append(element);
      }
      $('job-list').append(card);
    }
    $('result-status').textContent = result.message;
    $('results').hidden = false;
    $('results').scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (error) { $('message').textContent = error.message; }
  finally { $('preview-button').disabled = false; }
});
(async () => {
  try { await showAccount(await api('/auth/me')); }
  catch (error) { showGuest(); $('message').textContent = error.status === 401 ? 'Đăng nhập hoặc đăng ký để lưu hồ sơ.' : error.message; }
  try { await api('/health'); $('status').textContent = 'Hệ thống đang hoạt động'; }
  catch { $('status').textContent = 'Không thể kết nối máy chủ.'; }
})();
