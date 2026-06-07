"""Main dashboard window for the hotfolder printer.

It brings together the three UI widgets (status panel, job table, log view)
and the three services (log, queue, printer). The UI is read‑only – it does
not modify the backend logic other than toggling the soft‑pause flag via
``system_state.json``.
"""

import sys
from PyQt5 import QtWidgets, QtCore

# Local imports – the UI package lives under ``app.ui`` and the services
# under ``app.services``.
from .status_panel import StatusPanel
from .queue_table import QueueTable
from .log_viewer import LogViewer

from ..services.log_service import LogService
from ..services.queue_service import QueueService
from ..services.printer_service import PrinterService

class Dashboard(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hotfolder Printer – Monitoring Dashboard")
        self.resize(1100, 720)
        self._setup_ui()
        self._setup_services()
        self._connect_signals()
        self._start()

    # --------------------------------------------------------------------- UI layout
    def _setup_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Top status panel
        self.status_panel = StatusPanel()
        layout.addWidget(self.status_panel)

        # Job table (takes most vertical space)
        self.job_table = QueueTable()
        layout.addWidget(self.job_table, stretch=3)

        # Log viewer (bottom)
        self.log_viewer = LogViewer()
        layout.addWidget(self.log_viewer, stretch=2)

        # Toolbar with actions
        toolbar = QtWidgets.QToolBar()
        self.addToolBar(toolbar)
        self.pause_action = QtWidgets.QAction("Pause Queue", self)
        self.resume_action = QtWidgets.QAction("Resume Queue", self)
        self.refresh_action = QtWidgets.QAction("Refresh", self)
        toolbar.addAction(self.pause_action)
        toolbar.addAction(self.resume_action)
        toolbar.addSeparator()
        toolbar.addAction(self.refresh_action)

        # Connect button clicks
        self.pause_action.triggered.connect(self._pause_queue)
        self.resume_action.triggered.connect(self._resume_queue)
        self.refresh_action.triggered.connect(self._refresh)

    # --------------------------------------------------------------------- Services
    def _setup_services(self):
        self.log_service = LogService()
        self.queue_service = QueueService()
        self.printer_service = PrinterService()

    def _connect_signals(self):
        # Log → UI
        self.log_service.new_log_line.connect(self.log_viewer.append_line)
        self.log_service.printer_update.connect(self.status_panel.update_printer)
        self.log_service.preset_loaded.connect(self.status_panel.update_preset)

        # Log → QueueService (job lifecycle events)
        self.log_service.job_added.connect(self.queue_service.handle_job_added)
        self.log_service.job_processing.connect(self.queue_service.handle_job_processing)
        self.log_service.job_completed.connect(self.queue_service.handle_job_completed)

        # QueueService → UI (table & counters)
        self.queue_service.jobs_updated.connect(self.job_table.refresh)
        self.queue_service.counters_updated.connect(self.status_panel.update_counters)

    def _start(self):
        # Start background timers / polling
        self.log_service.start()
        self.queue_service.start_periodic_refresh()

    # --------------------------------------------------------------------- Toolbar actions
    def _pause_queue(self):
        if self.printer_service.pause_queue():
            QtWidgets.QMessageBox.information(self, "Paused", "Queue processing has been paused.")
        else:
            QtWidgets.QMessageBox.warning(self, "Error", "Failed to pause the queue.")

    def _resume_queue(self):
        if self.printer_service.resume_queue():
            QtWidgets.QMessageBox.information(self, "Resumed", "Queue processing has been resumed.")
        else:
            QtWidgets.QMessageBox.warning(self, "Error", "Failed to resume the queue.")

    def _refresh(self):
        # Clear log view and restart tailing from current end of file
        self.log_viewer.clear()
        # Restart log service (re‑open file, reset cursor)
        self.log_service._timer.stop()
        self.log_service.start()
        # Force a filesystem refresh to pick up any external changes
        self.queue_service.refresh()
        QtWidgets.QMessageBox.information(self, "Refresh", "Dashboard refreshed.")

# --------------------------------------------------------------------- entry point
def main():
    app = QtWidgets.QApplication(sys.argv)
    win = Dashboard()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
