import { $, names, element, notice, api, badge, action, refresh, startPolling } from '../core.js';
let snapshot = null; let videoSignature = ''; let requestKey = crypto.randomUUID(); let submittedPayload = null;
const preselected = new URLSearchParams(location.search).get('video');
  function preview() {
    const video = snapshot?.videos.find(item => item.id === $('videoSelect').value);
    const player = $('previewVideo');
    player.hidden = !video; $('previewEmpty').hidden = Boolean(video);
    if (video) {
      const source = `/video/output/${encodeURIComponent(video.output_filename)}`;
      if (player.getAttribute('src') !== source) { player.src = source; player.load(); }
      $('captionPreview').textContent = video.caption;
    } else { player.removeAttribute('src'); player.load(); $('captionPreview').textContent = 'Caption của video sẽ hiện ở đây.'; }
    $('scheduleButton').disabled = !video;
  }
  function renderVideos(videos) {
    const signature = JSON.stringify(videos);
    if (signature === videoSignature) return;
    videoSignature = signature;
    const previous = $('videoSelect').value || preselected;
    $('videoSelect').replaceChildren(new Option('Chọn video đã dựng', ''));
    for (const video of videos) $('videoSelect').add(new Option(video.caption.replace(/\s+/g,' ').slice(0,100), video.id));
    if (videos.some(video => video.id === previous)) $('videoSelect').value = previous;
    $('emptyVideos').hidden = videos.length > 0;
    preview();
  }

$('videoSelect').addEventListener('change', preview);
  $('scheduleForm').addEventListener('input', () => { requestKey = crypto.randomUUID(); submittedPayload = null; });
  $('scheduleForm').addEventListener('submit', async event => {
    event.preventDefault();
    const when = new Date($('scheduleAt').value);
    if (!submittedPayload && (!Number.isFinite(when.getTime()) || when.getTime() < Date.now() - 5000)) { notice('Chọn thời gian từ hiện tại trở đi.', true); return; }
    const button = $('scheduleButton'); button.disabled = true;
    // Keep the identical request/key after a lost response; editing starts a new request.
    submittedPayload ||= {video_id:$('videoSelect').value,scheduled_at:when.toISOString(),made_for_kids:$('youtubeAudience').value === 'yes',confirm_all_platforms:$('confirmPublish').checked,request_key:requestKey};
    try {
      await api('/api/social/batches', submittedPayload);
      notice('Đã lưu lịch cho cả 5 nền tảng. Giữ máy bật và kiểm tra bộ đăng đang hoạt động.');
      $('confirmPublish').checked = false; requestKey = crypto.randomUUID(); submittedPayload = null;
      await refresh();
    } catch (error) { notice(error.message, true); }
    finally { button.disabled = false; }
  });
  const soon = new Date(Date.now() + 5 * 60000);
  const localDate = new Date(soon.getTime() - soon.getTimezoneOffset() * 60000).toISOString().slice(0,16);
  $('scheduleAt').value = localDate;
  $('timezoneHint').textContent = `Múi giờ thiết bị: ${Intl.DateTimeFormat().resolvedOptions().timeZone}. Lịch được lưu theo UTC và hiển thị theo giờ thiết bị.`;

startPolling(data => {snapshot = data; renderVideos(data.videos);});
