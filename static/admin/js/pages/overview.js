import { $, startPolling } from '../core.js';

startPolling(data => {
  const tasks = data.batches.flatMap(batch => batch.tasks);
  $('metricReady').textContent = String(data.daily?.available_count ?? data.videos.length);
  $('metricAccounts').textContent = `${data.accounts.filter(account => account.state === 'connected').length}/5`;
  $('metricPublished').textContent = String(tasks.filter(task => task.state === 'published').length);
  $('metricAttention').textContent = String(tasks.filter(task => ['failed', 'needs_login', 'needs_review'].includes(task.state)).length);
});
