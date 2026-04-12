from collections import deque
import threading
import time

class PrintQueue:
    def __init__(self):
        self.queue = deque()
        self.lock = threading.Lock()
        self.running = True

    def add_job(self, job):
        with self.lock:
            self.queue.append(job)
            print(f"[QUEUE] Job added: {job['file']}")

    def get_job(self):
        with self.lock:
            if self.queue:
                return self.queue.popleft()
        return None

    def worker(self, processor_func):
        print("[QUEUE] Worker started")

        while self.running:
            job = self.get_job()

            if job:
                try:
                    processor_func(job)
                except Exception as e:
                    print(f"[ERROR] Job failed: {e}")
            else:
                time.sleep(0.5)

    def start(self, processor_func):
        t = threading.Thread(target=self.worker, args=(processor_func,))
        t.daemon = True
        t.start()