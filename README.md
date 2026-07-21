# Kazu - Pygame Image Dot Annotator

A simple Pygame app with a split layout:

- **Left panel**: image viewport (empty until you import an image)
- **Right panel**: menu with import button and dot counter

## Features

- Import an image using **Import Image** button
- Pan/navigate image by **middle mouse drag** or **Shift + left drag**
- **Left click** on image to place a dot
- **Right click** near a dot to remove it ("undot")
- Dots are stored in image coordinates, so they move correctly when panning
- Live dot count in the right menu

## Requirements

- Python 3.9+
- pygame

Install dependency:

```bash
pip install pygame
```

## Run

```bash
python app.py
```

## Controls

- **Import Image button** (right panel): opens file picker
- **Left click in viewport**: add dot
- **Right click in viewport near a dot**: remove dot
- **Pan image**:
  - middle mouse button drag, or
  - hold Shift and drag with left mouse button

## Notes

- File selection uses `tkinter.filedialog` from Python standard library.
- Click interactions are ignored while panning.
