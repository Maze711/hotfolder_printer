"""QGraphicsView-based canvas for interactive placement preview.

Replaces the old QLabel preview. Supports:
- Mouse-drag to adjust photo position (emits photo_dragged)
- Mouse-wheel zoom
- Fit-to-view on resize / load
"""

from PyQt5 import QtWidgets, QtCore, QtGui


class PlacementCanvas(QtWidgets.QGraphicsView):
    photo_dragged = QtCore.pyqtSignal(float, float)   # dx, dy in image pixels
    drag_started = QtCore.pyqtSignal()
    drag_finished = QtCore.pyqtSignal()
    zoom_changed = QtCore.pyqtSignal(int)              # zoom percentage

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QtWidgets.QGraphicsScene(self)
        self.setScene(self._scene)

        self._pixmap_item = QtWidgets.QGraphicsPixmapItem()
        self._scene.addItem(self._pixmap_item)

        self._dragging = False
        self._last_scene_pos = None

        # Rendering quality
        self.setRenderHints(
            QtGui.QPainter.SmoothPixmapTransform | QtGui.QPainter.Antialiasing
        )
        self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.setMinimumSize(200, 200)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                           QtWidgets.QSizePolicy.Expanding)

    # ------------------------------------------------------------------ public API

    def set_pixmap(self, pixmap: QtGui.QPixmap):
        self._pixmap_item.setPixmap(pixmap)
        self._scene.setSceneRect(QtCore.QRectF(pixmap.rect()))
        self._fit()

    def clear(self):
        self._pixmap_item.setPixmap(QtGui.QPixmap())
        self._scene.setSceneRect(QtCore.QRectF())

    def set_zoom(self, percent: int):
        """Programmatic zoom (called from slider)."""
        factor = percent / 100.0
        self.resetTransform()
        self.scale(factor, factor)

    def current_zoom(self) -> int:
        t = self.transform()
        return max(1, round(t.m11() * 100))

    # ------------------------------------------------------------------ internal

    def _fit(self):
        if self._pixmap_item.pixmap() and not self._pixmap_item.pixmap().isNull():
            self.fitInView(self._pixmap_item, QtCore.Qt.KeepAspectRatio)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit()

    def wheelEvent(self, event):
        factor = 1.15
        if event.angleDelta().y() > 0:
            self.scale(factor, factor)
        else:
            self.scale(1 / factor, 1 / factor)
        self.zoom_changed.emit(self.current_zoom())

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._dragging = True
            self._last_scene_pos = self.mapToScene(event.pos())
            self.setCursor(QtCore.Qt.ClosedHandCursor)
            self.drag_started.emit()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging and self._last_scene_pos is not None:
            current = self.mapToScene(event.pos())
            dx = current.x() - self._last_scene_pos.x()
            dy = current.y() - self._last_scene_pos.y()
            self._last_scene_pos = current
            self.photo_dragged.emit(dx, dy)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton and self._dragging:
            self._dragging = False
            self._last_scene_pos = None
            self.setCursor(QtCore.Qt.ArrowCursor)
            self.drag_finished.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)
