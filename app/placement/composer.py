import os
from PIL import Image, ImageOps


def _compose_photo(photo, placement):
    target_size = (placement["width"], placement["height"])

    if placement["mode"] == "fill":
        return ImageOps.fit(photo, target_size, method=Image.Resampling.LANCZOS)

    return ImageOps.contain(photo, target_size, method=Image.Resampling.LANCZOS)


def _build_output_filename(image_paths):
    if len(image_paths) == 1:
        return os.path.basename(image_paths[0])

    stems = [os.path.splitext(os.path.basename(path))[0] for path in image_paths]
    ext = os.path.splitext(os.path.basename(image_paths[0]))[1] or ".jpg"
    return f"{'__'.join(stems)}{ext}"
