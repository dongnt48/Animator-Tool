"""Local model/credential settings; only public status leaves the server."""
import re
from .client import MODEL, configured_key


def validate_provider_update(body):
    updates={}
    if 'model' in body:
        model=body['model']
        if not isinstance(model,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}',model.strip()):
            raise ValueError('Tên model không hợp lệ (tối đa 200 ký tự, không chứa khoảng trắng).')
        updates['model']=model.strip()
    if 'api_key' in body:
        key=body['api_key']
        if not isinstance(key,str) or len(key)>512:
            raise ValueError('API key không hợp lệ (tối đa 512 ký tự).')
        key=key.strip()
        if any(ord(char)<=32 or ord(char)>126 for char in key):
            raise ValueError('API key không được chứa khoảng trắng hoặc ký tự điều khiển.')
        if key:
            updates['api_key']=key
    if not any(field in body for field in ('model','api_key')):
        raise ValueError('Cần nhập model hoặc API key.')
    return updates


def resolve_provider(store):
    value=store.get_caption_provider()
    return {'model':value.get('model') or MODEL,'api_key':value.get('api_key') or configured_key(),
            'has_saved_key':bool(value.get('api_key'))}


def public_provider(store):
    value=resolve_provider(store)
    return {'model':value['model'],'configured':bool(value['api_key']),'has_saved_key':value['has_saved_key']}
