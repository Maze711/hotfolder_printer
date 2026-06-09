"""Widget for the Job Preview panel with interactive placement editing.

Shows the selected input image overlaid with its template.
Supports per-slot drag, scale, rotation via QGraphicsView canvas.
"""

from PyQt5 import QtWidgets, QtCore, QtGui
import os
import json
import io
from PIL import Image
import logging

from .placement_canvas import PlacementCanvas
from .placement_editor import PlacementEditorWidget
from ..placement.renderer import render_preview
from ..placement.validator import _resolve_and_validate_placements


logger = logging.getLogger(__name__)


_DEFAULT_ADJUSTMENTS = {"x_offset": 0, "y_offset": 0, "scale": 1.0, "rotation": 0}


class JobPreviewPanel(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.current_path = None
        self._base_image = None
        self._image_list = None
        self._template_path = None
        self._template_rgba = None
        self._placements = []
        self._slot_adjustments = []
        self._current_slot = 0
        self._config = None

        self._render_timer = QtCore.QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.setInterval(50)
        self._render_timer.timeout.connect(self._re_render)

    def _setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        self.filename_label = QtWidgets.QLabel("--")
        self.filename_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.filename_label)

        self.canvas = PlacementCanvas()
        layout.addWidget(self.canvas, stretch=1)

        self.editor = PlacementEditorWidget()
        layout.addWidget(self.editor)

        # Canvas signals
        self.canvas.photo_dragged.connect(self._on_photo_dragged)
        self.canvas.drag_started.connect(self._on_drag_started)
        self.canvas.drag_finished.connect(self._on_drag_finished)
        self.canvas.zoom_changed.connect(self.editor.set_zoom_value)

        # Editor signals
        self.editor.save_requested.connect(self._on_save)
        self.editor.slot_changed.connect(self._on_slot_changed)
        self.editor.zoom_changed.connect(self.canvas.set_zoom)
        self.editor.scale_changed.connect(self._on_scale_changed)
        self.editor.auto_fit_btn.clicked.connect(self._on_auto_fit)
        self.editor.rotate_l_btn.clicked.connect(self._on_rotate_left)
        self.editor.rotate_r_btn.clicked.connect(self._on_rotate_right)
        self.editor.reset_btn.clicked.connect(self._on_reset)

    # ------------------------------------------------------------------ public API

    def clear(self):
        self.filename_label.setText("--")
        self.canvas.clear()
        self.current_path = None
        self._base_image = None
        self._image_list = None
        self._template_path = None
        self._template_rgba = None
        self._placements = []
        self._slot_adjustments = []
        self._config = None
        self.editor.set_slot_count(0)

    def set_job(self, image_path: str):
        if not os.path.isfile(image_path):
            logger.warning("[PREVIEW] Image file not found: %s", image_path)
            self.clear()
            return

        self.current_path = image_path
        self.filename_label.setText(os.path.basename(image_path))

        logger.info("[PREVIEW] Opening image: %s", image_path)
        try:
            self._base_image = Image.open(image_path).convert("RGBA")
        except Exception:
            logger.exception("[PREVIEW] Failed to open image %s", image_path)
            self.clear()
            return

        auto_template = (
            self._find_template_for_image(image_path)
            if self._is_input_image(image_path)
            else None
        )
        if auto_template and os.path.isfile(auto_template):
            self._template_path = auto_template
        else:
            self._template_path = None

        # Load config and resolve placements
        self._config = self._load_config_for_image(image_path)
        if self._config and self._template_path and os.path.isfile(self._template_path):
            try:
                self._template_rgba = Image.open(self._template_path).convert("RGBA")
                self._placements = _resolve_and_validate_placements(
                    self._config, self._template_rgba.size
                )
            except Exception as exc:
                logger.warning("[PREVIEW] Placement resolution failed: %s", exc)
                self._placements = []
                self._template_rgba = None
        else:
            self._placements = []
            self._template_rgba = None

        # Load images per slot for multi-placement templates
        self._image_list = None
        num_placements = len(self._placements)
        if num_placements > 1 and self._is_input_image(image_path):
            self._image_list = self._load_multi_images(image_path, num_placements)

        # Initialize per-slot adjustments
        slot_count = max(num_placements, 1)
        self._slot_adjustments = []
        saved = self._load_adjustments_from_config(self._config) if self._config else []
        for i in range(slot_count):
            if i < len(saved) and saved[i]:
                self._slot_adjustments.append(dict(saved[i]))
            else:
                self._slot_adjustments.append(dict(_DEFAULT_ADJUSTMENTS))

        self.editor.set_slot_count(len(self._placements))
        self._current_slot = 0
        self._sync_scale_slider()

        self._re_render()

        logger.info("[PREVIEW] Loaded preview for %s", image_path)

    def set_template(self, template_path: str | None):
        if template_path and not os.path.isfile(template_path):
            logger.warning("[PREVIEW] Template file not found: %s", template_path)
            return
        self._template_path = template_path
        if template_path and self._config:
            try:
                self._template_rgba = Image.open(template_path).convert("RGBA")
                self._placements = _resolve_and_validate_placements(
                    self._config, self._template_rgba.size
                )
            except Exception as exc:
                logger.warning("[PREVIEW] Placement re-resolution failed: %s", exc)
                self._placements = []
                self._template_rgba = None
        else:
            self._template_rgba = None
            self._placements = []

        # Rebuild adjustments list to match new placement count
        new_count = len(self._placements)
        old_count = len(self._slot_adjustments)
        if new_count != old_count:
            adj = []
            for i in range(new_count):
                if i < old_count:
                    adj.append(self._slot_adjustments[i])
                else:
                    adj.append(dict(_DEFAULT_ADJUSTMENTS))
            self._slot_adjustments = adj

        self.editor.set_slot_count(new_count)
        self._sync_scale_slider()
        self._re_render()

    def get_adjustments(self) -> list[dict]:
        return [dict(a) for a in self._slot_adjustments]

    def reset_adjustments(self):
        if not self._slot_adjustments:
            return
        self._slot_adjustments[self._current_slot] = dict(_DEFAULT_ADJUSTMENTS)
        self._sync_scale_slider()
        self._re_render()

    # ------------------------------------------------------------------ internal: rendering

    def _re_render(self):
        if self._base_image is None:
            if self._template_path and os.path.isfile(self._template_path):
                try:
                    tmpl = Image.open(self._template_path).convert("RGBA")
                    pixmap = self._pil_to_pixmap(tmpl)
                    if pixmap and not pixmap.isNull():
                        self.canvas.set_pixmap(pixmap)
                except Exception:
                    self.canvas.clear()
            return

        if self.current_path and not self._is_input_image(self.current_path):
            pixmap = self._pil_to_pixmap(self._base_image)
            if pixmap:
                self.canvas.set_pixmap(pixmap)
            return

        if self._template_rgba and self._placements:
            try:
                photos = self._image_list if self._image_list else self._base_image
                preview = render_preview(
                    self._template_rgba,
                    photos,
                    self._placements,
                    self._config or {},
                    self._slot_adjustments,
                )
                logger.info(
                    "[PREVIEW] Rendered with %d slot(s), adjustments: %s",
                    len(self._placements),
                    self._slot_adjustments,
                )
            except Exception as exc:
                logger.exception("[PREVIEW] render_preview failed: %s", exc)
                preview = self._base_image
        else:
            preview = self._base_image

        pixmap = self._pil_to_pixmap(preview)
        if pixmap and not pixmap.isNull():
            self.canvas.set_pixmap(pixmap)
        else:
            self.canvas.clear()

    # ------------------------------------------------------------------ internal: adjustment handlers

    def _on_drag_started(self):
        self._render_timer.stop()

    def _on_drag_finished(self):
        self._render_timer.stop()
        self._re_render()

    def _on_photo_dragged(self, dx: float, dy: float):
        if not self._slot_adjustments:
            return
        adj = self._slot_adjustments[self._current_slot]
        adj["x_offset"] += round(dx)
        adj["y_offset"] += round(dy)
        self._render_timer.start()

    def _on_slot_changed(self, index: int):
        self._current_slot = index
        self._sync_scale_slider()

    def _on_scale_changed(self, scale: float):
        if not self._slot_adjustments:
            return
        self._slot_adjustments[self._current_slot]["scale"] = scale
        self._re_render()

    def _sync_scale_slider(self):
        if self._slot_adjustments and self._current_slot < len(self._slot_adjustments):
            val = self._slot_adjustments[self._current_slot].get("scale", 1.0)
            self.editor.set_scale_value(val)

    def _on_auto_fit(self):
        self.reset_adjustments()

    def _on_reset(self):
        self.reset_adjustments()

    def _on_rotate_left(self):
        if not self._slot_adjustments:
            return
        adj = self._slot_adjustments[self._current_slot]
        adj["rotation"] = (adj["rotation"] - 90) % 360
        self._re_render()

    def _on_rotate_right(self):
        if not self._slot_adjustments:
            return
        adj = self._slot_adjustments[self._current_slot]
        adj["rotation"] = (adj["rotation"] + 90) % 360
        self._re_render()

    # ------------------------------------------------------------------ internal: save / load adjustments

    def _get_config_path(self) -> str | None:
        if not self.current_path:
            return None
        parts = os.path.abspath(self.current_path).split(os.sep)
        try:
            idx = parts.index("hotfolders")
            preset_dir = os.sep.join(parts[: idx + 2])
        except ValueError:
            return None
        cfg = os.path.join(preset_dir, "config.json")
        return cfg if os.path.isfile(cfg) else None

    def _load_adjustments_from_config(self, config: dict | None) -> list[dict]:
        if not config:
            return []
        result = []
        placements_cfg = config.get("placements") or (
            [config.get("placement")] if config.get("placement") else []
        )
        for p in placements_cfg:
            editor = p.get("editor", {}) if isinstance(p, dict) else {}
            result.append({
                "x_offset": editor.get("x_offset", 0),
                "y_offset": editor.get("y_offset", 0),
                "scale": editor.get("scale", 1.0),
                "rotation": editor.get("rotation", 0),
            })
        return result

    def _on_save(self):
        """Write current slot adjustments into config.json."""
        cfg_path = self._get_config_path()
        if not cfg_path:
            logger.warning("[PREVIEW] No config path for save")
            return
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception as exc:
            logger.error("[PREVIEW] Failed to read config: %s", exc)
            return

        placements_cfg = config.get("placements") or (
            [config.get("placement")] if config.get("placement") else []
        )

        for i, adj in enumerate(self._slot_adjustments):
            if i >= len(placements_cfg):
                break
            placements_cfg[i]["editor"] = {
                "x_offset": adj["x_offset"],
                "y_offset": adj["y_offset"],
                "scale": adj["scale"],
                "rotation": adj["rotation"],
            }

        try:
            tmp = cfg_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
            os.replace(tmp, cfg_path)
            logger.info("[PREVIEW] Adjustments saved to %s", cfg_path)
        except Exception as exc:
            logger.error("[PREVIEW] Failed to write config: %s", exc)

    # ------------------------------------------------------------------ multi-image support

    def _load_multi_images(self, image_path: str, count: int) -> list[Image.Image] | None:
        input_dir = os.path.dirname(image_path)
        try:
            entries = sorted(
                os.path.join(input_dir, f)
                for f in os.listdir(input_dir)
                if f.lower().endswith((".png", ".jpg", ".jpeg")) and os.path.isfile(os.path.join(input_dir, f))
            )
        except Exception:
            return None
        images = []
        for path in entries[:count]:
            try:
                images.append(Image.open(path).convert("RGBA"))
            except Exception:
                images.append(self._base_image)
        if len(images) < count:
            pad = self._base_image
            images.extend([pad] * (count - len(images)))
        return images

    # ------------------------------------------------------------------ helpers (preserved)

    def _is_input_image(self, image_path: str) -> bool:
        return os.path.sep + "input" + os.path.sep in os.path.abspath(image_path)

    def _load_config_for_image(self, image_path: str) -> dict | None:
        parts = os.path.abspath(image_path).split(os.sep)
        try:
            idx = parts.index("hotfolders")
            preset_dir = os.sep.join(parts[: idx + 2])
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

    @staticmethod
    def _pil_to_pixmap(img: Image.Image) -> QtGui.QPixmap | None:
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
        input_dir = os.path.dirname(image_path)
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
            return os.path.abspath(os.path.join(preset_dir, tmpl_rel))
        except Exception:
            return None
