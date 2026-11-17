import { $, names, element, notice, api, badge, action, refresh, startPolling } from '../core.js';
let snapshot = null; let videoSignature = ''; let requestKey = crypto.randomUUID(); let submittedPayload = null;
const preselected = new URLSearchParams(location.search).get('video');
let targetPlatforms = [];
let targetsRendered = false;
let pendingVideo = null;
function renderTargets(accounts) {
  if (submittedPayload) return;
  const targets = accounts.filter(account => account.publishing_enabled !== false).map(account => account.platform);
  if (!targetsRendered || JSON.stringify(targets) !== JSON.stringify(targetPlatforms)) {
    targetsRendered = true;
    targetPlatforms = targets;
    $('confirmPublish').checked = false;
    if (!submittedPayload) requestKey = crypto.randomUUID();
    $('scheduleDestinations').replaceChildren(...targets.map(platform => element('span', names[platform])));
    if (!targets.length) $('scheduleDestinations').append(element('span', 'Chưa bật nền tảng nhận bài. Vào Tài khoản để bật đăng.'));
    $('scheduleButton').textContent = targets.length === 5 ? 'Lên lịch cho cả 5 nền tảng' : `Lên lịch cho ${targets.length} nền tảng`;
    $('youtubeOptions').hidden = !targets.includes('youtube');
    $('youtubeAudience').required = targets.includes('youtube');
  }
}
  function preview() {
    const video = snapshot?.videos.find(item => item.id === $('videoSelect').value);
    const player = $('previewVideo');
    player.hidden = !video; $('previewEmpty').hidden = Boolean(video);
    if (video) {
      const source = `/video/output/${encodeURIComponent(video.output_filename)}`;
      if (player.getAttribute('src') !== source) { player.src = source; player.load(); }
      $('captionPreview').textContent = video.caption;
    } else { player.removeAttribute('src'); player.load(); $('captionPreview').textContent = 'Caption của video sẽ hiện ở đây.'; }
    $('scheduleButton').disabled = !video || !targetPlatforms.length;
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
  $('scheduleForm').addEventListener('input', () => { requestKey = crypto.randomUUID(); submittedPayload = null; pendingVideo = null; });
  $('scheduleForm').addEventListener('submit', async event => {
    event.preventDefault();
    const when = new Date($('scheduleAt').value);
    if (!submittedPayload && (!Number.isFinite(when.getTime()) || when.getTime() < Date.now() - 5000)) { notice('Chọn thời gian từ hiện tại trở đi.', true); return; }
    const button = $('scheduleButton'); button.disabled = true;
    // Keep the identical request/key after a lost response; editing starts a new request.
    pendingVideo ||= snapshot?.videos.find(video => video.id === $('videoSelect').value);
    submittedPayload ||= {video_id:$('videoSelect').value,scheduled_at:when.toISOString(),made_for_kids:$('youtubeAudience').value === 'yes',confirm_all_platforms:$('confirmPublish').checked,request_key:requestKey,platforms:[...targetPlatforms]};
    try {
      const result = await api('/api/social/batches', submittedPayload);
      const count = result.batch.tasks.length;
      notice(`Đã lưu lịch cho ${count === 5 ? 'cả 5' : count} nền tảng. Giữ máy bật và kiểm tra bộ đăng đang hoạt động.`);
      $('confirmPublish').checked = false; requestKey = crypto.randomUUID(); submittedPayload = null; pendingVideo = null;
      await refresh();
    } catch (error) { notice(error.message, true); }
    finally { button.disabled = false; }
  });
  const soon = new Date(Date.now() + 5 * 60000);
  const localDate = new Date(soon.getTime() - soon.getTimezoneOffset() * 60000).toISOString().slice(0,16);
  $('scheduleAt').value = localDate;
  $('timezoneHint').textContent = `Múi giờ thiết bị: ${Intl.DateTimeFormat().resolvedOptions().timeZone}. Lịch được lưu theo UTC và hiển thị theo giờ thiết bị.`;

startPolling(data => {
  if (submittedPayload && pendingVideo && !data.videos.some(video => video.id === pendingVideo.id)) {
    data = {...data, videos:[...data.videos, pendingVideo]};
  }
  snapshot = data; renderTargets(data.accounts); renderVideos(data.videos); preview();
});
