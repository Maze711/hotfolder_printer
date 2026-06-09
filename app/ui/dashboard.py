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

import logging
logger = logging.getLogger(__name__)

from ..logging_utils import setup_logging

# Ensure logging is configured for the dashboard (independent of engine.py)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
setup_logging(PROJECT_ROOT)


class Dashboard(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hotfolder Printer – Monitoring Dashboard")
        self.resize(1800, 1000)
        self._jobs = {}
        self.current_job_path = None
        self.current_template = None

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
        body_layout.addWidget(self.job_table, stretch=2)
        body_layout.addWidget(self.job_preview, stretch=5)
        body_layout.addWidget(self.template_panel, stretch=1)
        layout.addWidget(body_widget, stretch=4)

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

        # Log → QueueService (print lifecycle)
        self.log_service.job_print_started.connect(self.queue_service.handle_print_started)
        self.log_service.job_print_completed.connect(self.queue_service.handle_print_completed)

        # QueueService → UI (table & counters)
        self.queue_service.jobs_updated.connect(self._update_jobs)
        self.queue_service.counters_updated.connect(self.status_panel.update_counters)

        # Table selection changes
        self.job_table.itemSelectionChanged.connect(self._on_job_selected)

        # Template selection → preview, details, logging
        self.template_panel.template_selected.connect(self._on_template_changed)

    def _update_jobs(self, jobs: dict):
        """Store the latest job dict, refresh the table, and keep details in sync."""
        self._jobs = jobs
        self.job_table.refresh(jobs)
        # Keep details panel in sync when the currently-selected job updates
        if self.current_job_path and self.current_job_path in jobs:
            info = jobs[self.current_job_path]
            status = info.get("status", "—")
            added = info.get("ts", "—")
            self.job_details.set_job(self.current_job_path, status, self.current_template, added)

    @staticmethod
    def _file_path_at_row(table, row: int) -> str | None:
        """Return the text from column 0 of *row*, or ``None``."""
        item = table.item(row, 0)
        return item.text() if item else None

    def _on_job_selected(self):
        """Handle user selection of a job in the table.

        Updates the preview panel and details panel with information about the
        selected job.
        """
        file_path = self._file_path_at_row(self.job_table, self.job_table.currentRow())
        if not file_path:
            return
        self.current_job_path = file_path

        # Update preview – this will auto-detect and set the initial template
        self.job_preview.set_job(file_path)

        # If operator has manually selected a template, override the auto-detected one
        if self.current_template:
            self.job_preview.set_template(self.current_template)

        # Retrieve status and timestamp from stored jobs dict
        info = self._jobs.get(file_path, {})
        status = info.get("status", "—")
        added = info.get("ts", "—")

        # Use operator-selected template if available, else auto-detect
        template_path = self.current_template
        if not template_path:
            try:
                template_path = self.job_preview._find_template_for_image(file_path)
            except Exception:
                template_path = None

        # Update details panel
        self.job_details.set_job(file_path, status, template_path, added)

    def _on_template_changed(self, template_path: str):
        """Handle user selection of a template from the TemplatePanel."""
        self.current_template = template_path
        self.job_preview.set_template(template_path)
        self.job_details.set_template(template_path)
        logger.info("[TEMPLATE] Template selected: %s", template_path)

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

    def _is_input_path(self, path: str) -> bool:
        """Return ``True`` if *path* is inside an ``input`` folder."""
        return os.path.sep + "input" + os.path.sep in os.path.abspath(path)

    def _approve_selected(self):
        """Approve the currently selected job and trigger printing."""
        file_path = self._file_path_at_row(self.job_table, self.job_table.currentRow())
        if not file_path:
            QtWidgets.QMessageBox.information(self, "Approve", "No job selected.")
            return
        # Validate – only output files with status "Pending Review" can be approved
        info = self._jobs.get(file_path, {})
        status = info.get("status", "")
        if self._is_input_path(file_path):
            QtWidgets.QMessageBox.warning(
                self, "Approve",
                "Cannot approve an input file. The job must be processed first."
            )
            return
        if status != "Pending Review":
            QtWidgets.QMessageBox.warning(
                self, "Approve",
                f"Cannot approve a job with status \"{status}\". Only \"Pending Review\" jobs can be approved."
            )
            return
        logger.info("[APPROVAL] Job approved: %s", file_path)
        # Update status to Approved
        self.queue_service.approve_job(file_path)
        # Load config for printer settings
        config = self._load_config_for_output(file_path)
        # Print the file (print lifecycle signals update status to Printing → Completed)
        success = self.printer_service.print_file(file_path, config)
        if success:
            QtWidgets.QMessageBox.information(self, "Approve", "Job sent to printer.")
        else:
            QtWidgets.QMessageBox.warning(self, "Approve", "Failed to print job.")

    def _reject_selected(self):
        """Reject the currently selected job – removes it from processing."""
        file_path = self._file_path_at_row(self.job_table, self.job_table.currentRow())
        if not file_path:
            QtWidgets.QMessageBox.information(self, "Reject", "No job selected.")
            return
        logger.info("[APPROVAL] Job rejected: %s", file_path)
        self.queue_service.reject_job(file_path)
        # Clear preview if the rejected job was the one being previewed
        if self.current_job_path == file_path:
            self.job_preview.clear()
            self.current_job_path = None
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
