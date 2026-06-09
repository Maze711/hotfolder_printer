"""Log service – tails hotfolder_printer.log and emits Qt signals.

The service runs a QTimer that reads any newly appended lines and parses
them into higher‑level events for the UI.
"""

import os
import re
from PyQt5 import QtCore

# Determine PROJECT_ROOT (two levels up from this file: app/services -> app -> root)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))

LOG_PATH = os.path.join(PROJECT_ROOT, "logs", "hotfolder_printer.log")

class LogService(QtCore.QObject):
    # Signals emitted for UI consumption
    new_log_line        = QtCore.pyqtSignal(str)                     # raw line
    job_added           = QtCore.pyqtSignal(str)                     # input file path
    job_processing      = QtCore.pyqtSignal(str)                     # file path started processing
    job_completed       = QtCore.pyqtSignal(str)                     # output path (saved)
    job_ready           = QtCore.pyqtSignal(str)                     # output path ready for review
    job_print_started   = QtCore.pyqtSignal(str)                     # output path – print initiated
    job_print_completed = QtCore.pyqtSignal(str)                     # output path – print submitted
    printer_update      = QtCore.pyqtSignal(str, str)                # printer name, mode/status
    preset_loaded       = QtCore.pyqtSignal(str)                     # preset folder path

    def __init__(self, parent=None):
        super().__init__(parent)
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(500)  # poll twice a second
        self._timer.timeout.connect(self._poll)
        self._file = None
        self._position = 0
        # Compile regexes once for speed
        self._re_job_added       = re.compile(r"\[QUEUE\] Job added: (.+)$")
        self._re_processing      = re.compile(r"\[QUEUE\] Worker started processing (.+)$")
        self._re_saved           = re.compile(r"\[SAVED\] (.+)$")
        self._re_print           = re.compile(r"\[PRINT\] Preparing print job: (.+) \(mode=(.+)\)")
        self._re_print_started   = re.compile(r"\[PRINT\] Started (.+)$")
        self._re_print_completed = re.compile(r"\[PRINT\] Completed (.+)$")
        self._re_loaded          = re.compile(r"\[LOADED\] (.+)$")

    def start(self):
        """Open the log file and start the polling timer.
        The file is opened in binary mode and the cursor is placed at the end
        so that only new lines are emitted.
        """
        # Ensure directory exists
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        # Open (or create) the log file
        self._file = open(LOG_PATH, "rb")
        self._file.seek(0, os.SEEK_END)
        self._position = self._file.tell()
        self._timer.start()

    def _poll(self):
        if not self._file:
            return
        self._file.seek(self._position)
        data = self._file.read()
        if not data:
            return
        self._position = self._file.tell()
        try:
            text = data.decode("utf-8", errors="replace")
        except Exception:
            text = ""
        lines = text.splitlines()
        for line in lines:
            self.new_log_line.emit(line)
            self._parse(line)

    # ------------------------------------------------------------------ parsing
    def _parse(self, line: str):
        m = self._re_job_added.search(line)
        if m:
            self.job_added.emit(m.group(1))
            return
        m = self._re_processing.search(line)
        if m:
            self.job_processing.emit(m.group(1))
            return
        m = self._re_saved.search(line)
        if m:
            # Emit a signal when a job is saved and ready for review
            self.job_ready.emit(m.group(1))
            return
        m = self._re_print.search(line)
        if m:
            self.printer_update.emit(m.group(1), m.group(2))
            return
        m = self._re_print_started.search(line)
        if m:
            self.job_print_started.emit(m.group(1))
            return
        m = self._re_print_completed.search(line)
        if m:
            self.job_print_completed.emit(m.group(1))
            return
        m = self._re_loaded.search(line)
        if m:
            self.preset_loaded.emit(m.group(1))
            return
