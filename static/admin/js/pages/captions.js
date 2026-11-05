import { $, element, api, notice, startPolling } from '../core.js';

let videos = [];
const selected = new Set();
const drafts = new Map();
let busy = false;
let configured = false;
let initialized = false;
let batchResults = [];
let hashtagsLoaded = false;
let savedHashtags = '';
let savingHashtags = false;
let providerLoaded = false;
let savingProvider = false;
let savedModel = '';
let activeRowId = null;
const chunks = items => Array.from({length:Math.ceil(items.length/100)},(_,i) => items.slice(i*100,(i+1)*100));
const preselected = new URLSearchParams(location.search).get('video');
const libraryTable = $('videoTableBody');
const wasRewritten = video => video.caption_rewritten ?? Boolean(video.caption_ai || video.caption_ai_saved_at || video.caption);
function eligibleIds() {
  return videos.filter(video => selected.has(video.id) && ($('captionRewriteMode').value === 'all' || !wasRewritten(video))).map(video => video.id);
}

function updateSelection() {
  $('captionSelectedCount').textContent = `${selected.size} đã chọn`;
  const eligible = eligibleIds();
  $('captionEligibleCount').textContent = `${eligible.length} sẽ viết`;
  $('captionRewriteMode').disabled = busy;
  $('rewriteCaptions').disabled = busy || savingProvider || !providerLoaded || savingHashtags || !hashtagsLoaded || (!configured && !$('captionApiKey').value.trim()) || eligible.length === 0;
  $('captionModel').disabled = busy || savingProvider || !providerLoaded;
  $('captionApiKey').disabled = busy || savingProvider || !providerLoaded;
  $('saveCaptionProvider').disabled = busy || savingProvider || !providerLoaded;
  $('captionHashtags').disabled = busy || savingHashtags || !hashtagsLoaded;
  $('saveCaptionHashtags').disabled = busy || savingHashtags || !hashtagsLoaded || $('captionHashtags').value === savedHashtags;
  $('captionSelectAll').checked = videos.length > 0 && videos.every(video => selected.has(video.id));
  $('captionSelectAll').indeterminate = selected.size > 0 && selected.size < videos.length;
  $('captionSelectAll').disabled = busy;
  const checkboxes = libraryTable ? libraryTable.querySelectorAll('input[data-caption-video]') : $('captionVideos').querySelectorAll('input');
  checkboxes.forEach(input => {input.disabled = busy; if (libraryTable) input.checked = selected.has(input.dataset.captionVideo);});
  if (libraryTable) libraryTable.querySelectorAll('[data-caption-rewrite]').forEach(button => {
    button.disabled = busy || savingProvider || savingHashtags || !providerLoaded || !hashtagsLoaded;
    button.textContent = busy && activeRowId === button.dataset.captionRewrite ? 'Đang viết…' : 'Viết lại caption';
    button.setAttribute('aria-busy',String(busy && activeRowId === button.dataset.captionRewrite));
  });
}
function drawApiState() {
  $('captionApiState').textContent = configured ? 'API đã cấu hình' : 'Chưa có API key';
  $('captionApiState').dataset.state = configured ? 'connected' : 'needs_login';
}
function applyProvider(data) {
  savedModel = data.model; $('captionModel').value = savedModel;
  $('captionApiKey').value = '';
  $('captionApiKey').placeholder = data.configured ? 'Đã có khóa. Để trống để giữ nguyên' : 'Nhập API key';
  configured = data.configured; providerLoaded = true; drawApiState();
}
async function loadProvider() {
  try {
    applyProvider(await api('/api/captions/provider'));
    $('captionProviderState').textContent = configured ? 'Đã cấu hình' : 'Chưa có API key';
  } catch (error) {notice(error.message,true); $('captionProviderState').textContent = 'Chưa tải được. Bấm Làm mới để thử lại.';}
  finally {updateSelection();}
}
async function persistProvider() {
  if (!providerLoaded) throw new Error('Chưa tải xong cấu hình AI.');
  if ($('captionModel').value === savedModel && !$('captionApiKey').value.trim()) return;
  savingProvider = true; updateSelection();
  try {
    const data = await api('/api/captions/provider',{model:$('captionModel').value,api_key:$('captionApiKey').value});
    applyProvider(data); $('captionProviderState').textContent = 'Đã lưu cấu hình';
  } finally {savingProvider = false; updateSelection();}
}
for (const id of ['captionModel','captionApiKey']) $(id).addEventListener('input',() => {$('captionProviderState').textContent = 'Chưa lưu'; updateSelection();});
$('saveCaptionProvider').addEventListener('click',async () => {
  if (busy || savingProvider) return;
  try {await persistProvider();} catch (error) {notice(error.message,true);}
});
async function loadHashtags() {
  try {
    const data = await api('/api/captions/settings');
    savedHashtags = data.hashtags; $('captionHashtags').value = savedHashtags; hashtagsLoaded = true;
    $('captionHashtagState').textContent = savedHashtags ? 'Đã lưu' : 'Không thêm hashtag';
  } catch (error) {notice(error.message,true); $('captionHashtagState').textContent = 'Chưa tải được. Bấm Làm mới để thử lại.';}
  finally {updateSelection();}
}
async function persistHashtags() {
  if (!hashtagsLoaded) throw new Error('Chưa tải xong cài đặt hashtag.');
  if ($('captionHashtags').value === savedHashtags) return savedHashtags;
  savingHashtags = true; updateSelection();
  try {
    const data = await api('/api/captions/settings',{hashtags:$('captionHashtags').value});
    savedHashtags = data.hashtags; $('captionHashtags').value = savedHashtags;
    $('captionHashtagState').textContent = savedHashtags ? 'Đã lưu' : 'Không thêm hashtag';
    return savedHashtags;
  } finally {savingHashtags = false; updateSelection();}
}
$('captionHashtags').addEventListener('input',() => {$('captionHashtagState').textContent = 'Chưa lưu'; updateSelection();});
$('saveCaptionHashtags').addEventListener('click',async () => {
  if (busy || savingHashtags) return;
  try {await persistHashtags();} catch (error) {notice(error.message,true);}
});
function drawVideos() {
  if (libraryTable) {updateSelection(); return;}
  const fragment = document.createDocumentFragment();
  for (const video of videos) {
    const label = element('label', undefined, 'caption-video');
    const checkbox = element('input'); checkbox.type = 'checkbox'; checkbox.checked = selected.has(video.id);
    checkbox.addEventListener('change', () => {
      if (checkbox.checked) selected.add(video.id); else selected.delete(video.id);
      updateSelection();
    });
    const copy = element('span'); copy.append(element('strong', `#${video.stt ?? ''} ${video.title}`),element('span',video.caption,'caption-current'));
    copy.append(element('span',video.transcript_chars ? `Thoại đã lưu: ${video.transcript_chars.toLocaleString('vi-VN')} ký tự` : 'Chưa lưu lời thoại','hint'));
    if (video.caption_rewritten) copy.append(element('span','Đã viết lại','badge'));
    label.append(checkbox,copy); fragment.append(label);
  }
  if (!videos.length) fragment.append(element('p','Chưa có video trong thư viện.','hint'));
  $('captionVideos').replaceChildren(fragment); updateSelection();
}
async function loadVideos() {
  try {
    const data = await api('/api/captions/videos'); videos = data.videos; configured = data.configured;
    if (!initialized && preselected && videos.some(video => video.id === preselected)) selected.add(preselected);
    initialized = true;
    for (const id of selected) if (!videos.some(video => video.id === id)) selected.delete(id);
    drawApiState();
    drawVideos();
  } catch (error) {notice(error.message,true);}
}
function updateSaveAll() { if ($('saveAllCaptions')) $('saveAllCaptions').disabled = busy || ![...drafts.values()].some(draft => !draft.saved && draft.input.value !== draft.original); }
async function saveDrafts(items) {
  busy = true; updateSaveAll(); updateSelection();
  items.forEach(draft => {draft.input.disabled = true;});
  try {
    const results = [];
    for (const group of chunks(items)) {
      const payload = group.map(draft => ({video_id:draft.video_id,caption:draft.input.value,expected_caption:draft.original}));
      const data = await api('/api/captions/save',{items:payload});
      results.push(...data.results);
      for (const result of data.results) {
        const draft = drafts.get(result.video_id);
        if (!draft) continue;
        draft.feedback.textContent = result.message;
        draft.saved = result.status === 'saved'; draft.button.disabled = draft.saved;
        if (draft.saved) {draft.input.disabled = true; draft.button.textContent = 'Đã lưu';}
      }
    }
    const saved = results.filter(result => result.status === 'saved').length;
    notice(`Đã lưu ${saved}/${items.length} caption.`, saved !== items.length);
    await loadVideos();
  } catch (error) {notice(error.message,true);}
  finally {items.forEach(draft => {draft.input.disabled = draft.saved;}); busy = false; updateSaveAll(); updateSelection(); await loadVideos();}
}
function drawResults(results, append=false) {
  if (libraryTable) {
    batchResults = append ? [...batchResults,...results] : results;
    const errors = batchResults.filter(result => result.error);
    const skipped = batchResults.filter(result => result.skipped).length;
    const feedback = document.createDocumentFragment();
    if (batchResults.length) feedback.append(element('p',`Đã viết lại ${batchResults.length-errors.length-skipped}/${batchResults.length} video và lưu trực tiếp.${skipped ? ` Bỏ qua ${skipped} video đã viết lại.` : ''}`,'hint'));
    if (errors.length) {
      const details = element('details'); details.append(element('summary',`${errors.length} video cần kiểm tra`));
      for (const result of errors) {
        const row = element('p'); const link = element('a',videos.find(video => video.id===result.video_id)?.title || result.video_id);
        link.href = `/videos/${encodeURIComponent(result.video_id)}`;
        row.append(link,document.createTextNode(`: ${result.error}`)); details.append(row);
      }
      feedback.append(details);
    }
    $('captionBatchFeedback').replaceChildren(feedback);
    return;
  }
  if (!append) {drafts.clear(); $('captionResults').replaceChildren();}
  const fragment = document.createDocumentFragment();
  for (const result of results) {
    const article = element('article',undefined,'caption-draft');
    const video = videos.find(item => item.id === result.video_id);
    article.append(element('h3',video?.title || result.video_id));
    if (result.skipped) {article.append(element('p',result.message,'hint')); fragment.append(article); continue;}
    if (result.error) {article.append(element('p',result.error,'caption-error')); fragment.append(article); continue;}
    const original = element('details'); original.append(element('summary','Caption trước khi viết lại'),element('p',result.original,'caption-current')); article.append(original);
    if (result.transcript_used) {
      const dialogue = element('details');
      dialogue.append(element('summary',`Lời thoại đã gửi (${result.transcript_chars.toLocaleString('vi-VN')} ký tự)`),element('p',result.transcript,'caption-current'));
      article.append(dialogue);
      if (result.transcript_shortened) article.append(element('p',`Chỉ gửi ${result.transcript_chars} ký tự đầu trong ${result.transcript_total_chars.toLocaleString('vi-VN')} ký tự thoại. Bản đầy đủ vẫn được giữ.`,'hint'));
    }
    const label = element('label','Caption mới'); label.htmlFor = `draft-${result.video_id}`;
    const input = element('textarea'); input.id = label.htmlFor; input.rows = 5; input.maxLength = 10000; input.value = result.caption;
    const feedback = element('p','','hint'); const button = element('button','Lưu caption này','secondary'); button.type = 'button';
    const draft = {...result,original:result.saved ? result.caption : result.original,input,feedback,button,saved:false}; drafts.set(result.video_id,draft);
    button.disabled = result.saved === true;
    input.addEventListener('input',() => {button.disabled = input.value === draft.original; updateSaveAll();});
    button.addEventListener('click',async () => {if (busy) return; button.disabled = true; await saveDrafts([draft]); button.disabled = draft.saved;});
    article.append(label,input,feedback,button); fragment.append(article);
  }
  $('captionResults').append(fragment); updateSaveAll();
  if ($('captionDrafts') && results.length) $('captionDrafts').open = true;
}
if (libraryTable) {
  window.addEventListener('library:updated',event => {
    videos = event.detail;
    const ids = new Set(videos.map(video => video.id));
    for (const id of selected) if (!ids.has(id)) selected.delete(id);
    updateSelection();
  });
  libraryTable.addEventListener('change',event => {
    const input = event.target.closest('input[data-caption-video]');
    if (!input || busy) return;
    if (input.checked) selected.add(input.dataset.captionVideo); else selected.delete(input.dataset.captionVideo);
    updateSelection();
  });
  libraryTable.addEventListener('click',event => {
    const button = event.target.closest('[data-caption-rewrite]');
    if (!button || busy) return;
    runRewrite([button.dataset.captionRewrite]);
  });
}
$('captionSelectAll').addEventListener('change',event => {selected.clear(); if (event.target.checked) videos.forEach(video => selected.add(video.id)); drawVideos();});
$('captionRewriteMode').addEventListener('change',updateSelection);
$('rewriteCaptions').addEventListener('click',() => runRewrite());
async function runRewrite(rowIds=null) {
  if (busy || savingProvider || savingHashtags || (!rowIds && !selected.size)) return;
  if (!providerLoaded || !hashtagsLoaded) {notice('Đang tải cấu hình. Hãy thử lại sau giây lát.',true); return;}
  if ([...drafts.values()].some(draft => !draft.saved && draft.input.value !== draft.original) && !confirm('Bạn có chỉnh sửa thủ công chưa lưu. Tiếp tục viết lại?')) return;
  const includeTranscript = $('captionUseTranscript').checked;
  const ids = rowIds || eligibleIds();
  if (!ids.length) {notice('Không có video cần viết lại trong lựa chọn hiện tại.'); return;}
  const mode = rowIds ? 'all' : $('captionRewriteMode').value;
  const groups = chunks(ids);
  const instruction = $('captionInstruction').value;
  activeRowId = rowIds?.[0] ?? null;
  busy = true; updateSelection(); updateSaveAll(); $('captionUseTranscript').disabled = true;
  $('rewriteCaptions').textContent = includeTranscript ? 'Đang nhận diện thoại & viết caption…' : 'AI đang viết…';
  $('captionInstruction').disabled = true;
  drawResults([]);
  try {
    await persistProvider();
    const hashtags = await persistHashtags();
    let finished = 0;
    for (let index=0; index<groups.length; index++) {
      $('rewriteCaptions').textContent = `Batch ${index+1}/${groups.length} (${finished}/${ids.length})…`;
      const data = await api('/api/captions/rewrite',{video_ids:groups[index],instruction,include_transcript:includeTranscript,rewrite_mode:mode,hashtags});
      drawResults(data.results,true);
      finished += groups[index].length;
      await loadVideos();
      if (libraryTable) await window.fetchVideos();
    }
    notice(`Đã xử lý ${finished} video trong ${groups.length} batch. Caption thành công đã lưu trực tiếp.`);
  }
  catch (error) {notice(error.message,true);}
  finally {busy = false; activeRowId = null; $('captionUseTranscript').disabled = false; $('captionInstruction').disabled = false; $('rewriteCaptions').textContent = 'Viết lại caption'; updateSelection(); updateSaveAll();}
}
$('saveAllCaptions')?.addEventListener('click',() => {if (!busy) saveDrafts([...drafts.values()].filter(draft => !draft.saved));});
startPolling(() => {});
$('refreshStatus').addEventListener('click',loadVideos);
$('refreshStatus').addEventListener('click',() => {if (!hashtagsLoaded) loadHashtags();});
$('refreshStatus').addEventListener('click',() => {if (!providerLoaded) loadProvider();});
loadProvider();
loadHashtags();
loadVideos();
