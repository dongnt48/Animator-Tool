const form = document.getElementById('animationSettingsForm');
if (form) {
  const model = document.getElementById('animationModel');
  const speech = document.getElementById('animationSpeechModel');
  const channelName = document.getElementById('animationChannelName');
  const button = document.getElementById('saveAnimationSettings');
  const message = document.getElementById('animationSettingsMessage');
  const ready = document.getElementById('animationReadiness');
  let saving = false;
  let dirty = false;
  let loaded = false;
  const enable = value => [model, speech, channelName, button].filter(Boolean).forEach(el => { el.disabled = !value; });
  const apply = data => {
    if (model) model.value = data.settings.model;
    if (speech) speech.value = data.settings.speech_model;
    channelName.value = data.settings.channel_name || '';
    const status = data.readiness;
    if (ready) ready.textContent = status.cli_installed && status.speech_installed
      ? 'Đã cài CLI & nhận diện · dùng phiên đăng nhập agy'
      : [!status.cli_installed ? 'Chưa cài agy' : '', !status.speech_installed ? 'Chưa cài nhận diện' : ''].filter(Boolean).join(' · ');
  };
  const save = async () => {
    if (saving) throw new Error('Đang lưu cấu hình dựng video.');
    if (!loaded) throw new Error('Chưa tải được cấu hình dựng video. Tải lại trang rồi thử lại.');
    if (!dirty) return;
    saving = true;
    enable(false);
    button.textContent = 'Đang lưu…';
    try {
      const response = await fetch('/api/animation/settings', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({channel_name: channelName.value.trim(),
          ...(model ? {model: model.value.trim()} : {}), ...(speech ? {speech_model: speech.value} : {})}),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || 'Không lưu được cấu hình.');
      apply(data);
      dirty = false;
      message.textContent = 'Đã lưu. Áp dụng cho lần dựng tiếp theo; kịch bản đã có sẽ được dùng lại.';
    } finally {
      saving = false;
      enable(true);
      button.textContent = 'Lưu cấu hình';
    }
  };
  window.saveAnimationSettings = save;
  form.addEventListener('input', () => { dirty = true; message.textContent = 'Có thay đổi chưa lưu.'; });
  form.addEventListener('submit', async event => {
    event.preventDefault();
    try { await save(); } catch (error) { message.textContent = error.message; }
  });
  fetch('/api/animation/settings').then(async response => {
    const data = await response.json();
    if (!response.ok) throw new Error(data.message || 'Không tải được cấu hình.');
    apply(data);
    loaded = true;
    enable(true);
  }).catch(error => { if (ready) ready.textContent = 'Không tải được cấu hình'; message.textContent = error.message; });
}
