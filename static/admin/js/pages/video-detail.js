import { $, element, api, notice, startPolling, names, badge } from '../core.js';
import './cover-editor.js';

const videoId = $('videoDetail').dataset.videoId;
let expectedCaption = '';
let saving = false;
const renderStates = {new:'Chờ dựng',processing:'Đang dựng',completed:'Đã dựng',error:'Lỗi dựng'};

function externalLink(url,text) {
  try {
    const parsed = new URL(url);
    if (parsed.protocol !== 'https:') return null;
    const link = element('a',text); link.href = parsed.href; link.target = '_blank'; link.rel = 'noopener noreferrer';
    return link;
  } catch {return null;}
}
function showMedia(media) {
  const fragment = document.createDocumentFragment();
  for (const [key,label] of [['original','Video gốc'],['output','Video đã dựng']]) {
    if (!media[key]) continue;
    const section = element('div'); section.append(element('h3',label));
    const player = element('video'); player.controls = true; player.preload = 'metadata'; player.src = media[key];
    section.append(player); fragment.append(section);
  }
  if (!fragment.childNodes.length) fragment.append(element('p','Không tìm thấy file video trên máy.','hint'));
  $('detailMedia').replaceChildren(fragment);
}
async function load() {
  try {
    const data = await api(`/api/social/videos/${encodeURIComponent(videoId)}`);
    const video = data.video;
    expectedCaption = video.caption ?? video.title ?? '';
    $('detailTitle').textContent = video.title || 'Video';
    $('detailCurrentCaption').textContent = expectedCaption;
    $('detailCaptionState').textContent = video.caption_ai_saved_at || video.caption ? 'Đã viết lại' : 'Chưa viết lại';
    $('detailCaption').value = expectedCaption;
    $('detailDraftNote').textContent = 'Caption hiện tại dùng để đăng bài. Bấm lưu khi chỉnh sửa thủ công.';
    $('detailTranscript').textContent = video.transcript || 'Chưa có lời thoại được lưu.';
    $('detailSentDialogue').hidden = !video.caption_ai_result?.transcript;
    $('detailSentText').textContent = video.caption_ai_result?.transcript || '';
    $('detailRenderLog').textContent = video.log || '';
    const metadata = document.createDocumentFragment();
    for (const [label,value] of [['STT',video.stt],['Trạng thái dựng',renderStates[video.status] || video.status],
      ['Ngày tạo',video.created_at],['Thời lượng',video.duration_sec ? `${video.duration_sec}s` : '—'],
      ['Tỷ lệ',video.aspect_ratio],['Phong cách',video.style],['Nhân vật',video.character]]) {
      const pair = element('div'); pair.append(element('dt',label),element('dd',String(value ?? '—'))); metadata.append(pair);
    }
    const source = externalLink(video.tiktok_url,'Mở video nguồn');
    if (source) {const pair = element('div'); pair.append(element('dt','Nguồn'),source); metadata.append(pair);}
    $('detailMetadata').replaceChildren(metadata);
    showMedia(data.media);
    const publications = document.createDocumentFragment();
    for (const [platform,label] of Object.entries(names)) {
      const state = data.publication[platform];
      const row = element('div',undefined,'record-publication'); row.append(element('strong',label));
      row.append(state ? badge(state.state) : element('span','Chưa đăng','hint'));
      if (state?.url) {const link = externalLink(state.url,'Xem bài đăng'); if (link) row.append(link);}
      if (state?.message) row.append(element('p',state.message,'hint'));
      if (state?.cover_state) {
        const labels = {pending:'Ảnh bìa: chờ áp dụng', applied:'Ảnh bìa: đã thấy ảnh mới trong xem trước', frame:'Ảnh bìa: đã chọn khung video', automatic:'Ảnh bìa: dùng tự động', needs_review:'Ảnh bìa: cần kiểm tra', none:'Ảnh bìa: chưa cấu hình'};
        const cover = element('p', labels[state.cover_state] || labels.none, 'cover-status');
        cover.title = state.cover_message || ''; row.append(cover);
      }
      publications.append(row);
    }
    $('detailPublication').replaceChildren(publications);
    $('videoDetail').hidden = false;
  } catch (error) {notice(error.message,true);}
}
$('detailCaptionForm').addEventListener('submit',async event => {
  event.preventDefault(); if (saving) return;
  saving = true; $('detailSaveCaption').disabled = true; $('detailCaption').disabled = true;
  try {
    const data = await api('/api/captions/save',{items:[{video_id:videoId,caption:$('detailCaption').value,expected_caption:expectedCaption}]});
    const result = data.results[0];
    notice(result.message,result.status !== 'saved');
    if (result.status === 'saved') await load();
  } catch (error) {notice(error.message,true);}
  finally {saving = false; $('detailSaveCaption').disabled = false; $('detailCaption').disabled = false;}
});
$('refreshStatus').addEventListener('click',() => {if (!saving) load();});
startPolling(() => {});
load();
