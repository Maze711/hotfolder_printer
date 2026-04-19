from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os

from logging_utils import get_logger


logger = get_logger(__name__)

class Handler(FileSystemEventHandler):
    def __init__(self, config, queue):
        self.config = config
        self.queue = queue

    def _enqueue_if_image(self, src_path):
        file_path = os.path.abspath(src_path)
        if not file_path.lower().endswith((".jpg", ".png", ".jpeg")):
            return

        job = {
            "file": file_path,
            "config": self.config,
        }
        self.queue.add_job(job)

    def on_created(self, event):
        if event.is_directory:
            return

        self._enqueue_if_image(event.src_path)

    def on_moved(self, event):
        if event.is_directory:
            return

        self._enqueue_if_image(event.dest_path)

    def on_modified(self, event):
        if event.is_directory:
            return

        self._enqueue_if_image(event.src_path)

def start_watcher(folder, config, queue):
    os.makedirs(folder, exist_ok=True)

    event_handler = Handler(config, queue)
    observer = Observer()
    observer.schedule(event_handler, folder, recursive=False)
    observer.start()

    logger.info("[WATCHING] %s", folder)

    return observer