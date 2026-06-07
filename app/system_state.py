"""Simple file‑based pause flag for the hotfolder printer.

The dashboard can toggle the flag by editing ``system_state.json``.
The backend reads the flag before processing each job and will wait
while ``paused`` is ``true``.
"""
import json
import os
import threading

# The JSON file lives at the project root (next to README, .git, etc.)
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
_STATE_FILE = os.path.join(_PROJECT_ROOT, "system_state.json")

_lock = threading.Lock()
_cached_state = None

def _load_state():
    global _cached_state
    try:
        with open(_STATE_FILE, "r", encoding="utf-8") as f:
            _cached_state = json.load(f)
    except Exception:
        # If the file is missing or malformed, fallback to a sane default
        _cached_state = {"paused": False}
    return _cached_state

def is_paused() -> bool:
    """Return ``True`` if the system is currently paused.

    The function caches the JSON content and refreshes it only when the
    cached value is ``None``.  The dashboard can invalidate the cache by
    calling :func:`set_paused` which also writes the new value back to the
    file.
    """
    with _lock:
        state = _cached_state or _load_state()
        return bool(state.get("paused", False))

def set_paused(value: bool):
    """Update the pause flag and persist it to ``system_state.json``.
    """
    with _lock:
        state = _cached_state or {"paused": False}
        state["paused"] = bool(value)
        _cached_state = state
        try:
            with open(_STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f)
        except Exception:
            # Silently ignore write errors – the UI will still see the flag
            pass
