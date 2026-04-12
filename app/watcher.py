from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time

class Handler(FileSystemEventHandler):
    def __init__(self, config, queue):
        self.config = config
        self.queue = queue

    def on_created(self, event):
        if event.is_directory:
            return

        if event.src_path.lower().endswith(('.jpg', '.png', '.jpeg')):
            job = {
                "file": event.src_path,
                "config": self.config
            }

            self.queue.add_job(job)

def start_watcher(folder, config, queue):
    event_handler = Handler(config, queue)
    observer = Observer()
    observer.schedule(event_handler, folder, recursive=False)
    observer.start()

    print(f"[WATCHING] {folder}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()