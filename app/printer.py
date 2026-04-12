import win32api
import win32print
import os

def print_image(file_path, printer_name=None):
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

        print(f"[PRINT] Sending to printer: {file_path}")

        # Windows shell print command (simple & reliable)
        win32api.ShellExecute(
            0,
            "print",
            file_path,
            None,
            ".",
            0
        )

        print("[PRINT] Job sent successfully")

    except Exception as e:
        print(f"[PRINTER ERROR] {e}")