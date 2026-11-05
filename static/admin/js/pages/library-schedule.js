import { $, api, notice, refresh } from '../core.js';

const dialog = $('libraryScheduleDialog');
let videoId = null;
let busy = false;
let requestKey = crypto.randomUUID();
let submittedPayload = null;
let loading = false;

function setBusy(value) {
  busy = value;
  for (const id of ['libraryScheduleAt','libraryScheduleAudience','libraryScheduleConfirm','libraryScheduleSubmit','libraryScheduleClose']) $(id).disabled = value;
  $('libraryScheduleSubmit').textContent = value ? 'Đang lưu…' : 'Lưu lịch đăng';
}
function close() {
  if (busy) return;
  dialog.close(); submittedPayload = null; videoId = null;
}
$('libraryScheduleClose').addEventListener('click',close);
dialog.addEventListener('cancel',event => {if (busy) event.preventDefault();});
$('libraryScheduleForm').addEventListener('input',() => {
  requestKey = crypto.randomUUID(); submittedPayload = null;
  $('libraryScheduleMessage').textContent = '';
});
$('videoTableBody').addEventListener('click',async event => {
  const button = event.target.closest('[data-schedule-video]');
  if (!button || busy || loading) return;
  const id = button.dataset.scheduleVideo;
  loading = true; button.disabled = true;
  try {
    const data = await api(`/api/social/videos/${encodeURIComponent(id)}`);
    if (data.video.status !== 'completed' || !data.media.output) throw new Error('Video chưa dựng xong hoặc không còn file thành phẩm.');
    videoId = id; requestKey = crypto.randomUUID(); submittedPayload = null;
    $('libraryScheduleForm').reset(); $('libraryScheduleMessage').textContent = '';
    $('libraryScheduleTitle').textContent = data.video.title || 'Video';
    $('libraryScheduleCaption').textContent = data.video.caption ?? data.video.title ?? '';
    const soon = new Date(Date.now()+5*60000);
    $('libraryScheduleAt').value = new Date(soon.getTime()-soon.getTimezoneOffset()*60000).toISOString().slice(0,16);
    $('libraryScheduleTimezone').textContent = `Múi giờ: ${Intl.DateTimeFormat().resolvedOptions().timeZone}`;
    dialog.showModal();
  } catch (error) {notice(error.message,true);}
  finally {loading = false; button.disabled = false;}
});
$('libraryScheduleForm').addEventListener('submit',async event => {
  event.preventDefault(); if (busy || !videoId) return;
  const when = new Date($('libraryScheduleAt').value);
  if (!submittedPayload && (!Number.isFinite(when.getTime()) || when.getTime() < Date.now()-5000)) {
    $('libraryScheduleMessage').textContent = 'Chọn thời gian từ hiện tại trở đi.'; return;
  }
  submittedPayload ||= {video_id:videoId,scheduled_at:when.toISOString(),made_for_kids:$('libraryScheduleAudience').value==='yes',confirm_all_platforms:$('libraryScheduleConfirm').checked,request_key:requestKey};
  setBusy(true);
  try {
    await api('/api/social/batches',submittedPayload);
    dialog.close(); submittedPayload = null; videoId = null;
    notice('Đã lưu lịch đăng cho cả 5 nền tảng.');
    await window.fetchVideos(); await refresh();
  } catch (error) {$('libraryScheduleMessage').textContent = error.message;}
  finally {setBusy(false);}
});
