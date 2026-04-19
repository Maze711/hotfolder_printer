import win32api
import win32print
import os
from logging_utils import get_logger


logger = get_logger(__name__)

def print_image(file_path, printer_name=None, print_settings=None):
    if print_settings is None:
        print_settings = {}

    try:
        if printer_name:
            try:
                win32print.SetDefaultPrinter(printer_name)
            except Exception as e:
                logger.warning("[PRINTER WARNING] Could not set printer: %s", e)

        if not os.path.exists(file_path):
            logger.error("[PRINTER ERROR] File not found: %s", file_path)
            return

        mode = str(print_settings.get("mode", "dialog")).lower()
        if mode not in {"dialog", "silent"}:
            raise ValueError("print_settings.mode must be either 'dialog' or 'silent'")

        logger.info("[PRINT] Preparing print job: %s (mode=%s)", file_path, mode)

        win32api.ShellExecute(
            0,
            "print",
            file_path,
            None,
            ".",
            0
        )

        if mode == "dialog":
            logger.info("[PRINT] Print dialog opened")
        else:
            logger.info("[PRINT] Job sent successfully")

    except Exception as e:
        logger.exception("[PRINTER ERROR] %s", e)