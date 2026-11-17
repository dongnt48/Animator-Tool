import { $, names, element, notice, api, badge, action, refresh, startPolling } from '../core.js';
let batchesSignature = "";
  function safePostUrl(platform, url) {
    try {
      const parsed = new URL(url);
      const hosts = {facebook:['facebook.com','www.facebook.com','m.facebook.com'],instagram:['instagram.com','www.instagram.com'],threads:['threads.com','www.threads.com','threads.net','www.threads.net'],tiktok:['tiktok.com','www.tiktok.com'],youtube:['youtube.com','www.youtube.com','youtu.be']};
      return parsed.protocol === 'https:' && !parsed.username && !parsed.password && hosts[platform]?.includes(parsed.hostname);
    } catch { return false; }
  }
  function renderBatches(batches) {
    const signature = JSON.stringify(batches);
    if (signature === batchesSignature) return;
    batchesSignature = signature;
    const previousOpen = new Map([...$('batches').querySelectorAll('details.batch')].map(node => [node.id, node.open]));
    const fragment = document.createDocumentFragment();
    for (const batch of batches) {
      const card = element('details', undefined, 'batch');
      card.id = `batch-${batch.id}`;
      const heading = element('summary', undefined, 'batch-heading');
      const title = element('span', new Date(batch.scheduled_at * 1000).toLocaleString('vi-VN', {dateStyle:'medium',timeStyle:'short'}));
      const failures = batch.tasks.filter(task => ['failed','needs_login','needs_review'].includes(task.state)).length;
      const published = batch.tasks.filter(task => task.state === 'published').length;
      const active = batch.tasks.some(task => ['running','submitting'].includes(task.state));
      const cancelled = batch.tasks.every(task => task.state === 'cancelled');
      const status = badge(failures ? 'needs_review' : published === batch.tasks.length ? 'published' : active ? 'running' : 'queued');
      status.textContent = cancelled ? 'Đã hủy' : failures ? `${failures} cần xử lý` : `${published}/${batch.tasks.length} đã đăng`;
      if (cancelled) status.dataset.state = 'cancelled';
      heading.append(title, status);
      card.open = previousOpen.has(card.id) ? previousOpen.get(card.id) : failures > 0 || active;
      const body = element('div', undefined, 'batch-body');
      if (batch.tasks.some(task => ['queued','failed','needs_login','needs_review'].includes(task.state))) {
        body.append(action('Hủy phần chưa chạy', async () => {
          if (!confirm('Hủy các nền tảng chưa chạy trong lịch này?')) return;
          const result = await api(`/api/social/batches/${batch.id}/cancel`, {}); notice(result.message);
        }, 'danger'));
      }
      body.append(element('p', batch.caption, 'batch-caption'));
      for (const task of batch.tasks) {
        const row = element('div', undefined, 'task');
        row.append(element('span', names[task.platform], 'task-name'), badge(task.state));
        const taskMessage = element('div', undefined, 'task-message');
        taskMessage.append(element('span', task.state === 'needs_review' ? 'Hệ thống chưa xác định được kết quả đăng. Không tự đăng lại để tránh trùng bài.' : task.message || (task.state === 'queued' ? 'Chờ đến giờ đăng.' : '')));
        row.append(taskMessage);
        const covers = {pending:'Bìa: chờ áp dụng', applied:'Bìa: đã thấy ảnh mới trong xem trước', frame:'Bìa: đã chọn khung video', automatic:'Bìa: dùng tự động', needs_review:'Bìa: cần kiểm tra', none:'Bìa: chưa cấu hình'};
        const coverStatus = element('span', covers[task.cover_state] || covers.none, 'cover-status');
        coverStatus.title = task.cover_message || '';
        taskMessage.append(coverStatus);
        const controls = element('div', undefined, 'task-actions');
        if (task.url && safePostUrl(task.platform, task.url)) {
          const link = element('a','Mở bài đã đăng ↗'); link.href = task.url; link.target = '_blank'; link.rel = 'noopener noreferrer'; controls.append(link);
        }
        if (['failed','needs_login'].includes(task.state)) {
          controls.append(action('Thử lại nền tảng này', async () => {
            const prompt = `Đăng lại riêng lên ${names[task.platform]} ngay bây giờ?`;
            if (!confirm(prompt)) return;
            const result = await api(`/api/social/tasks/${task.id}/retry`, {}); notice(result.message);
          }));
        }
        row.append(controls); body.append(row);
      }
      card.append(heading, body);
      fragment.append(card);
    }
    if (!batches.length) fragment.append(element('p','Chưa có lượt đăng. Kết quả sẽ xuất hiện khi đến giờ.', 'empty'));
    $('batches').replaceChildren(fragment);
  }

startPolling(data => renderBatches(data.batches));
