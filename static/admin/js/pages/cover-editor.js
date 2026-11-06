import {api} from '../core.js';
const form = document.getElementById('coverForm');
if (form) {
  const endpoint = '/api/covers/videos/' + encodeURIComponent(document.getElementById('videoDetail').dataset.videoId);
  const title = document.getElementById('coverTitle');
  const timestamp = document.getElementById('coverTimestamp');
  const focusX = document.getElementById('coverFocusX'), focusY = document.getElementById('coverFocusY');
  const message = document.getElementById('coverMessage');
  const controls = [...form.querySelectorAll('button,input')];
  let ready = false, loaded = false, busy = false;
  function show(cover) {
    title.value = cover.title;
    timestamp.value = cover.timestamp ?? '';
    [focusX.value, focusY.value] = (cover.focus || [.5, .5]).map(value => value * 100);
    ready = cover.ready;
    document.getElementById('coverPreviews').hidden = !ready;
    const [width, height] = (cover.aspect_ratio || '9:16').split(':').map(Number);
    document.getElementById('coverLandscapeFigure').hidden = !(width > height);
    if (ready) {
      document.getElementById('coverPortrait').src = cover.images.portrait;
      document.getElementById('coverLandscape').src = cover.images.landscape;
    }
    document.getElementById('coverTitleSave').disabled = !ready;
  }
  async function save(kind) {
    if (busy || !loaded) return;
    busy = true; controls.forEach(control => {control.disabled = true;});
    message.textContent = 'Đang tạo ảnh bìa…';
    try {
      let result;
      if (kind === 'upload') {
        const file = document.getElementById('coverUpload').files[0];
        if (!file) throw new Error('Chọn ảnh trước khi lưu.');
        if (file.size > 5*1024*1024) throw new Error('Ảnh tối đa 5 MiB.');
        const body = new FormData(); body.append('image', file); body.append('title', title.value);
        body.append('focus_x', Number(focusX.value) / 100); body.append('focus_y', Number(focusY.value) / 100);
        const response = await fetch(endpoint, {method: 'POST', body});
        result = await response.json();
        if (!response.ok) throw new Error(result.message || 'Không lưu được ảnh.');
      } else result = await api(endpoint, {title: title.value, timestamp: timestamp.value === '' ? null : Number(timestamp.value),
        focus: [Number(focusX.value) / 100, Number(focusY.value) / 100], mode: kind});
      show(result.cover); message.textContent = result.message;
      document.getElementById('coverUpload').value = '';
    } catch (error) {message.textContent = error.message;}
    finally {busy = false; controls.forEach(control => {control.disabled = false;}); document.getElementById('coverTitleSave').disabled = !ready;}
  }
  form.addEventListener('submit', event => {event.preventDefault(); save('frame');});
  document.getElementById('coverTitleSave').addEventListener('click', () => save('title'));
  document.getElementById('coverUploadSave').addEventListener('click', () => save('upload'));
  controls.forEach(control => {control.disabled = true;});
  api(endpoint).then(result => {show(result.cover); loaded = true; message.textContent = ready ? 'Ảnh bìa đã sẵn sàng.' : 'Chưa có ảnh bìa. Tạo từ video hoặc tải ảnh riêng.'; controls.forEach(control => {control.disabled = false;}); document.getElementById('coverTitleSave').disabled = !ready;})
    .catch(error => {message.textContent = error.message;});
}
