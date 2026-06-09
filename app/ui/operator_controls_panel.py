"""Operator control buttons.

Buttons are wired to the Dashboard's existing actions where possible.
New Approve/Reject buttons are added for the preview workflow.
"""

from PyQt5 import QtWidgets, QtCore


class OperatorControlsPanel(QtWidgets.QWidget):
    def __init__(self, dashboard, parent=None):
        super().__init__(parent)
        self.dashboard = dashboard
        layout = QtWidgets.QVBoxLayout(self)

        # First row – upload/print actions
        row1 = QtWidgets.QHBoxLayout()
        for txt in ["Add Images", "Add Folder", "Print Selected", "Print Queue", "Reprint"]:
            btn = QtWidgets.QPushButton(txt)
            btn.clicked.connect(lambda _, t=txt: QtWidgets.QMessageBox.information(self, "Info", f"{t} clicked (placeholder)"))
            row1.addWidget(btn)
        layout.addLayout(row1)

        # Second row – queue and watcher controls
        row2 = QtWidgets.QHBoxLayout()
        for txt in ["Pause Queue", "Resume Queue", "Start Watcher", "Stop Watcher", "Refresh"]:
            btn = QtWidgets.QPushButton(txt)
            if txt == "Pause Queue":
                btn.clicked.connect(self.dashboard._pause_queue)
            elif txt == "Resume Queue":
                btn.clicked.connect(self.dashboard._resume_queue)
            elif txt == "Refresh":
                btn.clicked.connect(self.dashboard._refresh)
            else:
                # Placeholder for watcher start/stop
                btn.clicked.connect(lambda _, t=txt: QtWidgets.QMessageBox.information(self, "Info", f"{t} clicked (placeholder)"))
            row2.addWidget(btn)
        layout.addLayout(row2)

        # Third row – approval workflow
        row3 = QtWidgets.QHBoxLayout()
        approve_btn = QtWidgets.QPushButton("Approve")
        approve_btn.clicked.connect(self.dashboard._approve_selected)
        reject_btn = QtWidgets.QPushButton("Reject")
        reject_btn.clicked.connect(self.dashboard._reject_selected)
        row3.addWidget(approve_btn)
        row3.addWidget(reject_btn)
        layout.addLayout(row3)
