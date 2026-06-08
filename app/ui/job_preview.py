"""Placeholder widget for the Job Preview panel.

Currently displays a static label. In future phases this will show a
preview of the selected job image with template overlay.
"""

from PyQt5 import QtWidgets, QtCore


class JobPreviewPanel(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        label = QtWidgets.QLabel("Job Preview (placeholder)")
        label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(label)
