from concurrent.futures import ThreadPoolExecutor
from flask import Blueprint, jsonify, request
import database
from .client import rewrite_captions, CaptionError, MAX_TRANSCRIPT_CHARS
from .transcripts import dialogue_for_video
from .hashtags import normalize_hashtags, finish_caption
from .provider import public_provider, resolve_provider

captions = Blueprint('captions', __name__)


def was_rewritten(video):
    return bool(video.get('caption_ai') or video.get('caption_ai_saved_at') or video.get('caption'))


def caption_store():
    from services.social.routes import get_store
    return get_store()


@captions.get('/api/captions/settings')
def settings():
    return jsonify(status='success',hashtags=caption_store().get_caption_hashtags())


@captions.post('/api/captions/settings')
def save_settings():
    value=caption_store().save_caption_hashtags(request.get_json().get('hashtags'))
    return jsonify(status='success',hashtags=value)


@captions.get('/api/captions/provider')
def provider_settings():
    return jsonify(status='success',**public_provider(caption_store()))


@captions.post('/api/captions/provider')
def save_provider_settings():
    store=caption_store()
    store.save_caption_provider(request.get_json())
    return jsonify(status='success',**public_provider(store))


@captions.errorhandler(ValueError)
def invalid(error):
    return jsonify(status='error',message=str(error)),400


@captions.before_request
def validate_json():
    if request.method == 'POST' and (not request.is_json or not isinstance(request.get_json(silent=True),dict)):
        return jsonify(status='error',message='Cần gửi một JSON object hợp lệ.'),400


@captions.get('/api/captions/videos')
def videos():
    items = [{'id':v['id'],'title':v.get('title',''),'caption':v.get('caption',v.get('title','')),
              'status':v.get('status'),'stt':v.get('stt'),
              'caption_rewritten':was_rewritten(v),
              'caption_rewrite_state':'saved' if was_rewritten(v) else 'new',
              'transcript_chars':len(v.get('transcript','')) if isinstance(v.get('transcript'),str) else 0} for v in database.get_all_videos()]
    provider=public_provider(caption_store())
    return jsonify(status='success',videos=items,configured=provider['configured'],model=provider['model'])


@captions.post('/api/captions/rewrite')
def rewrite():
    body=request.get_json()
    ids=body.get('video_ids')
    instruction=body.get('instruction','')
    include_transcript=body.get('include_transcript',False)
    rewrite_mode=body.get('rewrite_mode','all')
    if rewrite_mode not in ('all','unwritten'):
        raise ValueError('Chọn viết lại tất cả hoặc chỉ video chưa viết lại.')
    if type(include_transcript) is not bool:
        raise ValueError('Lựa chọn dùng lời thoại phải là bật hoặc tắt.')
    if not isinstance(ids,list) or not 1 <= len(ids) <= 100 or any(not isinstance(i,str) or not i for i in ids):
        raise ValueError('Mỗi batch từ 1 đến 100 video.')
    if len(set(ids)) != len(ids):
        raise ValueError('Danh sách video bị trùng.')
    if not isinstance(instruction,str) or len(instruction)>2000:
        raise ValueError('Yêu cầu viết lại tối đa 2.000 ký tự.')
    hashtags=normalize_hashtags(body['hashtags'] if 'hashtags' in body else caption_store().get_caption_hashtags())
    provider=resolve_provider(caption_store())
    def process(video_id):
        video=database.get_video(video_id)
        if not video:
            return {'video_id':video_id,'error':'Video đã bị xóa.'}
        if rewrite_mode=='unwritten' and was_rewritten(video):
            return {'video_id':video_id,'skipped':True,'message':'Video đã viết lại, bỏ qua.'}
        original=video.get('caption',video.get('title',''))
        if not isinstance(original,str) or not original.strip() or len(original)>10000:
            return {'video_id':video_id,'error':'Caption gốc không hợp lệ.'}
        try:
            transcript=dialogue_for_video(video_id) if include_transcript else ''
            total_chars=len(transcript)
            transcript=transcript[:MAX_TRANSCRIPT_CHARS]
            return {'video_id':video_id,'original':original,
                    'transcript_total_chars':total_chars,'transcript_shortened':total_chars>len(transcript),
                    'transcript_used':bool(transcript),'transcript_chars':len(transcript),'transcript':transcript}
        except CaptionError as error:
            return {'video_id':video_id,'error':str(error)}
    with ThreadPoolExecutor(max_workers=3) as pool:
        results=list(pool.map(process,ids))
    valid=[item for item in results if 'error' not in item and not item.get('skipped')]
    if valid:
        try:
            generated=rewrite_captions(valid,instruction,model=provider['model'],api_key=provider['api_key'])
            for item in valid:
                item.update(generated[item['video_id']])
                if 'error' not in item:
                    try:
                        item['caption']=finish_caption(item['caption'],hashtags)
                    except ValueError as error:
                        item['error']=str(error)
        except CaptionError as error:
            for item in valid:
                item['error']=str(error)
        database.apply_caption_results(valid)
    return jsonify(status='success',results=results)


@captions.post('/api/captions/save')
def save():
    items=request.get_json().get('items')
    if not isinstance(items,list) or not 1 <= len(items) <= 100 or any(not isinstance(item,dict) for item in items):
        raise ValueError('Mỗi batch từ 1 đến 100 caption để lưu.')
    results=[]
    for item in items:
        video_id=item.get('video_id')
        caption=item.get('caption')
        expected=item.get('expected_caption')
        if not isinstance(video_id,str) or not isinstance(caption,str) or not caption.strip() or len(caption)>10000 or not isinstance(expected,str):
            results.append({'video_id':video_id if isinstance(video_id,str) else '', 'status':'error','message':'Caption hoặc video không hợp lệ.'})
            continue
        status=database.update_video_caption(video_id,caption.strip(),expected)
        results.append({'video_id':video_id,'status':status,'message':{'saved':'Đã lưu','conflict':'Caption đã thay đổi ở nơi khác. Tải lại trước khi lưu.','missing':'Video đã bị xóa.'}[status]})
    return jsonify(status='success',results=results)
