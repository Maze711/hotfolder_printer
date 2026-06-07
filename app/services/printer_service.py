"""Printer service – controls pause/resume of the backend.

The UI calls ``pause_queue`` and ``resume_queue`` which toggle the
``system_state.json`` flag used by the backend (see ``app/system_state.py``).
"""

from ..system_state import set_paused, is_paused

class PrinterService:
    """Expose a thin API for the dashboard.

    The backend reads the flag via ``system_state.is_paused()`` before each
    job, so toggling it here instantly affects processing.
    """

    @staticmethod
    def pause_queue() -> bool:
        """Set the pause flag to ``True``. Returns ``True`` if operation succeeded."""
        try:
            set_paused(True)
            return True
        except Exception:
            return False

    @staticmethod
    def resume_queue() -> bool:
        """Clear the pause flag. Returns ``True`` if operation succeeded."""
        try:
            set_paused(False)
            return True
        except Exception:
            return False

    @staticmethod
    def is_paused() -> bool:
        """Query the current pause state."""
        try:
            return is_paused()
        except Exception:
            return False
