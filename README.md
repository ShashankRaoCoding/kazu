# Kazu - Pygame Image Dot Annotator

A simple Pygame app with a split layout:

- **Left panel**: image viewport (empty until you import an image)
- **Right panel**: menu with import button and dot counter

## Features

- Import an image using **Import Image** button
- Pan/navigate image by **right click + drag**
- Zoom with **mouse wheel** (centered around cursor)
- **Left click** on image to place a dot
- **Shift + left click** near a dot to remove it ("undot")
- Dots are stored in image coordinates, so they remain attached while panning/zooming
- Save annotations to JSON and load annotations from JSON
- Undo/redo for dot add/remove operations
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
- **Save Dots button**: saves dots to a JSON file
- **Load Dots button**: loads dots from a JSON file
- **Left click in viewport**: add dot
- **Shift + Left click in viewport near a dot**: remove dot
- **Pan image**: right mouse button drag
- **Zoom**: mouse wheel (in viewport)
- **Undo**: `Ctrl+Z`
- **Redo**: `Ctrl+Y` or `Ctrl+Shift+Z`

## Notes

- File selection/save uses `tkinter.filedialog` from Python standard library.
