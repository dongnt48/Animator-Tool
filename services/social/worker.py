"""Run with python -m services.social.worker; never starts merely by importing Flask."""
import logging
import os
import time
import threading
import uuid
from pathlib import Path
from .store import Store, media_hash
from .browser import BrowserPublisher, LoginRequired, valid_permalink
from .daily import DailyScheduler

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / 'data' / 'social'


def data_dir():
    return Path(os.environ.get('SOCIAL_DATA_DIR', str(DEFAULT_DATA_DIR))).resolve()


class Worker:
    def __init__(self, store, publisher=None):
        self.store = store
        self.owner = 'worker:' + uuid.uuid4().hex
        self.publisher = publisher or BrowserPublisher(store.path.parent, cover_reporter=lambda task, state, message:
            self.store.set_cover_result(task['id'], self.owner, state, message))

    def run_once(self, now=None):
        self.store.heartbeat()
        task = self.store.claim_next(self.owner, now=now)
        if task is None:
            return False
        stop = threading.Event()
        def keep_alive():
            while not stop.wait(5):
                try:
                    self.store.heartbeat(task['id'])
                except Exception:
                    logging.exception('Worker heartbeat failed')
        pulse = threading.Thread(target=keep_alive, daemon=True)
        pulse.start()
        try:
            if not Path(task['media_path']).is_file():
                raise ValueError('Video đã bị xóa. Hãy tạo lịch mới từ video hiện có.')
            if media_hash(task['media_path']) != task['media_hash']:
                raise ValueError('File video đã thay đổi sau khi lên lịch. Hãy tạo lịch mới để xác nhận nội dung.')
            for shape in ('portrait', 'landscape'):
                if task.get('cover'):
                    cover_path = Path(task['cover'][shape+'_path']).resolve(strict=True)
                    if cover_path.parent != self.store.path.parent/'media' or media_hash(cover_path) != task['cover'][shape+'_hash']:
                        raise ValueError('Ảnh bìa đã thay đổi sau khi lên lịch. Tạo lịch mới để xác nhận ảnh.')
            receipt = self.publisher(task, lambda: self.store.mark_submitting(task['id'], self.owner))
            if not valid_permalink(task['platform'], receipt.url):
                raise ValueError('Chưa có link bài hợp lệ từ nền tảng.')
            self.store.finish(task['id'], self.owner, 'published', receipt.message, receipt.url)
        except Exception as exc:
            state = 'needs_login' if isinstance(exc, LoginRequired) else 'failed'
            if self.store.task_state(task['id']) == 'submitting':
                state = 'needs_review'
            self.store.finish(task['id'], self.owner, state, str(exc))
        finally:
            stop.set()
            pulse.join(timeout=2)
            self.store.heartbeat()
        return True


class WorkerLock:
    """OS-held lock: released on process exit, including crashes."""
    def __init__(self, path):
        self.path = Path(path)
        self.stream = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.stream = open(self.path, 'a+b')
        if self.stream.tell() == 0:
            self.stream.write(b'0')
            self.stream.flush()
        self.stream.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.stream.close()
            raise RuntimeError('Đã có worker đăng bài đang chạy.') from None
        return self

    def __exit__(self, *args):
        self.stream.close()


def main():
    logging.basicConfig(level=logging.INFO)
    root = data_dir()
    try:
        with WorkerLock(root / 'worker.lock'):
            store = Store(root / 'social.sqlite3')
            store.recover_interrupted()
            worker = Worker(store)
            logging.info('Social publishing worker ready. Keep this computer awake and online.')
            stop = threading.Event()
            daily = threading.Thread(target=DailyScheduler(store).run, args=(stop,), daemon=True)
            daily.start()
            try:
                while True:
                    worker.run_once()
                    time.sleep(2)
            finally:
                stop.set()
                daily.join(timeout=5)
    except KeyboardInterrupt:
        return


if __name__ == '__main__':
    main()
