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
