"""Placeholder widget for the Template panel.

Shows a static label for now; later will list available templates and
allow selection.
"""

from PyQt5 import QtWidgets, QtCore


class TemplatePanel(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        label = QtWidgets.QLabel("Template Panel (placeholder)")
        label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(label)
