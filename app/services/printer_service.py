"""Printer service – controls pause/resume of the backend.

The UI calls ``pause_queue`` and ``resume_queue`` which toggle the
``system_state.json`` flag used by the backend (see ``app/system_state.py``).
"""

from ..system_state import set_paused, is_paused
from ..logging_utils import get_logger
logger = get_logger(__name__)



class PrinterService:
    """Expose a thin API for the dashboard.

    The backend reads the flag via ``system_state.is_paused()`` before each
    job, so toggling it here instantly affects processing.
    """

    @staticmethod
    def print_file(file_path: str, config: dict | None = None) -> bool:
        """Print *file_path* using the configured printer.

        ``config`` can contain ``printer_name`` and ``print_settings`` just like the
        internal ``processor`` does. Returns ``True`` on success.
        """
        try:
            # Import locally to avoid circular imports
            from ..printer import print_image
            printer_name = None
            print_settings = {}
            if config:
                printer_name = config.get("printer_name")
                print_settings = config.get("print_settings", {})
            print_image(file_path, printer_name=printer_name, print_settings=print_settings)
            return True
        except Exception as exc:
            logger.error("[PRINT SERVICE] Failed to print %s: %s", file_path, exc)
            return False

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






