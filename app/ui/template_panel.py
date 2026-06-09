"""Widget for the Template panel.

Displays available templates from all hotfolder presets and allows
operator selection.  Emits ``template_selected(str)`` with the
absolute template path whenever the user picks a template.
"""

import os
import json
from PyQt5 import QtWidgets, QtCore

# Determine PROJECT_ROOT (three levels up: app/ui/ -> app/ -> root)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))


class TemplatePanel(QtWidgets.QWidget):
    template_selected = QtCore.pyqtSignal(str)  # absolute template path

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)

        title = QtWidgets.QLabel("Templates")
        title.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(title)

        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        layout.addWidget(self.list_widget, stretch=1)

        self._scan_templates()

        self.list_widget.currentItemChanged.connect(self._on_item_changed)

    def _scan_templates(self):
        """Walk ``hotfolders/*/config.json`` and populate the list widget."""
        self._row_to_path = {}  # row index → absolute template path
        base = os.path.join(PROJECT_ROOT, "hotfolders")
        if not os.path.isdir(base):
            return
        for preset_name in sorted(os.listdir(base)):
            preset_dir = os.path.join(base, preset_name)
            if not os.path.isdir(preset_dir):
                continue
            config_path = os.path.join(preset_dir, "config.json")
            if not os.path.isfile(config_path):
                continue
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                tmpl_rel = cfg.get("template")
                if not tmpl_rel:
                    continue
                tmpl_path = os.path.abspath(os.path.join(preset_dir, tmpl_rel))
                if not os.path.isfile(tmpl_path):
                    continue
            except Exception:
                continue
            row = self.list_widget.count()
            self.list_widget.addItem(preset_name)
            self._row_to_path[row] = tmpl_path

    def _on_item_changed(self, current, previous):
        if current is None:
            return
        row = self.list_widget.row(current)
        path = self._row_to_path.get(row)
        if path:
            self.template_selected.emit(path)
