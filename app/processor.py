from collections import deque
from PIL import Image, ImageOps
import os
from printer import print_image


def _to_pixels(value, total, default):
    if value is None:
        return default

    if isinstance(value, str):
        raw = value.strip()
        if raw.endswith("%"):
            try:
                return int(total * (float(raw[:-1]) / 100.0))
            except ValueError:
                return default
        try:
            value = float(raw)
        except ValueError:
            return default

    if isinstance(value, (int, float)):
        if 0 <= value <= 1:
            return int(total * value)
        return int(value)

    return default


def _resolve_placement(config, template_size):
    template_width, template_height = template_size

    placement = config.get("placement", {})
    area = placement.get("area", placement)
    mode = str(placement.get("mode", "fit")).lower()
    if mode not in {"fit", "fill"}:
        mode = "fit"

    x = _to_pixels(area.get("x"), template_width, 0)
    y = _to_pixels(area.get("y"), template_height, 0)
    width = _to_pixels(area.get("width"), template_width, template_width)
    height = _to_pixels(area.get("height"), template_height, template_height)

    paper_width_mm = area.get("paper_width_mm")
    paper_height_mm = area.get("paper_height_mm")
    dpi = float(area.get("dpi", 300))

    def mm_to_px(mm_value, axis_total, paper_mm):
        if mm_value is None:
            return None
        mm_value = float(mm_value)
        if paper_mm:
            return int(axis_total * (mm_value / float(paper_mm)))
        return int((mm_value / 25.4) * dpi)

    x_mm_px = mm_to_px(area.get("x_mm"), template_width, paper_width_mm)
    y_mm_px = mm_to_px(area.get("y_mm"), template_height, paper_height_mm)
    width_mm_px = mm_to_px(area.get("width_mm"), template_width, paper_width_mm)
    height_mm_px = mm_to_px(area.get("height_mm"), template_height, paper_height_mm)

    if x_mm_px is not None:
        x = x_mm_px
    if y_mm_px is not None:
        y = y_mm_px
    if width_mm_px is not None:
        width = width_mm_px
    if height_mm_px is not None:
        height = height_mm_px

    # Keep the placement area valid even if config values are off.
    x = max(0, min(x, template_width - 1))
    y = max(0, min(y, template_height - 1))
    width = max(1, min(width, template_width - x))
    height = max(1, min(height, template_height - y))

    return {
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "mode": mode,
    }


def _detect_black_placeholder(template, threshold=25, min_pixels=2500):
    gray = template.convert("L")
    width, height = gray.size
    pixels = gray.tobytes()
    total = width * height
    visited = bytearray(total)

    def is_black(index):
        return pixels[index] <= threshold

    largest = None
    largest_count = 0

    for idx in range(total):
        if visited[idx] or not is_black(idx):
            continue

        queue = deque([idx])
        visited[idx] = 1
        count = 0

        start_x = idx % width
        start_y = idx // width
        min_x = max_x = start_x
        min_y = max_y = start_y

        while queue:
            current = queue.popleft()
            x = current % width
            y = current // width
            count += 1

            if x < min_x:
                min_x = x
            if x > max_x:
                max_x = x
            if y < min_y:
                min_y = y
            if y > max_y:
                max_y = y

            if x > 0:
                left = current - 1
                if not visited[left] and is_black(left):
                    visited[left] = 1
                    queue.append(left)

            if x < width - 1:
                right = current + 1
                if not visited[right] and is_black(right):
                    visited[right] = 1
                    queue.append(right)

            if y > 0:
                up = current - width
                if not visited[up] and is_black(up):
                    visited[up] = 1
                    queue.append(up)

            if y < height - 1:
                down = current + width
                if not visited[down] and is_black(down):
                    visited[down] = 1
                    queue.append(down)

        if count > largest_count:
            largest_count = count
            largest = {
                "x": min_x,
                "y": min_y,
                "width": (max_x - min_x) + 1,
                "height": (max_y - min_y) + 1,
            }

    if largest and largest_count >= min_pixels:
        return largest

    return None


def _compose_photo(photo, placement):
    target_size = (placement["width"], placement["height"])

    if placement["mode"] == "fill":
        # Fill crops photo to completely cover the target area.
        return ImageOps.fit(photo, target_size, method=Image.Resampling.LANCZOS)

    # Fit keeps the full image visible and letterboxes if needed.
    return ImageOps.contain(photo, target_size, method=Image.Resampling.LANCZOS)

def process_job(job):
    image_path = job["file"]
    config = job["config"]

    template = Image.open(config["template"]).convert("RGB")
    photo = Image.open(image_path).convert("RGB")
    placement = _resolve_placement(config, template.size)

    detect_black = bool(config.get("auto_detect_black_placeholder", False))
    if detect_black:
        threshold = int(config.get("black_threshold", 25))
        min_pixels = int(config.get("black_min_pixels", 2500))
        detected = _detect_black_placeholder(template, threshold=threshold, min_pixels=min_pixels)
        if detected:
            placement["x"] = detected["x"]
            placement["y"] = detected["y"]
            placement["width"] = detected["width"]
            placement["height"] = detected["height"]
            print(
                f"[PLACEMENT] Black placeholder detected at "
                f"x={detected['x']}, y={detected['y']}, "
                f"w={detected['width']}, h={detected['height']}"
            )
        else:
            print("[PLACEMENT WARNING] No black placeholder detected, using configured placement")

    composed_photo = _compose_photo(photo, placement)

    paste_x = placement["x"] + (placement["width"] - composed_photo.width) // 2
    paste_y = placement["y"] + (placement["height"] - composed_photo.height) // 2

    template.paste(composed_photo, (paste_x, paste_y))

    os.makedirs(config["output"], exist_ok=True)

    output_path = os.path.join(
        config["output"],
        os.path.basename(image_path)
    )

    template.save(output_path)

    print(f"[SAVED] {output_path}")

    print_image(output_path, config.get("printer_name"))