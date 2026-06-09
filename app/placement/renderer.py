from PIL import Image
from .composer import _compose_photo
from .masker import _apply_black_guide_mask


def _apply_slot_adjustments(composed, placement, adjustments):
    scale = adjustments.get("scale", 1.0)
    rotation = adjustments.get("rotation", 0)

    if scale != 1.0:
        new_size = (max(1, int(composed.width * scale)),
                    max(1, int(composed.height * scale)))
        composed = composed.resize(new_size, Image.Resampling.LANCZOS)

    if rotation != 0:
        composed = composed.rotate(rotation, expand=True,
                                   resample=Image.Resampling.BICUBIC,
                                   center=(composed.width // 2, composed.height // 2))

    # Clip to placement bounding box — any overflow after scale/rotate is hidden
    pw, ph = placement["width"], placement["height"]
    if composed.width > pw or composed.height > ph:
        left = (composed.width - pw) // 2
        top = (composed.height - ph) // 2
        composed = composed.crop((left, top, left + pw, top + ph))

    x_offset = adjustments.get("x_offset", 0)
    y_offset = adjustments.get("y_offset", 0)

    paste_x = placement["x"] + (placement["width"] - composed.width) // 2 + x_offset
    paste_y = placement["y"] + (placement["height"] - composed.height) // 2 + y_offset

    return composed, paste_x, paste_y


def render_preview(template_rgba, photo_rgba, placements, config, slot_adjustments=None):
    if slot_adjustments is None:
        slot_adjustments = [{} for _ in placements]

    if isinstance(photo_rgba, list):
        photo_list = photo_rgba
    else:
        photo_list = [photo_rgba] * len(placements)

    if len(photo_list) < len(placements):
        photo_list = photo_list + [photo_list[-1]] * (len(placements) - len(photo_list))
    photo_list = photo_list[:len(placements)]

    masked_template = _apply_black_guide_mask(template_rgba, config, placements)

    underlay = Image.new("RGBA", template_rgba.size, (0, 0, 0, 0))

    for idx, placement in enumerate(placements):
        adj = slot_adjustments[idx] if idx < len(slot_adjustments) else {}

        composed = _compose_photo(photo_list[idx], placement).convert("RGBA")
        composed, paste_x, paste_y = _apply_slot_adjustments(composed, placement, adj)
        underlay.paste(composed, (paste_x, paste_y))

    return Image.alpha_composite(underlay, masked_template)
