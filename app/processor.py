from PIL import Image
import os
from printer import print_image

def process_job(job):
    image_path = job["file"]
    config = job["config"]

    placement = config["placement"]

    template = Image.open(config["template"]).convert("RGB")
    photo = Image.open(image_path).convert("RGB")

    photo = photo.resize((placement["width"], placement["height"]))

    template.paste(photo, (placement["x"], placement["y"]))

    os.makedirs(config["output"], exist_ok=True)

    output_path = os.path.join(
        config["output"],
        os.path.basename(image_path)
    )

    template.save(output_path)

    print(f"[SAVED] {output_path}")

    print_image(output_path, config.get("printer_name"))