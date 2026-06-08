"""Status panel widget for the hotfolder‑printer dashboard.

Displays:
* Printer name / last status
* Active preset (folder name)
* Queue counters (Pending / Processing / Completed)
"""

from PyQt5 import QtWidgets, QtCore
import os

class StatusPanel(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    # --------------------------------------------------------------------- UI setup
    def _setup_ui(self):
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(20)

        self.printer_label = QtWidgets.QLabel("Printer: –")
        self.hotfolder_label = QtWidgets.QLabel("Hotfolder: –")
        self.queue_label = QtWidgets.QLabel("Queue: 0 jobs")
        self.mode_label = QtWidgets.QLabel("Mode: –")
        self.preset_label  = QtWidgets.QLabel("Active preset: –")
        self.template_label = QtWidgets.QLabel("Active Template: –")
        self.last_print_label = QtWidgets.QLabel("Last Print: –")
        self.counters_label = QtWidgets.QLabel("Pending: 0 | Processing: 0 | Done: 0 | Failed: 0")

        # Make the counters bold for visibility
        font = self.counters_label.font()
        font.setBold(True)
        self.counters_label.setFont(font)

        layout.addWidget(self.printer_label)
        layout.addWidget(self.hotfolder_label)
        layout.addWidget(self.queue_label)
        layout.addWidget(self.mode_label)
        layout.addWidget(self.preset_label)
        layout.addWidget(self.template_label)
        layout.addWidget(self.last_print_label)
        layout.addStretch()
        layout.addWidget(self.counters_label)

    # --------------------------------------------------------------------- public slots
    @QtCore.pyqtSlot(str, str)
    def update_printer(self, printer_name: str, last_status: str):
        """Update printer information.
        ``printer_name`` may be ``None`` – we display a dash.
        ``last_status`` is a short string such as "dialog" or "error".
        """
        printer = printer_name or "–"
        self.printer_label.setText(f"Printer: {printer} ({last_status})")

    @QtCore.pyqtSlot(str)
    def update_preset(self, preset_path: str):
        """Show the active preset name (folder name)."""
        name = os.path.basename(preset_path) if preset_path else "–"
        self.preset_label.setText(f"Active preset: {name}")

    @QtCore.pyqtSlot(int, int, int)
    def update_counters(self, pending: int, processing: int, completed: int):
        """Refresh the numeric counters shown on the right side.
        The UI expects a "Done" column and a placeholder for failed jobs.
        """
        self.counters_label.setText(
            f"Pending: {pending} | Processing: {processing} | Done: {completed} | Failed: 0"
        )
