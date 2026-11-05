import { $, names, element, notice, api, badge, action, refresh, startPolling } from '../core.js';
let dailyDirty = false; let dailyTimes = []; let dailyConfigSignature = '';
  function drawDailyTimes() {
    const fragment = document.createDocumentFragment();
    for (const value of dailyTimes) {
      const remove = element('button', `${value} ×`, 'secondary');
      remove.type = 'button'; remove.setAttribute('aria-label', `Bỏ giờ ${value}`);
      remove.addEventListener('click', () => {dailyTimes = dailyTimes.filter(time => time !== value); dailyDirty = true; drawDailyTimes();});
      fragment.append(remove);
    }
    if (!dailyTimes.length) fragment.append(element('span','Chưa có khung giờ nào.', 'hint'));
    $('dailyTimes').replaceChildren(fragment);
  }
  function dailyRequirements() {
    $('dailyConfirm').required = $('dailyEnabled').checked;
    $('dailyAudience').required = $('dailyEnabled').checked;
    $('dailySettingsSummary').textContent = `${$('dailySelection').value === 'random' ? 'Ngẫu nhiên' : 'Bài cũ trước'} · ${$('dailyTimezone').value === 'UTC' ? 'UTC' : 'UTC+7'}`;
  }
  function renderDaily(daily) {
    if (!daily) return;
    const config = daily.config;
    const signature = JSON.stringify(config);
    if (!dailyDirty && signature !== dailyConfigSignature) {
      dailyConfigSignature = signature;
      dailyTimes = [...config.times]; drawDailyTimes();
      $('dailyEnabled').checked = config.enabled;
      $('dailyTimezone').value = config.timezone;
      $('dailySelection').value = config.selection;
      $('dailyAudience').value = config.made_for_kids === null ? '' : config.made_for_kids ? 'yes' : 'no';
      $('dailyConfirm').checked = false; dailyRequirements();
    }
    $('dailyAvailable').textContent = String(daily.available_count);
    $('dailyState').textContent = config.enabled ? 'Đang bật tự động' : 'Chưa bật tự động';
    $('dailyState').dataset.state = config.enabled ? 'online' : 'disconnected';
    const format = value => new Date(value * 1000).toLocaleString('vi-VN', {timeZone:config.timezone,dateStyle:'short',timeStyle:'short'});
    $('dailyNext').textContent = daily.next_at ? `Lượt tiếp theo: ${format(daily.next_at)}` : 'Chưa có lượt tiếp theo.';
    const preview = document.createDocumentFragment();
    for (const caption of daily.preview || []) preview.append(element('li', caption));
    $('dailyQueue').replaceChildren(preview);
    const outcomes = {scheduled:'Đã lấy một video',preparing:'Đang lấy bài',empty:'Hết bài',blocked:'Chưa có phiên đăng nhập',skipped:'Đã bỏ qua',error:'Lỗi lấy bài',cancelled:'Đã dừng'};
    const runs = document.createDocumentFragment();
    for (const run of daily.runs.slice(0,8)) {
      const row = element('div', undefined, 'daily-run');
      row.append(element('strong', `${format(run.slot_at)} · ${outcomes[run.state] || run.state}`), element('p', run.message, 'hint'));
      if (run.batch_id) {const link = element('a','Xem kết quả 5 nền tảng ↓'); link.href = `/publishing/results#batch-${run.batch_id}`; row.append(link);}
      runs.append(row);
    }
    if (!daily.runs.length) runs.append(element('p','Chưa đến khung giờ tự động nào.', 'hint'));
    $('dailyRuns').replaceChildren(runs);
  }
  $('dailyForm').addEventListener('input', () => {dailyDirty = true; dailyRequirements();});
  $('addDailyTime').addEventListener('click', () => {
    const value = $('dailyTime').value;
    if (!/^(?:[01]\d|2[0-3]):[0-5]\d$/.test(value)) {notice('Chọn giờ hợp lệ rồi bấm Thêm giờ.', true); return;}
    if (dailyTimes.length >= 24 && !dailyTimes.includes(value)) {notice('Tối đa 24 khung giờ mỗi ngày.', true); return;}
    dailyTimes = [...new Set([...dailyTimes,value])].sort(); dailyDirty = true; drawDailyTimes(); $('dailyTime').value = '';
  });
  $('dailyForm').addEventListener('submit', async event => {
    event.preventDefault(); $('saveDaily').disabled = true;
    try {
      const enabled = $('dailyEnabled').checked;
      const audience = $('dailyAudience').value;
      const result = await api('/api/social/daily', {enabled,times:dailyTimes,timezone:$('dailyTimezone').value,
        selection:$('dailySelection').value,made_for_kids:audience === '' ? null : audience === 'yes',confirm_all_platforms:$('dailyConfirm').checked});
      dailyDirty = false; dailyConfigSignature = ''; notice(result.message); await refresh();
    } catch (error) {notice(error.message,true);}
    finally {$('saveDaily').disabled = false;}
  });

startPolling(data => renderDaily(data.daily));
