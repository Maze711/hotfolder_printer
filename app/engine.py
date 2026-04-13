import os
import json
from watcher import start_watcher
from job_queue import PrintQueue
from processor import process_job

APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(APP_DIR)
BASE_DIR = os.path.join(PROJECT_ROOT, "hotfolders")

def load_presets():
    presets = []

    if not os.path.isdir(BASE_DIR):
        raise FileNotFoundError(f"Hotfolders directory not found: {BASE_DIR}")

    for folder in os.listdir(BASE_DIR):
        path = os.path.join(BASE_DIR, folder)

        config_path = os.path.join(path, "config.json")

        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = json.load(f)

            config["base_path"] = path
            config["template"] = os.path.join(path, config["template"])
            config["input"] = os.path.join(path, "input")
            config["output"] = os.path.join(path, "output")

            presets.append(config)

    return presets


def start_engine():
    queue = PrintQueue()

    # start worker
    queue.start(process_job)

    presets = load_presets()

    for preset in presets:
        start_watcher(preset["input"], preset, queue)
        print(f"[LOADED] {preset['base_path']}")

    print("[ENGINE] Running...")