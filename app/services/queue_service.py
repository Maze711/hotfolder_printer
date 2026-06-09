"""Queue service – maintains the in‑memory job list for the dashboard.

It receives events from ``LogService`` (job_added, job_processing, job_completed)
and also performs a periodic filesystem scan to capture jobs that existed before
the UI started. The service caps the stored jobs at ``MAX_JOBS = 200`` to keep
the UI responsive.
"""

import os
import collections
from datetime import datetime
from PyQt5 import QtCore

# Determine PROJECT_ROOT (two levels up from this file: app/services -> app -> root)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))

MAX_JOBS = 200

class QueueService(QtCore.QObject):
    def clear(self):
        """Clear all jobs and reset counters to zero.
        This is used by the UI "Clear Queue" action to empty the table.
        """
        self._jobs.clear()
        # Emit an empty job list and zero counters
        self.jobs_updated.emit({})
        self.counters_updated.emit(0, 0, 0)
    # Signals emitted to UI
    jobs_updated = QtCore.pyqtSignal(dict)            # {filepath: {"status": str, "ts": str}}
    counters_updated = QtCore.pyqtSignal(int, int, int)  # pending, processing, completed

    def __init__(self, parent=None):
        super().__init__(parent)
        self._jobs = collections.OrderedDict()  # preserve insertion order (oldest -> newest)
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(5000)  # refresh every 5 seconds
        self._timer.timeout.connect(self.refresh)

    # ------------------------------------------------------------------ signal slots
    @QtCore.pyqtSlot(str)
    def handle_job_added(self, path: str):
        self._set_job(path, "Pending")

    @QtCore.pyqtSlot(str)
    def handle_job_processing(self, path: str):
        self._set_job(path, "Processing")

    @QtCore.pyqtSlot(str)
    def handle_job_ready(self, path: str):
        """Mark job as pending review when output is ready."""
        self._set_job(path, "Pending Review")

    @QtCore.pyqtSlot(str)
    def reject_job(self, path: str):
        """Mark job as rejected and remove it from the UI queue."""
        self._set_job(path, "Rejected")




    # ------------------------------------------------------------------ internal helpers
    def _set_job(self, path: str, status: str):
        ts = datetime.now().strftime("%H:%M:%S")
        if path in self._jobs:
            self._jobs[path]["status"] = status
            self._jobs[path]["ts"] = ts
        else:
            self._jobs[path] = {"status": status, "ts": ts}
        # Trim to MAX_JOBS (remove oldest entries first)
        while len(self._jobs) > MAX_JOBS:
            self._jobs.popitem(last=False)
        self._emit_updates()

    def _emit_updates(self):
        # Emit shallow copy for safety
        self.jobs_updated.emit(dict(self._jobs))
        # Compute counters
        pending = sum(1 for v in self._jobs.values() if v["status"] == "Pending")
        processing = sum(1 for v in self._jobs.values() if v["status"] == "Processing")
        completed = sum(1 for v in self._jobs.values() if v["status"] == "Completed")
        self.counters_updated.emit(pending, processing, completed)

    # ------------------------------------------------------------------ periodic filesystem scan
    def refresh(self):
        """Walk ``hotfolders/*/input`` and ``hotfolders/*/output`` to ensure the UI
        sees any jobs that were present before the UI launched.
        """
        base = os.path.join(PROJECT_ROOT, "hotfolders")
        if not os.path.isdir(base):
            return
        for root, _, files in os.walk(base):
            for name in files:
                if not name.lower().endswith(('.jpg', '.jpeg', '.png')):
                    continue
                full = os.path.join(root, name)
                if "input" in root:
                    if full not in self._jobs:
                        self._set_job(full, "Pending")
                elif "output" in root:
                    # Mark as completed regardless of prior state
                    self._set_job(full, "Completed")
        # No extra emit needed – _set_job already emitted

    def start_periodic_refresh(self):
        self._timer.start()
        self.refresh()
