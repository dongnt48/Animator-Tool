"""Stable source identity retained even after local media is removed."""
import re
from urllib.parse import urlsplit, urlunsplit


def source_id(url='', filename='', explicit=''):
    if isinstance(explicit, str) and re.fullmatch(r'\d+', explicit):
        return explicit
    if isinstance(url, str):
        try:
            parsed = urlsplit(url if '://' in url else 'https://' + url)
        except ValueError:
            return ''
        if (parsed.hostname or '').lower().endswith('.tiktok.com') or (parsed.hostname or '').lower() == 'tiktok.com':
            match = re.search(r'/(?:video|photo)/(\d+)(?:/|$)', parsed.path)
            if match:
                return match.group(1)
    match = re.fullmatch(r'tiktok_(\d+)(?:_[A-Za-z0-9]+)?\.mp4', filename if isinstance(filename, str) else '')
    return match.group(1) if match else ''


def video_url(url):
    if not isinstance(url, str) or not url.strip():
        return ''
    try:
        parsed = urlsplit(url.strip() if '://' in url else 'https://' + url.strip())
    except ValueError:
        return ''
    host = (parsed.hostname or '').lower()
    if host not in ('tiktok.com', 'www.tiktok.com', 'm.tiktok.com', 'vt.tiktok.com', 'vm.tiktok.com'):
        return ''
    if not source_id(url) and host not in ('vt.tiktok.com', 'vm.tiktok.com'):
        return ''  # A channel scan is not an individual video reservation.
    if host in ('tiktok.com', 'www.tiktok.com', 'm.tiktok.com'):
        host = 'www.tiktok.com'
    return urlunsplit(('https', host, parsed.path.rstrip('/'), '', ''))


def identity_keys(url='', filename='', explicit='', digest=''):
    number = source_id(url, filename, explicit)
    normalized = video_url(url)
    keys = set()
    if number:
        keys.add(('source_id', number))
    if normalized:
        keys.add(('url', normalized))
    if isinstance(digest, str) and re.fullmatch(r'[a-fA-F0-9]{64}', digest):
        keys.add(('hash', digest.lower()))
    return keys
