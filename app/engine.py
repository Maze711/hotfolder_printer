import json
import os
import time

from job_queue import PrintQueue
from logging_utils import get_logger, setup_logging
from processor import process_job
from watcher import start_watcher


APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(APP_DIR)
BASE_DIR = os.path.join(PROJECT_ROOT, "hotfolders")

logger = get_logger(__name__)
SUPPORTED_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png")


def _validate_and_enrich_preset(path, config):
    if not isinstance(config, dict):
        raise ValueError("config.json must be a JSON object")

    template_rel = config.get("template")
    if not template_rel or not isinstance(template_rel, str):
        raise ValueError("template must be a non-empty string")

    template_path = os.path.abspath(os.path.join(path, template_rel))
    if not os.path.isfile(template_path):
        raise FileNotFoundError(f"template missing: {template_path}")

    input_path = os.path.join(path, "input")
    output_path = os.path.join(path, "output")
    os.makedirs(input_path, exist_ok=True)
    os.makedirs(output_path, exist_ok=True)

    config["base_path"] = path
    config["template"] = template_path
    config["input"] = input_path
    config["output"] = output_path
    return config


def load_presets():
    presets = []

    if not os.path.isdir(BASE_DIR):
        raise FileNotFoundError(f"Hotfolders directory not found: {BASE_DIR}")

    for folder in os.listdir(BASE_DIR):
        path = os.path.join(BASE_DIR, folder)
        if not os.path.isdir(path):
            continue

        config_path = os.path.join(path, "config.json")
        if not os.path.exists(config_path):
            continue

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            presets.append(_validate_and_enrich_preset(path, config))
            logger.info("[LOADED] %s", path)
        except Exception as exc:
            logger.error("[PRESET ERROR] %s: %s", path, exc)

    return presets


def _enqueue_existing_input_files(preset, queue):
    input_path = preset["input"]
    queued_count = 0

    try:
        for entry in os.listdir(input_path):
            file_path = os.path.join(input_path, entry)
            if not os.path.isfile(file_path):
                continue
            if not entry.lower().endswith(SUPPORTED_IMAGE_EXTENSIONS):
                continue

            queue.add_job({
                "file": os.path.abspath(file_path),
                "config": preset,
            })
            queued_count += 1
    except Exception as exc:
        logger.error("[INPUT SCAN ERROR] %s: %s", input_path, exc)
        return

    if queued_count:
        logger.info("[INPUT SCAN] Queued %s existing file(s) from %s", queued_count, input_path)


def start_engine():
    setup_logging(PROJECT_ROOT)

    queue = PrintQueue()
    queue.start(process_job)

    presets = load_presets()
    observers = []

    for preset in presets:
        try:
            observer = start_watcher(preset["input"], preset, queue)
            observers.append(observer)
            _enqueue_existing_input_files(preset, queue)
        except Exception as exc:
            logger.error("[WATCHER ERROR] %s: %s", preset.get("base_path", "unknown"), exc)

    if not observers:
        logger.warning("[ENGINE] No active watchers. Check hotfolder configs.")
        return

    logger.info("[ENGINE] Running with %s watcher(s)", len(observers))

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("[ENGINE] Shutdown requested")
    finally:
        for observer in observers:
            observer.stop()
        for observer in observers:
            observer.join()
