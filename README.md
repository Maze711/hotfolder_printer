# Hotfolder Printer System

Python-based hotfolder printing system for photobooth setups.

## Features
- Folder monitoring (watchdog)
- Image processing (Pillow)
- Template-based layouts
- Automatic printing (Windows / Epson)
- Hotfolder preset system (config-driven)

## What Is Implemented Per Hotfolder

Each hotfolder preset must have this structure:

```text
hotfolders/<preset_name>/
	config.json
	template.png
	input/
	output/
```

### 1) landscape (implemented)

- Path: `hotfolders/landscape`
- Status: active and loaded by engine
- Config file: `hotfolders/landscape/config.json`

Current `landscape` behavior:

- Input watch folder: `hotfolders/landscape/input`
- Output folder: `hotfolders/landscape/output`
- Template file: `hotfolders/landscape/template.png`
- Print mode: `dialog`
- Placement mode: `fill`

Template and photo area rules for `landscape`:

- Paper size is defined in mm:
	- `paper_width_mm`: 152
	- `paper_height_mm`: 102
- Photo area size is defined in mm:
	- `width_mm`: 143.68
	- `height_mm`: 75.35
- Vertical offset is defined by `y: 13%`.
- `x` is ignored in this preset because image placement is auto-detected from the template.

Black placeholder requirement:

- `auto_detect_black_placeholder: true` is enabled.
- In `template.png`, draw a solid black rectangle where the photo should go.
- The system finds the largest connected black area and uses it as the photo placement box.
- Detection settings:
	- `black_threshold`: 25
	- `black_min_pixels`: 2500

If no black placeholder is found, the engine falls back to config placement values.

### 2) polaroid (not implemented yet)

- Path: `hotfolders/polaroid`
- Status: folder exists, no `config.json` yet

### 3) strip (not implemented yet)

- Path: `hotfolders/strip`
- Status: folder exists, no `config.json` yet

## How A Job Flows

1. User drops `.jpg/.jpeg/.png` into `input/`.
2. Engine loads `template.png` and source image.
3. Engine resolves placement from black placeholder (or fallback config).
4. Source image is composed into template (`fill` or `fit`).
5. Final file is saved to `output/`.
6. Print command is sent to Windows shell (`dialog` or `silent`).

## Tech Stack
- Python 3.12
- watchdog
- Pillow
- pywin32