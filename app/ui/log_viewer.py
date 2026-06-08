"""Log viewer widget – shows live tail of hotfolder_printer.log.

The widget is a read‑only QTextEdit that receives raw log lines via the
``new_log_line`` signal from ``LogService``. For readability it colour‑codes
lines containing ``[ERROR]`` (red), ``[WARN]`` (orange) and ``[PRINT]``
(blue). The view automatically scrolls to the bottom when new text is
added.
"""

from PyQt5 import QtWidgets, QtGui, QtCore

class LogViewer(QtWidgets.QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
                # Limit maximum block count if the widget supports it (e.g., QPlainTextEdit)
        if hasattr(self, "setMaximumBlockCount"):
            self.setMaximumBlockCount(1000)   # keep memory bounded
        # monospace font for log readability
        font = QtGui.QFont("Courier", 9)
        self.setFont(font)

    @QtCore.pyqtSlot(str)
    def append_line(self, line: str):
        """Append a line to the view, applying colour based on severity."""
        colour = None
        if "[ERROR]" in line:
            colour = "red"
        elif "[WARN]" in line:
            colour = "orange"
        elif "[PRINT]" in line:
            colour = "blue"
        if colour:
            html = f"<span style='color:{colour}'>{line}</span>"
        else:
            html = line
        self.append(html)
        self.moveCursor(QtGui.QTextCursor.End)
