"""Job details panel showing selected job info.

Displays filename, status, assigned template, and added timestamp.
"""

import os
from PyQt5 import QtWidgets


class JobDetailsPanel(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        self.labels = {}
        for field in ["Filename", "Status", "Template", "Added"]:
            lbl = QtWidgets.QLabel(f"{field}: --")
            layout.addWidget(lbl)
            self.labels[field] = lbl

    def set_job(self, file_path: str, status: str, template_path: str | None, added: str):
        """Populate the details panel for the selected job.

        * ``file_path`` – absolute path of the job file.
        * ``status`` – current status string from the queue service.
        * ``template_path`` – absolute path to the associated template, if any.
        * ``added`` – timestamp string when the job was added to the UI.
        """
        self.labels["Filename"].setText(f"Filename: {os.path.basename(file_path)}")
        self.labels["Status"].setText(f"Status: {status}")
        tmpl = os.path.basename(template_path) if template_path else "—"
        self.labels["Template"].setText(f"Template: {tmpl}")
        self.labels["Added"].setText(f"Added: {added}")

    def set_template(self, template_path: str | None):
        """Update only the Template field without changing other fields."""
        tmpl = os.path.basename(template_path) if template_path else "—"
        self.labels["Template"].setText(f"Template: {tmpl}")
