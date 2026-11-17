export const $ = id => document.getElementById(id);
export const names = {facebook:'Facebook', instagram:'Instagram', threads:'Threads', tiktok:'TikTok', youtube:'YouTube'};
const labels = {disconnected:'Chưa kết nối', connected:'Phiên đã lưu', connecting:'Đang đăng nhập', save_requested:'Đang lưu phiên', cancel_requested:'Đang đóng', queued:'Đã lên lịch', running:'Đang chuẩn bị / tải lên', submitting:'Đang xuất bản', published:'Đã đăng', failed:'Lỗi trước khi đăng', needs_login:'Cần đăng nhập', needs_review:'Chưa xác định kết quả', cancelled:'Đã hủy'};
export const element = (tag, text, className) => {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
  };
export function notice(message, error=false) {
    $('notice').hidden = false;
    $('notice').dataset.error = String(error);
    $('notice').textContent = message;
  }
export async function api(path, body) {
    const response = await fetch(path, body === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    const data = await response.json();
    if (!response.ok) throw new Error(data.message || 'Không thực hiện được yêu cầu.');
    return data;
  }
export function badge(state) {
    const node = element('span', labels[state] || state, 'badge');
    node.dataset.state = state;
    return node;
  }
export function action(text, handler, className='secondary') {
    const button = element('button', text, className);
    button.type = 'button';
    button.addEventListener('click', async () => {
      button.disabled = true;
      try { await handler(); pollGraceUntil = Date.now() + 8000; await refresh(); }
      catch (error) { notice(error.message, true); }
      finally { if (button.isConnected) button.disabled = false; }
    });
    return button;
  }

let renderer = () => {};
let refreshing = false;
let pollTimer = null;
let pollPeriod = 0;
let pollGraceUntil = 0;

function hasActiveSocialWork(data) {
  if (Date.now() < pollGraceUntil) return true;
  if (Array.isArray(data?.accounts) && data.accounts.some(a => ['connecting', 'save_requested', 'cancel_requested'].includes(a.state))) {
    return true;
  }
  if (Array.isArray(data?.batches)) {
    const now = Date.now() / 1000;
    for (const batch of data.batches) {
      for (const task of (batch.tasks || [])) {
        if (['running', 'submitting'].includes(task.state)) return true;
        if (task.state === 'queued' && batch.scheduled_for <= now + 5) return true;
      }
    }
  }
  return false;
}

function syncSocialPolling(active, uncertain) {
  const period = active ? 4000 : uncertain ? 15000 : 0;
  if (period !== pollPeriod && pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
  pollPeriod = period;
  if (period && !pollTimer) {
    pollTimer = setInterval(() => {if (!document.hidden) refresh();}, period);
  } else if (!period && pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

export async function refresh() {
  if (refreshing) return;
  refreshing = true;
  try {
    const data = await api('/api/social/status');
    $('navAccountsCount').textContent = `${data.accounts.filter(a => a.state === 'connected').length}/5`;
    $('workerStatus').textContent = data.worker_online ? 'Online' : 'Offline';
    $('workerStatus').dataset.state = data.worker_online ? 'online' : 'needs_login';
    $('startWorker').hidden = data.worker_online;
    renderer(data);
    syncSocialPolling(hasActiveSocialWork(data), data.batches?.some(batch => batch.tasks?.some(task => task.state === 'needs_review')));
  } catch (error) { notice(error.message, true); }
  finally { refreshing = false; }
}
export function startPolling(render) {
  renderer = render;
  $('refreshStatus').addEventListener('click', refresh);
  $('startWorker').addEventListener('click', async () => {
    $('startWorker').disabled = true;
    try { const result = await api('/api/social/worker/start', {}); pollGraceUntil = Date.now() + 8000; notice(result.message); }
    catch (error) { notice(error.message, true); }
    finally { $('startWorker').disabled = false; await refresh(); }
  });
  refresh();
}
