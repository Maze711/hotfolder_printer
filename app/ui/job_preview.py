"""Widget for the Job Preview panel.

Shows the selected input image overlaid with its template.
The preview auto‑scales to fit the widget while preserving aspect ratio.
"""

from PyQt5 import QtWidgets, QtCore, QtGui
import os
import json
import io
from PIL import Image, ImageOps
import logging

logger = logging.getLogger(__name__)


class JobPreviewPanel(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.current_path = None
        self._base_image = None       # cached PIL Image (RGBA) of the current job
        self._template_path = None    # currently selected template path

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
        self._base_image = None
        self._template_path = None

    def set_job(self, image_path: str):
        """Load preview for *image_path*.

        If ``image_path`` points to an ``output`` file, it is displayed directly.
        For an ``input`` image the associated template (if any) is overlaid.

        The base image is cached in ``_base_image`` so that ``set_template()`` can
        re‑render without reloading from disk.
        """
        if not os.path.isfile(image_path):
            logger.warning("[PREVIEW] Image file not found: %s", image_path)
            self.clear()
            return

        self.current_path = image_path
        self.filename_label.setText(os.path.basename(image_path))

        logger.info("[PREVIEW] Opening image: %s", image_path)
        try:
            self._base_image = Image.open(image_path).convert("RGBA")
            logger.info("[PREVIEW] Image opened OK – size: %s, mode: %s",
                        self._base_image.size, self._base_image.mode)
        except Exception as exc:
            logger.exception("[PREVIEW] Failed to open image %s", image_path)
            self.clear()
            return

        # Determine initial template: use the auto-detected one for this image
        auto_template = self._find_template_for_image(image_path) if self._is_input_image(image_path) else None
        if auto_template and os.path.isfile(auto_template):
            self._template_path = auto_template
            logger.info("[PREVIEW] Auto-detected template: %s", auto_template)
        else:
            self._template_path = None
            logger.info("[PREVIEW] No template auto-detected for %s", image_path)

        self._re_render()

        logger.info("[PREVIEW] Loaded preview for %s", image_path)

    def set_template(self, template_path: str | None):
        """Change the template overlay and re‑render without reloading the base image."""
        if template_path and not os.path.isfile(template_path):
            logger.warning("[PREVIEW] Template file not found: %s", template_path)
            return
        self._template_path = template_path
        self._re_render()

    def _is_input_image(self, image_path: str) -> bool:
        """Return ``True`` if *image_path* is inside an ``input`` folder."""
        return os.path.sep + "input" + os.path.sep in os.path.abspath(image_path)

    @staticmethod
    def _parse_pct(value: str, dimension: int) -> int:
        """Convert a percentage string like ``"8.02%"`` to an absolute pixel value."""
        return int(float(value.strip().rstrip("%")) * dimension / 100)

    def _get_placement(self, template_size, config: dict | None) -> tuple[int, int, int, int]:
        """Return ``(x, y, width, height)`` in pixels for the first placement.

        Reads from ``config["placement"]`` (single) or ``config["placements"][0]``
        (multiple) and converts percentage values to absolute pixel coordinates
        based on *template_size* ``(width, height)``.
        Falls back to centering the image on the template.
        """
        tw, th = template_size
        placement = None
        if config:
            placement = config.get("placement") or (
                config.get("placements", [None])[0] if config.get("placements") else None
            )
        if placement:
            x = self._parse_pct(placement.get("x", "0%"), tw)
            y = self._parse_pct(placement.get("y", "0%"), th)
            w = self._parse_pct(placement.get("width", "100%"), tw)
            h = self._parse_pct(placement.get("height", "100%"), th)
            logger.info("[PREVIEW] Placement from config: x=%d y=%d w=%d h=%d", x, y, w, h)
            return x, y, w, h
        # Fallback: center
        cx = (tw - min(tw, self._base_image.width)) // 2 if self._base_image else 0
        cy = (th - min(th, self._base_image.height)) // 2 if self._base_image else 0
        return cx, cy, tw, th

    def _load_config_for_image(self, image_path: str) -> dict | None:
        """Load the preset ``config.json`` for an input or output file."""
        parts = os.path.abspath(image_path).split(os.sep)
        try:
            idx = parts.index("hotfolders")
            preset_dir = os.sep.join(parts[:idx + 2])  # .../hotfolders/<preset>
        except ValueError:
            return None
        config_path = os.path.join(preset_dir, "config.json")
        if not os.path.isfile(config_path):
            return None
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def _re_render(self):
        """Re‑render the preview using ``_base_image`` and ``_template_path``."""
        if self._base_image is None:
            # No job loaded – show the template image itself as a preview
            if self._template_path and os.path.isfile(self._template_path):
                try:
                    template_img = Image.open(self._template_path).convert("RGBA")
                    pixmap = self._pil_to_pixmap(template_img)
                    if pixmap and not pixmap.isNull():
                        scaled = pixmap.scaled(self.image_label.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                        self.image_label.setPixmap(scaled)
                        logger.info("[PREVIEW] Template preview shown (no job loaded)")
                except Exception as exc:
                    logger.exception("[PREVIEW] Failed to show template preview: %s", exc)
                    self.image_label.clear()
            return

        # If output image, show base image directly (no overlay)
        if self.current_path and self._is_input_image(self.current_path) is False:
            preview = self._base_image
            logger.info("[PREVIEW] Output image – no template overlay")
        else:
            if self._template_path and os.path.isfile(self._template_path):
                try:
                    template = Image.open(self._template_path).convert("RGBA")
                    logger.info("[PREVIEW] Template applied: %s (size=%s)", self._template_path, template.size)

                    # Load placement from preset config to position the photo correctly
                    config = self._load_config_for_image(self.current_path if self.current_path else "")
                    px, py, pw, ph = self._get_placement(template.size, config)

                    # Resize photo to fill the placement area (mode="fill" behaviour)
                    fill = ImageOps.fit(self._base_image, (pw, ph), method=Image.Resampling.LANCZOS)

                    canvas = Image.new("RGBA", template.size, (0, 0, 0, 0))
                    canvas.paste(fill, (px, py))
                    preview = Image.alpha_composite(canvas, template)
                except Exception as exc:
                    logger.exception("[PREVIEW] Error applying template %s, falling back to bare image", self._template_path)
                    preview = self._base_image
            else:
                logger.info("[PREVIEW] No template – showing bare image")
                preview = self._base_image

        # Convert to QPixmap and display
        try:
            pixmap = self._pil_to_pixmap(preview)
            if pixmap is None:
                logger.error("[PREVIEW] _pil_to_pixmap returned None for preview size=%s", preview.size)
                self.image_label.clear()
                return
            if pixmap.isNull():
                logger.error("[PREVIEW] pixmap is null for preview size=%s", preview.size)
                self.image_label.clear()
                return
            scaled_pixmap = pixmap.scaled(self.image_label.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            self.image_label.setPixmap(scaled_pixmap)
        except Exception as exc:
            logger.exception("[PREVIEW] Failed to convert preview to QPixmap: %s", exc)
            self.image_label.clear()

        logger.info("[PREVIEW] Preview refreshed with template %s", self._template_path)

    @staticmethod
    def _pil_to_pixmap(img: Image.Image) -> QtGui.QPixmap | None:
        """Convert a PIL Image to QPixmap via PNG buffer (avoids Pillow Qt bugs)."""
        try:
            buf = io.BytesIO()
            img.convert("RGBA").save(buf, "PNG")
            buf.seek(0)
            pixmap = QtGui.QPixmap()
            if not pixmap.loadFromData(buf.getvalue()):
                logger.error("[PREVIEW] QPixmap.loadFromData failed")
                return None
            return pixmap
        except Exception as exc:
            logger.exception("[PREVIEW] _pil_to_pixmap failed: %s", exc)
            return None

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

