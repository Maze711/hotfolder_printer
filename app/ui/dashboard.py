"""Main dashboard window for the hotfolder printer.

It brings together the three UI widgets (status panel, job table, log view)
and the three services (log, queue, printer). The UI is read‑only – it does
not modify the backend logic other than toggling the soft‑pause flag via
``system_state.json``.
"""

import sys, os, json
from PyQt5 import QtWidgets, QtCore

# Local imports – the UI package lives under ``app.ui`` and the services
# under ``app.services``.
from .status_panel import StatusPanel
from .queue_table import QueueTable
from .log_viewer import LogViewer
from .job_preview import JobPreviewPanel
from .template_panel import TemplatePanel
from .job_details_panel import JobDetailsPanel
from .operator_controls_panel import OperatorControlsPanel

from ..services.log_service import LogService
from ..services.queue_service import QueueService
from ..services.printer_service import PrinterService

class Dashboard(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hotfolder Printer – Monitoring Dashboard")
        self.resize(1400, 900)
        self._jobs = {}

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

        # Main body panels (Queue, Job Preview, Template)
        self.job_table = QueueTable()
        self.job_preview = JobPreviewPanel()
        self.template_panel = TemplatePanel()
        body_widget = QtWidgets.QWidget()
        body_layout = QtWidgets.QHBoxLayout(body_widget)
        body_layout.setSpacing(5)
        body_layout.addWidget(self.job_table, stretch=3)
        body_layout.addWidget(self.job_preview, stretch=2)
        body_layout.addWidget(self.template_panel, stretch=2)
        layout.addWidget(body_widget, stretch=3)

        # Selected job details panel
        self.job_details = JobDetailsPanel()
        layout.addWidget(self.job_details)

        # Operator controls panel
        self.operator_controls = OperatorControlsPanel(self)
        layout.addWidget(self.operator_controls)

        # Log viewer (bottom)
        self.log_viewer = LogViewer()
        layout.addWidget(self.log_viewer, stretch=2)

        # Toolbar with actions
        toolbar = QtWidgets.QToolBar()
        self.addToolBar(toolbar)
        self.pause_action = QtWidgets.QAction("Pause Queue", self)
        self.refresh_action = QtWidgets.QAction("Refresh", self)
        self.resume_action = QtWidgets.QAction("Resume Queue", self)
        self.clear_queue_action = QtWidgets.QAction("Clear Queue", self)
        toolbar.addAction(self.pause_action)
        toolbar.addAction(self.resume_action)
        toolbar.addSeparator()
        toolbar.addAction(self.refresh_action)
        toolbar.addAction(self.clear_queue_action)

        # Connect button clicks
        self.pause_action.triggered.connect(self._pause_queue)
        self.resume_action.triggered.connect(self._resume_queue)
        self.refresh_action.triggered.connect(self._refresh)
        self.clear_queue_action.triggered.connect(self._clear_queue)

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
        # Use job_ready for review workflow instead of job_completed
        self.log_service.job_ready.connect(self.queue_service.handle_job_ready)

        # QueueService → UI (table & counters)
        self.queue_service.jobs_updated.connect(self._update_jobs)
        self.queue_service.counters_updated.connect(self.status_panel.update_counters)

        # Table selection changes
        self.job_table.itemSelectionChanged.connect(self._on_job_selected)

    def _update_jobs(self, jobs: dict):
        """Store the latest job dict and refresh the table view."""
        self._jobs = jobs
        self.job_table.refresh(jobs)

    def _on_job_selected(self):
        """Handle user selection of a job in the table.

        Updates the preview panel and details panel with information about the
        selected job.
        """
        selected_items = self.job_table.selectedItems()
        if not selected_items:
            return
        # Assuming selection is per row, first column contains the file path
        file_path_item = selected_items[0]
        file_path = file_path_item.text()
        # Update preview
        self.job_preview.set_job(file_path)
        # Retrieve status and timestamp from stored jobs dict
        info = self._jobs.get(file_path, {})
        status = info.get("status", "—")
        added = info.get("ts", "—")
        # Determine template path (if any)
        template_path = None
        try:
            template_path = self.job_preview._find_template_for_image(file_path)
        except Exception:
            template_path = None
        # Update details panel
        self.job_details.set_job(file_path, status, template_path, added)

    def _load_config_for_output(self, output_path: str) -> dict | None:
        """Load the preset ``config.json`` for a given output file.

        The output file resides in ``<preset>/output/``; the config file is in the
        preset root directory.
        """
        preset_dir = os.path.abspath(os.path.join(output_path, os.pardir, os.pardir))
        config_path = os.path.join(preset_dir, "config.json")
        if not os.path.isfile(config_path):
            return None
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def _approve_selected(self):
        """Approve the currently selected job and trigger printing."""
        selected_items = self.job_table.selectedItems()
        if not selected_items:
            QtWidgets.QMessageBox.information(self, "Approve", "No job selected.")
            return
        file_path = selected_items[0].text()
        # Update status to Approved
        self.queue_service.approve_job(file_path)
        # Load config for printer settings
        config = self._load_config_for_output(file_path)
        # Print the file
        success = self.printer_service.print_file(file_path, config)
        if success:
            QtWidgets.QMessageBox.information(self, "Approve", "Job printed successfully.")
        else:
            QtWidgets.QMessageBox.warning(self, "Approve", "Failed to print job.")

    def _reject_selected(self):
        """Reject the currently selected job – removes it from processing."""
        selected_items = self.job_table.selectedItems()
        if not selected_items:
            QtWidgets.QMessageBox.information(self, "Reject", "No job selected.")
            return
        file_path = selected_items[0].text()
        self.queue_service.reject_job(file_path)
        QtWidgets.QMessageBox.information(self, "Reject", "Job rejected and removed from queue.")

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
        """Clear log view and restart services."""
        self.log_viewer.clear()
        self.log_service._timer.stop()
        self.log_service.start()
        self.queue_service.refresh()
        QtWidgets.QMessageBox.information(self, "Refresh", "Dashboard refreshed.")

    def _clear_queue(self):
        """Remove all jobs from the UI queue view."""
        self.queue_service.clear()
        QtWidgets.QMessageBox.information(self, "Clear Queue", "Job queue cleared.")

# --------------------------------------------------------------------- entry point
def main():
    app = QtWidgets.QApplication(sys.argv)
    win = Dashboard()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
