"""Widget for the Job Preview panel.

Shows the selected input image overlaid with its template.
The preview auto‑scales to fit the widget while preserving aspect ratio.
"""

from PyQt5 import QtWidgets, QtCore, QtGui
import os
import json
from PIL import Image, ImageOps, ImageQt
import logging

logger = logging.getLogger(__name__)


class JobPreviewPanel(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.current_path = None

    def _setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Filename label
        self.filename_label = QtWidgets.QLabel("--")
        self.filename_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.filename_label)

        # Image display area
        self.image_label = QtWidgets.QLabel()
        self.image_label.setAlignment(QtCore.Qt.AlignCenter)
        self.image_label.setMinimumSize(200, 200)
        self.image_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        layout.addWidget(self.image_label, stretch=1)

    def clear(self):
        """Reset preview to empty state."""
        self.filename_label.setText("--")
        self.image_label.clear()
        self.current_path = None

    def set_job(self, image_path: str):
        """Load preview for *image_path*.

        If ``image_path`` points to an ``output`` file, it is displayed directly.
        For an ``input`` image the associated template (if any) is overlaid.
        """
        if not os.path.isfile(image_path):
            logger.warning("[PREVIEW] Image file not found: %s", image_path)
            self.clear()
            return

        self.current_path = image_path
        self.filename_label.setText(os.path.basename(image_path))

        try:
            img = Image.open(image_path).convert("RGBA")
        except Exception as exc:
            logger.exception("[PREVIEW] Failed to open image %s", image_path)
            self.clear()
            return

        # If this is an output image, skip applying template again
        if os.path.sep + "output" + os.path.sep in os.path.abspath(image_path):
            preview = img
        else:
            template_path = self._find_template_for_image(image_path)
            if template_path and os.path.isfile(template_path):
                try:
                    template = Image.open(template_path).convert("RGBA")
                    logger.info("[PREVIEW] Template applied: %s", template_path)
                    scaled = ImageOps.contain(img, template.size, method=Image.Resampling.LANCZOS)
                    canvas = Image.new("RGBA", template.size, (0, 0, 0, 0))
                    x = (template.width - scaled.width) // 2
                    y = (template.height - scaled.height) // 2
                    canvas.paste(scaled, (x, y))
                    preview = Image.alpha_composite(canvas, template)
                except Exception as exc:
                    logger.exception("[PREVIEW] Error applying template %s", template_path)
                    preview = img
            else:
                logger.info("[PREVIEW] No template found for %s", image_path)
                preview = img

        # Convert to QPixmap and display
        try:
            qimage = ImageQt.ImageQt(preview)
            pixmap = QtGui.QPixmap.fromImage(qimage)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(self.image_label.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                self.image_label.setPixmap(scaled_pixmap)
        except Exception as exc:
            logger.exception("[PREVIEW] Failed to convert preview to QPixmap: %s", exc)
            self.image_label.clear()

        logger.info("[PREVIEW] Loaded preview for %s", image_path)

    def _find_template_for_image(self, image_path: str) -> str | None:
        """Return the absolute template path for *image_path*.

        Expected layout:
        <project>/hotfolders/<preset>/input/<file>
        Config is located at <preset>/config.json and contains a ``template`` entry.
        """
        # Walk up to the preset folder (parent of ``input``)
        input_dir = os.path.dirname(image_path)  # .../input
        preset_dir = os.path.abspath(os.path.join(input_dir, os.pardir))
        config_path = os.path.join(preset_dir, "config.json")
        if not os.path.isfile(config_path):
            return None
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            tmpl_rel = cfg.get("template")
            if not tmpl_rel:
                return None
            # Resolve relative to preset_dir (engine does the same)
            tmpl_path = os.path.abspath(os.path.join(preset_dir, tmpl_rel))
            return tmpl_path
        except Exception:
            return None

