import os
from PIL import Image
from app.printer import print_image
from app.logging_utils import get_logger

from .validator import (
    _resolve_and_validate_placements,
    _validate_placeholder_against_config,
    _validate_required_image_count,
)
from .masker import _apply_black_guide_mask
from .composer import _compose_photo, _build_output_filename
from .renderer import render_preview  # noqa: F401


logger = get_logger("processor")


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
