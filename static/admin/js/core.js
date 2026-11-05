export const $ = id => document.getElementById(id);
export const names = {facebook:'Facebook', instagram:'Instagram', threads:'Threads', tiktok:'TikTok', youtube:'YouTube'};
const labels = {disconnected:'Chưa kết nối', connected:'Phiên đã lưu', connecting:'Đang đăng nhập', save_requested:'Đang lưu phiên', cancel_requested:'Đang đóng', queued:'Đã lên lịch', running:'Đang chuẩn bị / tải lên', submitting:'Đang xuất bản', published:'Đã đăng', failed:'Lỗi trước khi đăng', needs_login:'Cần đăng nhập', needs_review:'Cần kiểm tra bài', cancelled:'Đã hủy'};
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
      try { await handler(); await refresh(); }
      catch (error) { notice(error.message, true); }
      finally { if (button.isConnected) button.disabled = false; }
    });
    return button;
  }

let renderer = () => {};
let refreshing = false;
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
  } catch (error) { notice(error.message, true); }
  finally { refreshing = false; }
}
export function startPolling(render) {
  renderer = render;
  $('refreshStatus').addEventListener('click', refresh);
  $('startWorker').addEventListener('click', async () => {
    $('startWorker').disabled = true;
    try { const result = await api('/api/social/worker/start', {}); notice(result.message); }
    catch (error) { notice(error.message, true); }
    finally { $('startWorker').disabled = false; await refresh(); }
  });
  refresh();
  setInterval(() => {if (!document.hidden) refresh();}, 4000);
}
