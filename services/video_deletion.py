"""Persist a tombstone before removing media, using only bounded local paths."""
import hashlib
from pathlib import Path
import re

import database


def _path(root, name):
    if not isinstance(name, str) or not name or '/' in name or '\\' in name:
        return None
    candidate = root/name
    if candidate.is_symlink():
        return None
    path = candidate.resolve()
    return path if path.parent == root else None


def delete_media(video, downloads, outputs, static, covers=None):
    roots = {'downloads': Path(downloads).resolve(), 'outputs': Path(outputs).resolve(),
             'thumbnails': (Path(static)/'thumbnails').resolve(),
             'thumbnail_cache': (Path(static).parent/'data/social/thumbnails').resolve()}
    roots['covers'] = Path(covers or Path(static).parent/'data/social/covers').resolve()
    active_others = [v for v in database.get_all_videos() if v['id'] != video['id']]
    protected = set()
    for other in active_others:
        protected.update([('downloads', other.get('video_filename')),
                          ('outputs', other.get('output_filename')),
                          ('thumbnails', (other.get('thumbnail') or '').removeprefix('/static/thumbnails/'))])
    manifest = {(item['root'], item['name']) for item in video.get('deleted_media', [])
                if isinstance(item, dict) and item.get('root') in roots and isinstance(item.get('name'), str)}
    for root, name in [('downloads', video.get('video_filename')), ('outputs', video.get('output_filename'))]:
        if name:
            manifest.add((root, name))
    thumbnail = video.get('thumbnail') or ''
    if thumbnail.startswith('/static/thumbnails/'):
        manifest.add(('thumbnails', thumbnail.removeprefix('/static/thumbnails/')))
    pattern = re.compile(r'(?:^|_)' + re.escape(video['id']) + r'(?:_|\.|$)')
    other_patterns = [re.compile(r'(?:^|_)' + re.escape(v['id']) + r'(?:_|\.|$)')
                      for v in database.get_all_videos(include_deleted=True)
                      if v['id'] != video['id'] and len(v['id']) > len(video['id'])]
    if roots['outputs'].is_dir():
        for path in roots['outputs'].glob('*.mp4'):
            if pattern.search(path.name) and not any(p.search(path.name) for p in other_patterns):
                manifest.add(('outputs', path.name))
    if roots['covers'].is_dir():
        for path in roots['covers'].glob('*.jpg'):
            if path.name.startswith('cover_'+video['id']+'_'):
                manifest.add(('covers', path.name))
    # Derive cached JPEG names while the source file's fingerprint still exists.
    for root, name in list(manifest):
        path = _path(roots[root], name)
        if root in ('downloads', 'outputs') and path and path.is_file():
            stat = path.stat()
            key = hashlib.sha256(f'{path}:{stat.st_size}:{stat.st_mtime_ns}'.encode()).hexdigest()
            manifest.add(('thumbnail_cache', key+'.jpg'))
    digest = video.get('source_hash', '')
    original = _path(roots['downloads'], video.get('video_filename'))
    if not digest and original and original.is_file():
        with original.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    database.delete_video(video['id'], source_hash=digest,
                          deleted_media=[{'root': root, 'name': name} for root, name in sorted(manifest)],
                          reject_processing=True)
    errors, shared = [], []
    for root, name in sorted(manifest):
        if (root, name) in protected:
            shared.append(name)
            continue
        path = _path(roots[root], name)
        if path is None:
            continue
        try:
            path.unlink(missing_ok=True)
        except OSError:
            errors.append(name)
    return errors, shared
