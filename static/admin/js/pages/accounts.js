import { $, names, element, notice, api, badge, action, refresh, startPolling } from '../core.js';
let accountsSignature = "";
function accountMessage(message) {
  if (message?.includes('Page.wait_for_timeout: Target page, context or browser has been closed')) {
    return 'Cửa sổ đăng nhập đã đóng trước khi lưu phiên. Bấm Kết nối để thử lại.';
  }
  return message;
}

  function renderAccounts(accounts) {
    const signature = JSON.stringify(accounts);
    if (signature === accountsSignature) return;
    accountsSignature = signature;
    const connected = accounts.filter(account => account.state === 'connected').length;
    $('accountSummary').textContent = `${connected}/5 đã kết nối`;
    const fragment = document.createDocumentFragment();
    for (const account of accounts) {
      const card = element('article', undefined, 'account');
      card.append(element('h3', names[account.platform]), badge(account.state));
      const toggleLabel = element('label', undefined, 'toggle-label');
      const toggle = element('input'); toggle.type = 'checkbox'; toggle.role = 'switch';
      toggle.checked = account.publishing_enabled !== false;
      toggle.setAttribute('aria-label', `Đăng lên ${names[account.platform]}`);
      toggle.addEventListener('change', async () => {
        const enabled = toggle.checked; toggle.disabled = true;
        try {
          const result = await api(`/api/social/accounts/${account.platform}/publishing`, {enabled});
          notice(result.message); await refresh();
        } catch (error) {toggle.checked = !enabled; notice(error.message, true);}
        finally {toggle.disabled = false;}
      });
      toggleLabel.append(element('span', 'Cho phép đăng'), toggle); card.append(toggleLabel);
      const browserName = account.platform === 'tiktok' ? 'Google Chrome' : 'Chromium';
      card.append(element('p', `${browserName} · hồ sơ riêng. Nếu cửa sổ Studio lỗi: mở trình duyệt, đăng nhập, đóng trình duyệt rồi Kết nối và Lưu phiên.`, 'hint'));
      const message = accountMessage(account.message);
      if (message && account.state === 'needs_login') card.append(element('p', message));
      const controls = element('div', undefined, 'account-actions');
      const pending = ['connecting','save_requested','cancel_requested'].includes(account.state) && account.lease_until * 1000 > Date.now();
      if (pending) {
        const save = action('Lưu phiên', async () => {
          if (!confirm(`Bạn đã đăng nhập và kiểm tra đúng tài khoản ${names[account.platform]} trong cửa sổ trình duyệt?`)) return;
          const result = await api(`/api/social/accounts/${account.platform}/save`, {});
          notice(result.message);
        });
        save.disabled = account.state !== 'connecting';
        controls.append(save, action('Hủy', async () => {
          const result = await api(`/api/social/accounts/${account.platform}/cancel`, {}); notice(result.message);
        }));
      } else {
        const connect = action(account.state === 'connected' ? 'Kết nối lại' : 'Kết nối', async () => {
          const result = await api(`/api/social/accounts/${account.platform}/connect`, {}); notice(result.message);
        });
        connect.disabled = account.lease_until * 1000 > Date.now();
        controls.append(connect);
        const openBrowser = action('Mở trình duyệt để đăng nhập', async () => {
          const result = await api(`/api/social/accounts/${account.platform}/open-browser`, {}); notice(result.message);
        });
        openBrowser.disabled = account.lease_until * 1000 > Date.now();
        controls.append(openBrowser);
      }
      card.append(controls); fragment.append(card);
    }
    $('accounts').replaceChildren(fragment);
  }

startPolling(data => renderAccounts(data.accounts));
