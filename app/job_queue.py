from collections import deque
import os
import threading
import time

from logging_utils import get_logger


logger = get_logger(__name__)


class PrintQueue:
    def __init__(self):
        self.queue = deque()
        self.lock = threading.Lock()
        self.running = True
        self.in_queue = set()
        self.in_progress = set()
        self.last_processed_signature = {}
        self.pending_by_folder = {}
        self.pending_keys = set()

    @staticmethod
    def _job_key(file_path):
        return os.path.abspath(file_path).lower()

    def _get_file_signature(self, file_path):
        stats = os.stat(file_path)
        return (stats.st_size, stats.st_mtime_ns)

    def _folder_key(self, config):
        base_path = config.get("base_path")
        if base_path:
            return os.path.abspath(base_path).lower()
        input_path = config.get("input")
        if input_path:
            return os.path.abspath(input_path).lower()
        return "default"

    def _required_images(self, config):
        raw_value = config.get("images_per_template", 1)
        try:
            required = int(raw_value)
        except (TypeError, ValueError) as exc:
            raise ValueError("images_per_template must be an integer") from exc

        if required <= 0:
            raise ValueError("images_per_template must be > 0")

        return required

    def _enqueue_pending_file(self, config, file_path):
        key = self._job_key(file_path)
        folder = self._folder_key(config)

        with self.lock:
            if key in self.pending_keys:
                pending_count = len(self.pending_by_folder.get(folder, []))
                return None, pending_count

            pending = self.pending_by_folder.setdefault(folder, [])
            pending.append(file_path)
            self.pending_keys.add(key)
            return None, len(pending)

    def _try_get_pending_batch(self, config, required):
        folder = self._folder_key(config)

        with self.lock:
            pending = self.pending_by_folder.get(folder, [])
            if len(pending) < required:
                return None

            batch = pending[:required]
            self.pending_by_folder[folder] = pending[required:]

            for path in batch:
                self.pending_keys.discard(self._job_key(path))

            return batch

    def _wait_until_file_ready(self, file_path, timeout_seconds=20, check_interval=0.3, stable_checks=3):
        deadline = time.time() + timeout_seconds
        last_signature = None
        stable_count = 0

        while time.time() < deadline:
            try:
                signature = self._get_file_signature(file_path)
                with open(file_path, "rb") as _f:
                    _f.read(1)
            except OSError:
                time.sleep(check_interval)
                continue

            if signature == last_signature:
                stable_count += 1
            else:
                stable_count = 1
                last_signature = signature

            if stable_count >= stable_checks:
                return True

            time.sleep(check_interval)

        return False

    def add_job(self, job):
        file_path = job.get("file")
        if not file_path:
            logger.error("[QUEUE ERROR] Job missing file path")
            return

        key = self._job_key(file_path)

        with self.lock:
            if key in self.in_queue or key in self.in_progress:
                logger.info("[QUEUE] Duplicate ignored: %s", file_path)
                return

            self.queue.append(job)
            self.in_queue.add(key)
            logger.info("[QUEUE] Job added: %s", file_path)

    def get_job(self):
        with self.lock:
            if self.queue:
                job = self.queue.popleft()
                key = self._job_key(job["file"])
                self.in_queue.discard(key)
                self.in_progress.add(key)
                return job
        return None

    def _release_job(self, file_path):
        key = self._job_key(file_path)
        with self.lock:
            self.in_progress.discard(key)

    def _mark_processed(self, file_path):
        key = self._job_key(file_path)
        try:
            signature = self._get_file_signature(file_path)
        except OSError:
            return

        with self.lock:
            self.last_processed_signature[key] = signature

            if len(self.last_processed_signature) > 2000:
                oldest_key = next(iter(self.last_processed_signature.keys()))
                self.last_processed_signature.pop(oldest_key, None)

    def _was_already_processed(self, file_path):
        key = self._job_key(file_path)
        try:
            signature = self._get_file_signature(file_path)
        except OSError:
            return False

        with self.lock:
            return self.last_processed_signature.get(key) == signature

    def worker(self, processor_func):
        logger.info("[QUEUE] Worker started")

        while self.running:
            job = self.get_job()

            if job:
                file_path = job["file"]
                try:
                    if not os.path.exists(file_path):
                        logger.error("[READINESS ERROR] File not found: %s", file_path)
                        continue

                    if not self._wait_until_file_ready(file_path):
                        logger.error("[READINESS ERROR] Timed out waiting for file copy: %s", file_path)
                        continue

                    if self._was_already_processed(file_path):
                        logger.info("[QUEUE] Skipping already-processed file: %s", file_path)
                        continue

                    required_images = self._required_images(job["config"])

                    if required_images > 1:
                        _, pending_count = self._enqueue_pending_file(job["config"], file_path)
                        batch_files = self._try_get_pending_batch(job["config"], required_images)

                        if not batch_files:
                            logger.error(
                                "[BATCH ERROR] %s requires %s image(s) per template. Waiting (%s/%s).",
                                job["config"].get("name", "hotfolder"),
                                required_images,
                                pending_count,
                                required_images,
                            )
                            continue

                        batch_job = {
                            "file": batch_files[0],
                            "files": batch_files,
                            "config": job["config"],
                        }
                        processor_func(batch_job)

                        for batch_file in batch_files:
                            self._mark_processed(batch_file)
                        continue

                    processor_func(job)
                    self._mark_processed(file_path)
                except Exception as e:
                    logger.exception("[ERROR] Job failed for %s: %s", file_path, e)
                finally:
                    self._release_job(file_path)
            else:
                time.sleep(0.1)

    def start(self, processor_func):
        t = threading.Thread(target=self.worker, args=(processor_func,), name="print-queue-worker")
        t.daemon = True
        t.start()