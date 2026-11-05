import { $, names, element, notice, api, badge, action, refresh, startPolling } from '../core.js';
let accountsSignature = "";
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
      if (account.message && account.state === 'needs_login') card.append(element('p', account.message));
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
      }
      card.append(controls); fragment.append(card);
    }
    $('accounts').replaceChildren(fragment);
  }

startPolling(data => renderAccounts(data.accounts));
