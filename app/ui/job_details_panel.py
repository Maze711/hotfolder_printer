"""Placeholder panel showing details of the selected job.

In Phase 1 it displays static placeholder values. Later it will be populated
from the queue selection.
"""

from PyQt5 import QtWidgets


class JobDetailsPanel(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        self.labels = {}
        for field in ["Filename", "Status", "Template", "Copies", "Added", "Size"]:
            lbl = QtWidgets.QLabel(f"{field}: --")
            layout.addWidget(lbl)
            self.labels[field] = lbl
