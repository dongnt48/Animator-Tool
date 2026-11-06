import {api, element, startPolling} from '../core.js';
import './animation-settings.js';

const select = document.getElementById('animationVideo');
const button = document.getElementById('animationRenderButton');
const message = document.getElementById('animationRenderMessage');
const info = document.getElementById('animationVideoInfo');
let videos = [];
let submitting = false;
let polling = false;
let optionsSignature = '';
let acceptedVideoId = null;
const selected = () => videos.find(video => video.id === select.value);

function updateInfo() {
  const video = selected();
  info.hidden = !video;
  button.disabled = submitting || !video || video.status === 'processing';
  button.textContent = submitting ? 'Đang bắt đầu…' : video?.status === 'processing' ? 'Đang xử lý…' : 'Dựng bằng Antigravity';
  if (!video) return;
  document.getElementById('animationVideoTitle').textContent = video.caption || video.title || video.id;
  document.getElementById('animationProgress').textContent = video.log || video.status;
  const running = video.status === 'processing';
  const runState = document.getElementById('animationRunState');
  runState.dataset.state = video.status;
  runState.setAttribute('aria-busy', String(running));
  document.getElementById('animationStatus').textContent = ({processing: 'Đang chạy', error: 'Thất bại', completed: 'Đã hoàn thành', new: 'Chưa dựng'})[video.status] || 'Chưa có trạng thái';
  const progress = document.getElementById('animationStageProgress');
  const stageLabel = document.getElementById('animationStageLabel');
  progress.hidden = !running;
  stageLabel.hidden = !running;
  const stage = Number((video.log || '').match(/^([1-4])\/4:/)?.[1] || 0);
  if (stage) progress.value = stage;
  else progress.removeAttribute('value');
  stageLabel.textContent = stage ? `${stage}/4 · ${['', 'Chuẩn bị âm thanh', 'Nhận diện & phân cảnh AI', 'Dựng cảnh minh họa', 'Xuất video'][stage]}` : 'Đang chuẩn bị hoặc chờ lượt xử lý…';
  if (acceptedVideoId === video.id && ['error', 'completed'].includes(video.status)) {
    message.textContent = video.status === 'error' ? `Dựng thất bại: ${video.log || 'Không xử lý được video.'}` : 'Dựng xong. Bấm “Xem video và thành phẩm” để xem kết quả.';
    message.dataset.state = video.status;
    acceptedVideoId = null;
  }
  document.getElementById('animationVideoDetail').href = '/videos/' + encodeURIComponent(video.id);
  const thumbnail = document.getElementById('animationThumbnail');
  const src = '/api/social/videos/' + encodeURIComponent(video.id) + '/thumbnail/original';
  if (thumbnail.getAttribute('src') !== src) { thumbnail.hidden = false; thumbnail.src = src; }
}
document.getElementById('animationThumbnail').addEventListener('error', event => { event.target.hidden = true; });
select.addEventListener('change', () => { message.textContent = ''; delete message.dataset.state; updateInfo(); });

async function refreshVideos() {
  if (polling) return;
  polling = true;
  try {
    const data = await api('/api/videos');
    videos = data.videos.filter(video => video.video_filename);
    const signature = JSON.stringify(videos.map(v => [v.id, v.stt, v.caption || v.title]));
    if (signature !== optionsSignature) {
      const previous = select.value;
      select.replaceChildren(element('option', videos.length ? 'Chọn video…' : 'Chưa có video gốc trong thư viện'));
      select.firstElementChild.value = '';
      for (const video of videos) {
        const title = video.caption || video.title || video.id;
        const option = element('option', `#${video.stt || ''} · ${title.length > 90 ? title.slice(0, 90) + '…' : title}`);
        option.value = video.id;
        select.append(option);
      }
      select.value = videos.some(v => v.id === previous) ? previous : '';
      optionsSignature = signature;
    }
    select.disabled = submitting || !videos.length;
    updateInfo();
  } catch (error) { message.textContent = error.message; }
  finally { polling = false; }
}
document.getElementById('animationRenderForm').addEventListener('submit', async event => {
  event.preventDefault();
  const video = selected();
  if (submitting || !video || video.status === 'processing') return;
  submitting = true;
  select.disabled = true;
  updateInfo();
  try {
    await window.saveAnimationSettings();
    const result = await api('/api/animation/render/' + encodeURIComponent(video.id), {});
    acceptedVideoId = video.id;
    video.status = 'processing';
    video.log = 'Đã nhận yêu cầu, đang chuẩn bị dựng…';
    message.textContent = result.message;
    message.dataset.state = 'processing';
    await refreshVideos();
  } catch (error) { message.textContent = error.message; message.dataset.state = 'error'; }
  finally { submitting = false; select.disabled = !videos.length; updateInfo(); }
});
startPolling(() => {});
refreshVideos();
setInterval(() => { if (!document.hidden && !submitting) refreshVideos(); }, 2500);
