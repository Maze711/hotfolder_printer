"""Toolbar widget for interactive placement editing.

Provides per-slot controls for:
- Slot selection (when multiple placements exist)
- Auto Fit / Reset
- Rotate Left / Right
- Save adjustments to config
- Photo scale slider (size within placement region)
- View zoom slider (canvas magnification)
"""

from PyQt5 import QtWidgets, QtCore


class PlacementEditorWidget(QtWidgets.QWidget):
    save_requested = QtCore.pyqtSignal()
    slot_changed = QtCore.pyqtSignal(int)
    zoom_changed = QtCore.pyqtSignal(int)
    scale_changed = QtCore.pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._slot_count = 0
        self._setup_ui()
        self._connect()

    def _setup_ui(self):
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(4)

        # Slot selector
        self.slot_combo = QtWidgets.QComboBox()
        self.slot_combo.setMinimumWidth(100)
        self.slot_combo.setToolTip("Select placement slot to edit")
        layout.addWidget(self.slot_combo)

        sep1 = QtWidgets.QFrame()
        sep1.setFrameShape(QtWidgets.QFrame.VLine)
        sep1.setFrameShadow(QtWidgets.QFrame.Sunken)
        layout.addWidget(sep1)

        # Edit buttons
        self.auto_fit_btn = QtWidgets.QPushButton("Auto Fit")
        self.auto_fit_btn.setToolTip("Reset position, scale, rotation to defaults")

        self.rotate_l_btn = QtWidgets.QPushButton("Rotate L")
        self.rotate_l_btn.setToolTip("Rotate photo 90\u00b0 counter-clockwise")

        self.rotate_r_btn = QtWidgets.QPushButton("Rotate R")
        self.rotate_r_btn.setToolTip("Rotate photo 90\u00b0 clockwise")

        self.reset_btn = QtWidgets.QPushButton("Reset")

        self.save_btn = QtWidgets.QPushButton("Save Placement")
        self.save_btn.setToolTip("Save adjustment values to config.json")

        for btn in [self.auto_fit_btn, self.rotate_l_btn, self.rotate_r_btn,
                    self.reset_btn, self.save_btn]:
            layout.addWidget(btn)

        sep2 = QtWidgets.QFrame()
        sep2.setFrameShape(QtWidgets.QFrame.VLine)
        sep2.setFrameShadow(QtWidgets.QFrame.Sunken)
        layout.addWidget(sep2)

        # Photo scale slider (zooms the photo within the placement region)
        layout.addWidget(QtWidgets.QLabel("Scale:"))
        self.scale_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.scale_slider.setRange(10, 500)   # maps to 0.10 – 5.00
        self.scale_slider.setValue(100)
        self.scale_slider.setFixedWidth(120)
        self.scale_slider.setTickPosition(QtWidgets.QSlider.NoTicks)
        self.scale_slider.setToolTip("Scale photo within placement region (0.1x – 5.0x)")
        layout.addWidget(self.scale_slider)
        self.scale_label = QtWidgets.QLabel("1.00x")
        self.scale_label.setFixedWidth(40)
        layout.addWidget(self.scale_label)

        sep3 = QtWidgets.QFrame()
        sep3.setFrameShape(QtWidgets.QFrame.VLine)
        sep3.setFrameShadow(QtWidgets.QFrame.Sunken)
        layout.addWidget(sep3)

        # View zoom slider (canvas magnification)
        layout.addWidget(QtWidgets.QLabel("Zoom:"))
        self.zoom_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.zoom_slider.setRange(10, 400)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setFixedWidth(120)
        self.zoom_slider.setToolTip("Zoom preview canvas 10% – 400%")
        layout.addWidget(self.zoom_slider)
        self.zoom_label = QtWidgets.QLabel("100%")
        self.zoom_label.setFixedWidth(40)
        layout.addWidget(self.zoom_label)

        layout.addStretch()

        self._set_buttons_enabled(False)

    def _connect(self):
        self.slot_combo.currentIndexChanged.connect(self._on_slot_changed)
        self.scale_slider.valueChanged.connect(self._on_scale_slider)
        self.zoom_slider.valueChanged.connect(self._on_zoom_slider)

    def _set_buttons_enabled(self, enabled: bool):
        for btn in [self.auto_fit_btn, self.rotate_l_btn, self.rotate_r_btn,
                    self.reset_btn, self.save_btn]:
            btn.setEnabled(enabled)
        self.slot_combo.setEnabled(enabled)
        self.scale_slider.setEnabled(enabled)
        self.zoom_slider.setEnabled(enabled)

    # ------------------------------------------------------------------ slot management

    def set_slot_count(self, count: int):
        self._slot_count = count
        self.slot_combo.blockSignals(True)
        self.slot_combo.clear()
        if count <= 1:
            self.slot_combo.addItem("Slot 1")
            self.slot_combo.setVisible(False)
        else:
            self.slot_combo.setVisible(True)
            for i in range(count):
                self.slot_combo.addItem(f"Slot {i + 1} of {count}")
        self.slot_combo.blockSignals(False)
        self._set_buttons_enabled(count > 0)

    @property
    def current_slot(self) -> int:
        return self.slot_combo.currentIndex()

    def _on_slot_changed(self, index: int):
        self.slot_changed.emit(index)

    # ------------------------------------------------------------------ photo scale

    def set_scale_value(self, value: float):
        self.scale_slider.blockSignals(True)
        self.scale_slider.setValue(round(value * 100))
        self.scale_slider.blockSignals(False)
        self.scale_label.setText(f"{value:.2f}x")

    def _on_scale_slider(self, slider_value: int):
        scale = slider_value / 100.0
        self.scale_label.setText(f"{scale:.2f}x")
        self.scale_changed.emit(scale)

    # ------------------------------------------------------------------ view zoom

    def set_zoom_value(self, percent: int):
        self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(percent)
        self.zoom_slider.blockSignals(False)
        self.zoom_label.setText(f"{percent}%")

    def _on_zoom_slider(self, value: int):
        self.zoom_label.setText(f"{value}%")
        self.zoom_changed.emit(value)
