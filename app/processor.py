from collections import deque
from PIL import Image, ImageOps
import os
from printer import print_image
from logging_utils import get_logger


logger = get_logger(__name__)


SUPPORTED_MODES = {"fit", "fill"}


def _require_number(value, field_name):
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be numeric")
    if isinstance(value, (int, float)):
        return float(value)
    raise ValueError(f"{field_name} must be numeric")


def _require_pixels(value, total, field_name):
    if value is None:
        raise ValueError(f"Missing required placement field: {field_name}")

    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            raise ValueError(f"{field_name} cannot be empty")

        if raw.endswith("%"):
            percent_raw = raw[:-1].strip()
            try:
                percent = float(percent_raw)
            except ValueError as exc:
                raise ValueError(f"{field_name} has invalid percentage value: {value}") from exc
            return int(total * (percent / 100.0))

        try:
            numeric = float(raw)
        except ValueError as exc:
            raise ValueError(f"{field_name} has invalid numeric value: {value}") from exc

        if 0 <= numeric <= 1:
            return int(total * numeric)
        return int(numeric)

    if isinstance(value, (int, float)):
        if 0 <= float(value) <= 1:
            return int(total * float(value))
        return int(value)

    raise ValueError(f"{field_name} must be a number or percentage string")


def _mm_to_px(mm_value, axis_total, paper_mm, dpi, field_name):
    if mm_value is None:
        return None

    mm = _require_number(mm_value, field_name)
    if mm < 0:
        raise ValueError(f"{field_name} must be >= 0")

    if paper_mm is not None:
        paper = _require_number(paper_mm, f"paper size for {field_name}")
        if paper <= 0:
            raise ValueError(f"paper size for {field_name} must be > 0")
        return int(axis_total * (mm / paper))

    return int((mm / 25.4) * dpi)


def _resolve_and_validate_placement(config, template_size):
    template_width, template_height = template_size

    placement = config.get("placement")
    if not isinstance(placement, dict):
        raise ValueError("placement must be an object in config")

    area = placement.get("area", placement)
    if not isinstance(area, dict):
        raise ValueError("placement.area must be an object")

    mode = str(placement.get("mode", "fit")).lower()
    if mode not in SUPPORTED_MODES:
        raise ValueError(f"placement.mode must be one of {sorted(SUPPORTED_MODES)}")

    if area.get("x") is None and area.get("x_mm") is None:
        raise ValueError("placement.x or placement.x_mm is required")
    if area.get("y") is None and area.get("y_mm") is None:
        raise ValueError("placement.y or placement.y_mm is required")
    if area.get("width") is None and area.get("width_mm") is None:
        raise ValueError("placement.width or placement.width_mm is required")
    if area.get("height") is None and area.get("height_mm") is None:
        raise ValueError("placement.height or placement.height_mm is required")

    x = _require_pixels(area.get("x", 0), template_width, "placement.x")
    y = _require_pixels(area.get("y", 0), template_height, "placement.y")
    width = _require_pixels(area.get("width", 1), template_width, "placement.width")
    height = _require_pixels(area.get("height", 1), template_height, "placement.height")

    paper_width_mm = area.get("paper_width_mm")
    paper_height_mm = area.get("paper_height_mm")
    dpi = _require_number(area.get("dpi", 300), "placement.dpi")
    if dpi <= 0:
        raise ValueError("placement.dpi must be > 0")

    x_mm_px = _mm_to_px(area.get("x_mm"), template_width, paper_width_mm, dpi, "placement.x_mm")
    y_mm_px = _mm_to_px(area.get("y_mm"), template_height, paper_height_mm, dpi, "placement.y_mm")
    width_mm_px = _mm_to_px(area.get("width_mm"), template_width, paper_width_mm, dpi, "placement.width_mm")
    height_mm_px = _mm_to_px(area.get("height_mm"), template_height, paper_height_mm, dpi, "placement.height_mm")

    if x_mm_px is not None:
        x = x_mm_px
    if y_mm_px is not None:
        y = y_mm_px
    if width_mm_px is not None:
        width = width_mm_px
    if height_mm_px is not None:
        height = height_mm_px

    if x < 0 or y < 0:
        raise ValueError("placement x/y must be >= 0")
    if width <= 0 or height <= 0:
        raise ValueError("placement width/height must be > 0")
    if x + width > template_width:
        raise ValueError("placement exceeds template width")
    if y + height > template_height:
        raise ValueError("placement exceeds template height")

    return {
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "mode": mode,
    }


def _resolve_and_validate_placements(config, template_size):
    placements_cfg = config.get("placements")
    if placements_cfg is None:
        return [_resolve_and_validate_placement(config, template_size)]

    if not isinstance(placements_cfg, list) or not placements_cfg:
        raise ValueError("placements must be a non-empty array")

    resolved = []
    for idx, placement in enumerate(placements_cfg):
        if not isinstance(placement, dict):
            raise ValueError(f"placements[{idx}] must be an object")

        merged = dict(config)
        merged["placement"] = placement
        resolved.append(_resolve_and_validate_placement(merged, template_size))

    return resolved

def _detect_black_placeholders(template, threshold=25, min_pixels=2500):
    if threshold < 0 or threshold > 255:
        raise ValueError("black threshold must be in range 0-255")
    if min_pixels <= 0:
        raise ValueError("black_min_pixels must be > 0")

    gray = template.convert("L")
    width, height = gray.size
    pixels = gray.tobytes()
    total = width * height
    visited = bytearray(total)

    def is_black(index):
        return pixels[index] <= threshold

    components = []

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

        if count >= min_pixels:
            components.append(
                {
                    "x": min_x,
                    "y": min_y,
                    "width": (max_x - min_x) + 1,
                    "height": (max_y - min_y) + 1,
                    "pixels": count,
                }
            )

    components.sort(key=lambda c: (c["y"], c["x"]))
    return components


def _compose_photo(photo, placement):
    target_size = (placement["width"], placement["height"])

    if placement["mode"] == "fill":
        # Fill crops photo to completely cover the target area.
        return ImageOps.fit(photo, target_size, method=Image.Resampling.LANCZOS)

    # Fit keeps the full image visible and letterboxes if needed.
    return ImageOps.contain(photo, target_size, method=Image.Resampling.LANCZOS)


def _validate_placeholder_against_config(template_rgba, config, placements):
    if not bool(config.get("auto_detect_black_placeholder", False)):
        return

    threshold = int(config.get("black_threshold", 25))
    min_pixels = int(config.get("black_min_pixels", 2500))
    detected = _detect_black_placeholders(template_rgba, threshold=threshold, min_pixels=min_pixels)

    if not detected:
        raise ValueError("placeholder validation failed: no black placeholder detected")

    if len(detected) < len(placements):
        raise ValueError(
            "placeholder validation failed: "
            f"detected {len(detected)} placeholder(s) but config needs {len(placements)}"
        )

    # Match only the strongest candidates so decorative black text does not fail validation.
    detected = sorted(detected, key=lambda item: item["pixels"], reverse=True)[: len(placements)]
    detected.sort(key=lambda c: (c["y"], c["x"]))
    expected = sorted(placements, key=lambda c: (c["y"], c["x"]))

    tolerance = int(config.get("placeholder_tolerance_px", 15))
    if tolerance < 0:
        raise ValueError("placeholder_tolerance_px must be >= 0")

    mismatches = []
    for idx, (detected_item, placement_item) in enumerate(zip(detected, expected)):
        for field in ("x", "y", "width", "height"):
            if abs(detected_item[field] - placement_item[field]) > tolerance:
                mismatches.append(
                    "slot "
                    f"{idx} {field} detected={detected_item[field]} "
                    f"config={placement_item[field]} tolerance={tolerance}"
                )

    if mismatches:
        raise ValueError("placeholder validation failed: " + "; ".join(mismatches))


def _apply_black_guide_mask(template_rgba, config, placements):
    if not bool(config.get("use_black_guides_as_mask", True)):
        return template_rgba

    threshold = int(config.get("black_threshold", 25))
    tolerance = int(config.get("black_mask_tolerance", 10))
    if threshold < 0 or threshold > 255:
        raise ValueError("black threshold must be in range 0-255")
    if tolerance < 0:
        raise ValueError("black_mask_tolerance must be >= 0")

    masked = template_rgba.copy()
    px = masked.load()
    threshold_value = min(255, threshold + tolerance)

    for placement in placements:
        x0 = placement["x"]
        y0 = placement["y"]
        x1 = x0 + placement["width"]
        y1 = y0 + placement["height"]

        for y in range(y0, y1):
            for x in range(x0, x1):
                r, g, b, a = px[x, y]
                if a == 0:
                    continue
                if r <= threshold_value and g <= threshold_value and b <= threshold_value:
                    px[x, y] = (r, g, b, 0)

    return masked


def _validate_required_image_count(config, image_paths):
    raw_value = config.get("images_per_template", 1)
    try:
        required_images = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError("images_per_template must be an integer") from exc

    if required_images <= 0:
        raise ValueError("images_per_template must be > 0")

    if len(image_paths) != required_images:
        raise ValueError(
            f"{config.get('name', 'hotfolder')} requires exactly {required_images} input image(s) "
            f"per template, got {len(image_paths)}"
        )


def _build_output_filename(image_paths):
    if len(image_paths) == 1:
        return os.path.basename(image_paths[0])

    stems = [os.path.splitext(os.path.basename(path))[0] for path in image_paths]
    ext = os.path.splitext(os.path.basename(image_paths[0]))[1] or ".jpg"
    return f"{'__'.join(stems)}{ext}"

def process_job(job):
    image_paths = job.get("files") or [job["file"]]
    config = job["config"]

    template_path = config.get("template")
    if not template_path:
        raise ValueError("config missing template path")
    if not os.path.isfile(template_path):
        raise FileNotFoundError(f"template not found: {template_path}")

    for image_path in image_paths:
        if not os.path.isfile(image_path):
            raise FileNotFoundError(f"input image not found: {image_path}")

    _validate_required_image_count(config, image_paths)

    with Image.open(template_path) as template_image:
        template_rgba = template_image.convert("RGBA")

    placements = _resolve_and_validate_placements(config, template_rgba.size)
    _validate_placeholder_against_config(template_rgba, config, placements)

    masked_template = _apply_black_guide_mask(template_rgba, config, placements)

    if len(image_paths) == 1:
        slot_paths = [image_paths[0]] * len(placements)
    elif len(image_paths) == len(placements):
        slot_paths = image_paths
    else:
        raise ValueError(
            f"input image count ({len(image_paths)}) must be 1 or equal to placement count ({len(placements)})"
        )

    underlay = Image.new("RGBA", template_rgba.size, (0, 0, 0, 0))
    for placement, slot_path in zip(placements, slot_paths):
        with Image.open(slot_path) as photo_image:
            photo = photo_image.convert("RGB")

        composed_photo = _compose_photo(photo, placement).convert("RGBA")
        paste_x = placement["x"] + (placement["width"] - composed_photo.width) // 2
        paste_y = placement["y"] + (placement["height"] - composed_photo.height) // 2
        underlay.paste(composed_photo, (paste_x, paste_y))

    # Keep template artwork intact by compositing the photo below template pixels.
    final_image = Image.alpha_composite(underlay, masked_template).convert("RGB")

    output_dir = config.get("output")
    if not output_dir:
        raise ValueError("config missing output directory")

    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, _build_output_filename(image_paths))
    final_image.save(output_path)

    logger.info("[SAVED] %s", output_path)

    print_image(
        output_path,
        config.get("printer_name"),
        config.get("print_settings", {}),
    )