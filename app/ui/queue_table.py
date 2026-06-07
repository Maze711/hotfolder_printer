"""Table widget that displays the current job list for the dashboard.

The table has three columns:
* **File** – absolute path of the image or output file
* **Status** – Pending / Processing / Completed
* **Timestamp** – when the status was last updated (HH:MM:SS)

The widget receives a dictionary from ``QueueService`` via the
``jobs_updated`` signal. The dictionary is ordered (oldest → newest) and
contains at most ``MAX_JOBS`` entries, so the UI remains responsive.
"""

from PyQt5 import QtWidgets, QtCore

class QueueTable(QtWidgets.QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["File", "Status", "Time"])
        self.horizontalHeader().setStretchLastSection(True)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.setAlternatingRowColors(True)
        # Resize first two columns to reasonable widths
        self.setColumnWidth(0, 500)
        self.setColumnWidth(1, 100)
        self.setColumnWidth(2, 80)

    @QtCore.pyqtSlot(dict)
    def refresh(self, jobs: dict):
        """Replace the whole table content with the supplied ``jobs`` dict.
        ``jobs`` is an OrderedDict mapping ``filepath`` → ``{"status": str,
        "ts": str}``. Only the most recent ``MAX_JOBS`` entries are kept by the
        upstream service, so we can simply clear and repopulate.
        """
        self.setRowCount(0)
        for row_idx, (path, info) in enumerate(jobs.items()):
            self.insertRow(row_idx)
            file_item = QtWidgets.QTableWidgetItem(path)
            status_item = QtWidgets.QTableWidgetItem(info.get("status", ""))
            time_item = QtWidgets.QTableWidgetItem(info.get("ts", ""))
            # Colour coding for status
            status = info.get("status", "").lower()
            if status == "pending":
                status_item.setForeground(QtCore.Qt.gray)
            elif status == "processing":
                status_item.setForeground(QtCore.Qt.darkYellow)
            elif status == "completed":
                status_item.setForeground(QtCore.Qt.darkGreen)
            self.setItem(row_idx, 0, file_item)
            self.setItem(row_idx, 1, status_item)
            self.setItem(row_idx, 2, time_item)
        self.resizeRowsToContents()