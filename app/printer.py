import win32api
import win32print
import os

def print_image(file_path, printer_name=None, print_settings=None):
    if print_settings is None:
        print_settings = {}

    try:
        # Optional: set default printer
        if printer_name:
            try:
                win32print.SetDefaultPrinter(printer_name)
            except Exception as e:
                print(f"[PRINTER WARNING] Could not set printer: {e}")

        # Validate file exists
        if not os.path.exists(file_path):
            print(f"[PRINTER ERROR] File not found: {file_path}")
            return

        mode = str(print_settings.get("mode", "dialog")).lower()
        if mode not in {"dialog", "silent"}:
            mode = "dialog"

        print(f"[PRINT] Preparing print job: {file_path} (mode={mode})")

        # dialog: open Windows Print Pictures dialog for manual confirmation
        # silent: submit via shell print without changing flow
        win32api.ShellExecute(
            0,
            "print",
            file_path,
            None,
            ".",
            0
        )

        if mode == "dialog":
            print("[PRINT] Print dialog opened")
        else:
            print("[PRINT] Job sent successfully")

    except Exception as e:
        print(f"[PRINTER ERROR] {e}")