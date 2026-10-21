const $ = (id) => document.getElementById(id);
let registering = false;
let busy = false;
let profileDirty = false;
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
  profileDirty = true;
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
  profileDirty = false;
  resetCVWorkspace();
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
  profileDirty = false;
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
  await loadCVWorkspace();
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
    profileDirty = false;
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

let cvSelected = null;
let cvNextBefore = null;
let cvDirty = false;
let cvTextDirty = false;
let cvDesign = { template_id: 'monochrome', photo_id: null };
let cvLastPhotoId = null;
let cvWorking = false;
let cvEpoch = 0;
const cvOrigins = { profile: 'Bản nháp từ hồ sơ', manual: 'Chỉnh sửa thủ công', gemini: 'Gemini biên soạn' };
function resetCVWorkspace() {
  clearPDFPreview();
  cvEpoch++;
  cvSelected = null; cvNextBefore = null; cvDirty = false;
  cvTextDirty = false;
  cvDesign = { template_id: 'monochrome', photo_id: null };
  cvLastPhotoId = null;
  $('cv-photo-file').value = '';
  $('cv-photo-status').textContent = '';
  updateDesignControls();
  $('cv-section').hidden = true;
  $('cv-detail').hidden = true;
  $('cv-empty').hidden = false;
  $('cv-version-list').replaceChildren();
  $('cv-preview').replaceChildren();
  $('cv-edit-form').reset();
  $('cv-instructions').value = '';
  $('cv-consent').checked = false;
  $('cv-status').textContent = '';
}
function cvDate(value) {
  return new Intl.DateTimeFormat('vi-VN', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(value));
}
function cvEditorDocument() {
  return Object.fromEntries(new FormData($('cv-edit-form')));
}
let cvPreviewTimer = null;
let cvPreviewController = null;
let cvPreviewSerial = 0;
function clearPDFPreview() {
  clearTimeout(cvPreviewTimer);
  cvPreviewController?.abort();
  cvPreviewSerial++;
}
function cvPreview(document) {
  clearPDFPreview();
  const epoch = cvEpoch;
  const serial = cvPreviewSerial;
  const design = { ...cvDesign };
  const container = $('cv-preview');
  container.replaceChildren();
  const status = window.document.createElement('p');
  status.className = 'preview-message';
  status.textContent = 'Đang dựng bản xem trước PDF…';
  container.append(status);
  cvPreviewTimer = setTimeout(async () => {
    cvPreviewController = new AbortController();
    try {
      const response = await fetch('/api/cvs/preview?representation=images', { method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'cv-app' },
        body: JSON.stringify({ document, design }), signal: cvPreviewController.signal });
      if (!response.ok) {
        const data = await response.json();
        throw new Error(typeof data.detail === 'string' ? data.detail : 'Kiểm tra nội dung để dựng bản xem trước.');
      }
      const data = await response.json();
      if (epoch !== cvEpoch || serial !== cvPreviewSerial) return;
      const note = window.document.createElement('p');
      note.className = 'pdf-preview-link';
      note.textContent = `Bản xem trước từ PDF thực tế · ${data.total_pages} trang`;
      container.replaceChildren(note);
      const appendPages = (result) => {
        for (const page of result.pages) {
          const image = window.document.createElement('img');
          image.src = `data:image/png;base64,${page.image}`;
          image.alt = `Trang ${page.number} của CV`; image.className = 'pdf-page-image';
          container.append(image);
        }
      };
      appendPages(data);
      let nextPage = data.next_page;
      const more = window.document.createElement('button');
      more.type = 'button'; more.className = 'secondary preview-more'; more.textContent = 'Xem thêm trang';
      more.hidden = nextPage === null;
      container.append(more);
      more.addEventListener('click', async () => {
        more.disabled = true;
        try {
          const response = await fetch(`/api/cvs/preview?representation=images&start_page=${nextPage}`, {
            method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'cv-app' },
            body: JSON.stringify({ document, design }) });
          if (!response.ok) throw new Error('Chưa tải được các trang tiếp theo.');
          const result = await response.json();
          if (epoch !== cvEpoch || serial !== cvPreviewSerial) return;
          more.remove(); appendPages(result); container.append(more);
          nextPage = result.next_page; more.hidden = nextPage === null;
        } catch (error) { $('cv-status').textContent = error.message; }
        finally { more.disabled = false; }
      });    } catch (error) {
      if (error.name !== 'AbortError' && epoch === cvEpoch && serial === cvPreviewSerial) status.textContent = error.message;
    }
  }, 500);
}function showCV(version) {
  cvSelected = version; cvDirty = false;
  cvTextDirty = false;
  cvDesign = { ...(version.design || { template_id: 'forest', photo_id: null }) };
  if (cvDesign.photo_id) cvLastPhotoId = cvDesign.photo_id;
  updateDesignControls();
  $('cv-empty').hidden = true;
  $('cv-detail').hidden = false;
  $('cv-version-title').textContent = `Bản #${version.id} · ${cvOrigins[version.origin] || version.origin}`;
  $('cv-editor-status').textContent = `Đã lưu lúc ${cvDate(version.created_at)}`;
  for (const input of $('cv-edit-form').elements) {
    if (input.name) input.value = version.document[input.name] || '';
  }
  cvPreview(version.document);
  document.querySelectorAll('.cv-version').forEach((button) => {
    const active = Number(button.dataset.cvId) === version.id;
    button.classList.toggle('active', active);
    button.setAttribute('aria-pressed', String(active));
  });
}
async function refreshCVList(append = false, epoch = cvEpoch) {
  const data = await api(`/cvs${append && cvNextBefore ? `?before_id=${cvNextBefore}` : ''}`);
  if (epoch !== cvEpoch) return;
  if (!append) $('cv-version-list').replaceChildren();
  for (const version of data.items) {
    const button = document.createElement('button');
    button.type = 'button'; button.className = 'cv-version'; button.dataset.cvId = version.id;
    button.setAttribute('aria-pressed', String(version.id === cvSelected?.id));
    button.classList.toggle('active', version.id === cvSelected?.id);
    const title = document.createElement('strong'); title.textContent = `#${version.id} · ${version.title || 'CV ứng viên'}`;
    const meta = document.createElement('span'); meta.textContent = `${cvOrigins[version.origin] || version.origin} · ${cvDate(version.created_at)}`;
    button.append(title, meta);
    button.addEventListener('click', () => runCV(async (epoch) => {
      if (!checkCVSaved()) return;
      const detail = await api(`/cvs/${version.id}`);
      if (epoch === cvEpoch) { showCV(detail); $('cv-status').textContent = ''; }
    }));
    $('cv-version-list').append(button);
  }
  cvNextBefore = data.next_before_id;
  $('cv-more').hidden = !cvNextBefore;
  if (!data.items.length && !append) {
    const hint = document.createElement('p'); hint.className = 'field-hint'; hint.textContent = 'Chưa có phiên bản nào.';
    $('cv-version-list').append(hint);
  }
  return data.items;
}
async function loadCVWorkspace() {
  resetCVWorkspace();
  const epoch = cvEpoch;
  $('cv-section').hidden = false;
  try {
    const status = await api('/cvs/status');
    if (epoch !== cvEpoch) return;
    $('cv-ai-status').textContent = status.ai_available ? 'Gemini đã được cấu hình. Bạn có thể nhờ AI biên soạn CV.' : 'Chưa cấu hình Gemini. Bạn vẫn có thể tạo bản nháp, chỉnh sửa và tải PDF/DOCX.';
    const items = await refreshCVList(false, epoch);
    if (epoch !== cvEpoch) return;
    if (items?.length) {
      const detail = await api(`/cvs/${items[0].id}`);
      if (epoch === cvEpoch) showCV(detail);
    }
  } catch (error) { if (epoch === cvEpoch) $('cv-status').textContent = error.message; }
}
function checkCVSaved() {
  if (cvDirty) { $('cv-status').textContent = 'Hãy lưu thành phiên bản mới hoặc bỏ thay đổi trước khi chọn bản khác, nhờ AI hay tải tài liệu.'; return false; }
  return true;
}
async function runCV(action) {
  if (cvWorking) return;
  cvWorking = true;
  const epoch = cvEpoch;
  const controls = [...$('cv-section').querySelectorAll('button, input, textarea, select')];
  controls.forEach((control) => { control.disabled = true; });
  try { await action(epoch); }
  catch (error) { if (epoch === cvEpoch) $('cv-status').textContent = error.message; }
  finally {
    cvWorking = false;
    controls.forEach((control) => { control.disabled = false; });
  }
}
async function createCV(path, body) {
  await runCV(async (epoch) => {
    if (cvTextDirty) { $('cv-status').textContent = 'Hãy lưu hoặc bỏ thay đổi nội dung CV trước khi tạo CV mới.'; return; }
    if (profileDirty) { $('cv-status').textContent = 'Hồ sơ có thay đổi chưa lưu. Hãy lưu hồ sơ phía trên trước khi tạo CV.'; return; }
    $('cv-status').textContent = path === '/draft' ? 'Đang tạo bản nháp…' : 'Gemini đang biên soạn, vui lòng chờ…';
    const version = await api(`/cvs${path}`, { method: 'POST', body: JSON.stringify({ ...body, design: cvDesign }) });
    if (epoch !== cvEpoch) return;
    showCV(version);
    await refreshCVList(false, epoch);
    if (epoch === cvEpoch) $('cv-status').textContent = 'Đã tạo và lưu phiên bản mới. Hãy kiểm tra nội dung trước khi sử dụng.';
  });
}
$('cv-draft').addEventListener('click', () => createCV('/draft'));
$('cv-generate').addEventListener('click', () => createCV('/generate', { instructions: $('cv-instructions').value, consent: $('cv-consent').checked }));
$('cv-refresh').addEventListener('click', () => runCV((epoch) => refreshCVList(false, epoch)));
$('cv-more').addEventListener('click', () => runCV((epoch) => refreshCVList(true, epoch)));
$('cv-edit-form').addEventListener('input', () => {
  if (!cvSelected) return;
  cvDirty = true;
  cvTextDirty = true;
  $('cv-editor-status').textContent = 'Bản xem trước có thay đổi chưa lưu';
  cvPreview(cvEditorDocument());
});
const discardCV = document.createElement('button');
discardCV.type = 'button'; discardCV.className = 'secondary'; discardCV.textContent = 'Bỏ thay đổi';
discardCV.addEventListener('click', () => { if (cvSelected) { showCV(cvSelected); $('cv-status').textContent = 'Đã khôi phục nội dung phiên bản đang chọn.'; } });
$('cv-save-version').parentElement.append(discardCV);
$('cv-edit-form').addEventListener('submit', (event) => {
  event.preventDefault();
  // Read values before disabling fields; disabled fields are omitted by FormData.
  const document = cvEditorDocument();
  const design = { ...cvDesign };
  runCV(async (epoch) => {
    if (!cvSelected) return;
    $('cv-status').textContent = 'Đang lưu phiên bản…';
    const version = await api(`/cvs/${cvSelected.id}/versions`, { method: 'POST', body: JSON.stringify({ document, design }) });
    if (epoch !== cvEpoch) return;
    showCV(version); await refreshCVList(false, epoch);
    if (epoch === cvEpoch) $('cv-status').textContent = 'Đã lưu phiên bản mới. Phiên bản cũ được giữ nguyên.';
  });
});
$('cv-revise').addEventListener('click', () => runCV(async (epoch) => {
  if (!cvSelected || !checkCVSaved()) return;
  const instructions = $('cv-instructions').value.trim();
  if (!instructions) { $('cv-status').textContent = 'Hãy nhập yêu cầu biên soạn ở đầu phần CV.'; return; }
  $('cv-status').textContent = 'Gemini đang chỉnh sửa bản đã lưu…';
  const version = await api(`/cvs/${cvSelected.id}/revise`, { method: 'POST', body: JSON.stringify({ instructions, consent: $('cv-consent').checked }) });
  if (epoch !== cvEpoch) return;
  showCV(version); await refreshCVList(false, epoch);
  if (epoch === cvEpoch) $('cv-status').textContent = 'Đã lưu bản AI chỉnh sửa. Hãy đọc lại trước khi sử dụng.';
}));
async function downloadCV(format) {
  await runCV(async (epoch) => {
    if (!cvSelected || !checkCVSaved()) return;
    $('cv-status').textContent = 'Đang chuẩn bị tài liệu…';
    const response = await fetch(`/api/cvs/${cvSelected.id}/export/${format}`);
    if (!response.ok) {
      const data = await response.json();
      if (response.status === 401) showGuest();
      throw new Error(data.detail || 'Chưa tải được tài liệu.');
    }
    const blob = await response.blob();
    if (epoch !== cvEpoch) return;
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a'); link.href = url; link.download = `cv-${cvSelected.id}.${format}`;
    document.body.append(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    $('cv-status').textContent = 'Đã tải tài liệu của phiên bản đang chọn.';
  });
}
$('cv-download-pdf').addEventListener('click', () => downloadCV('pdf'));
$('cv-download-docx').addEventListener('click', () => downloadCV('docx'));

function updateDesignControls() {
  document.querySelectorAll('input[name="cv-template"]').forEach((input) => { input.checked = input.value === ({ forest: 'monochrome', portrait: 'gradient' }[cvDesign.template_id] || cvDesign.template_id); });
  const portrait = !['forest', 'minimal'].includes(cvDesign.template_id);
  $('cv-photo-panel').hidden = !portrait;
  $('cv-photo-preview').hidden = !portrait || !cvDesign.photo_id;
  $('cv-remove-photo').hidden = !portrait || !cvDesign.photo_id;
  if (portrait && cvDesign.photo_id) $('cv-photo-preview').src = `/api/cvs/photos/${cvDesign.photo_id}`;
  else $('cv-photo-preview').removeAttribute('src');
  $('cv-save-design').hidden = !cvSelected;
}
function designChanged() {
  updateDesignControls();
  if (cvSelected) {
    cvDirty = true;
    $('cv-editor-status').textContent = 'Mẫu hoặc ảnh có thay đổi chưa lưu';
    cvPreview(cvEditorDocument());
  }
}
document.querySelectorAll('input[name="cv-template"]').forEach((input) => {
  input.addEventListener('change', () => {
    cvDesign = { template_id: input.value, photo_id: cvLastPhotoId };
    $('cv-photo-status').textContent = '';
    designChanged();
  });
});
$('cv-save-design').addEventListener('click', () => $('cv-edit-form').requestSubmit());
$('cv-remove-photo').addEventListener('click', () => {
  cvLastPhotoId = null;
  cvDesign = { ...cvDesign, photo_id: null };
  $('cv-photo-file').value = '';
  $('cv-photo-status').textContent = 'Đã bỏ ảnh khỏi bản đang chỉnh. Mẫu Lavender và Gradient cần chọn ảnh trước khi lưu.';
  designChanged();
});
$('cv-photo-file').addEventListener('change', () => {
  const file = $('cv-photo-file').files[0];
  if (!file) return;
  if (file.size > 3 * 1024 * 1024) {
    $('cv-photo-status').textContent = 'Ảnh vượt quá 3 MB. Hãy chọn ảnh nhỏ hơn.';
    $('cv-photo-file').value = '';
    return;
  }
  runCV(async (epoch) => {
    $('cv-photo-status').textContent = 'Đang xử lý và lưu ảnh…';
    const response = await fetch('/api/cvs/photos', {
      method: 'POST', headers: { 'X-Requested-With': 'cv-app', 'Content-Type': file.type || 'application/octet-stream' }, body: file,
    });
    const data = await response.json();
    if (!response.ok) {
      if (response.status === 401) showGuest();
      throw new Error(typeof data.detail === 'string' ? data.detail : 'Không tải được ảnh.');
    }
    if (epoch !== cvEpoch) return;
    cvLastPhotoId = data.id;
    cvDesign = { ...cvDesign, photo_id: data.id };
    // Use the saved document if controls are disabled during upload.
    updateDesignControls();
    if (cvSelected) {
      cvDirty = true;
      $('cv-editor-status').textContent = 'Ảnh mới chưa được lưu vào phiên bản CV';
      const document = Object.fromEntries([...$('cv-edit-form').elements].filter((input) => input.name).map((input) => [input.name, input.value]));
      cvPreview(document);
    }
    $('cv-photo-status').textContent = 'Đã lưu ảnh trong MySQL. Hãy tạo CV hoặc lưu mẫu & ảnh vào bản mới.';
    $('cv-photo-file').value = '';
  });
});

(async () => {
  try { await showAccount(await api('/auth/me')); }
  catch (error) { showGuest(); $('message').textContent = error.status === 401 ? 'Đăng nhập hoặc đăng ký để lưu hồ sơ.' : error.message; }
  try { await api('/health'); $('status').textContent = 'Hệ thống đang hoạt động'; }
  catch { $('status').textContent = 'Không thể kết nối máy chủ.'; }
})();
