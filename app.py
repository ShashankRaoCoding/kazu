import json
import os
import sys
from dataclasses import dataclass

import pygame


# ---------- Optional tkinter import for native file dialog ----------
try:
    import tkinter as tk
    from tkinter import filedialog
except Exception:  # pragma: no cover
    tk = None
    filedialog = None


# ---------- Layout / style ----------
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 780
MENU_WIDTH = 320
VIEWPORT_WIDTH = WINDOW_WIDTH - MENU_WIDTH
VIEWPORT_HEIGHT = WINDOW_HEIGHT

BG_COLOR = (30, 30, 35)
VIEWPORT_BG = (20, 20, 24)
MENU_BG = (40, 40, 48)
TEXT_COLOR = (230, 230, 235)
MUTED_TEXT = (170, 170, 180)
BUTTON_COLOR = (70, 110, 190)
BUTTON_HOVER = (90, 130, 220)
BUTTON_TEXT = (245, 245, 250)
DOT_COLOR = (255, 60, 60)

# Dot sizing in image-space equivalent (adjusted visually through zoom)
BASE_DOT_RADIUS = 4
DOT_REMOVE_THRESHOLD = 10  # screen pixels

MIN_ZOOM = 0.1
MAX_ZOOM = 8.0
ZOOM_STEP = 1.1


@dataclass
class Button:
    rect: pygame.Rect
    label: str

    def draw(self, surf: pygame.Surface, font: pygame.font.Font, hovered: bool = False):
        color = BUTTON_HOVER if hovered else BUTTON_COLOR
        pygame.draw.rect(surf, color, self.rect, border_radius=8)
        txt = font.render(self.label, True, BUTTON_TEXT)
        txt_rect = txt.get_rect(center=self.rect.center)
        surf.blit(txt, txt_rect)

    def contains(self, pos):
        return self.rect.collidepoint(pos)


def _make_tk_root():
    if tk is None:
        return None
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    return root


def open_image_dialog():
    """Open native file dialog and return selected image path or None."""
    if filedialog is None:
        return None

    root = _make_tk_root()
    filetypes = [
        ("Image files", "*.png *.jpg *.jpeg *.bmp *.gif *.webp"),
        ("All files", "*.*"),
    ]
    path = filedialog.askopenfilename(title="Select an image", filetypes=filetypes)
    if root is not None:
        root.destroy()
    return path if path else None


def save_json_dialog(default_name="annotations.json"):
    if filedialog is None:
        return None

    root = _make_tk_root()
    path = filedialog.asksaveasfilename(
        title="Save annotations",
        defaultextension=".json",
        initialfile=default_name,
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
    )
    if root is not None:
        root.destroy()
    return path if path else None


def load_json_dialog():
    if filedialog is None:
        return None

    root = _make_tk_root()
    path = filedialog.askopenfilename(
        title="Load annotations",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
    )
    if root is not None:
        root.destroy()
    return path if path else None


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def main():
    pygame.init()
    pygame.display.set_caption("Kazu - Image Dot Annotator")

    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    clock = pygame.time.Clock()

    # Fonts
    font = pygame.font.SysFont("arial", 24)
    small_font = pygame.font.SysFont("arial", 18)

    # Right menu buttons
    import_btn = Button(
        rect=pygame.Rect(VIEWPORT_WIDTH + 40, 60, MENU_WIDTH - 80, 48),
        label="Import Image",
    )
    save_btn = Button(
        rect=pygame.Rect(VIEWPORT_WIDTH + 40, 118, MENU_WIDTH - 80, 48),
        label="Save Dots",
    )
    load_btn = Button(
        rect=pygame.Rect(VIEWPORT_WIDTH + 40, 176, MENU_WIDTH - 80, 48),
        label="Load Dots",
    )

    # Image state
    image = None
    image_rect = None
    image_path = None

    # Transform state
    offset_x = 0.0
    offset_y = 0.0
    zoom = 1.0

    # Dots stored in image coordinates (x, y)
    dots = []

    # History for undo/redo
    # action tuple formats:
    # ("add", (x, y))  -> undo removes that exact dot instance
    # ("remove", (x, y), idx) -> undo inserts at idx
    undo_stack = []
    redo_stack = []

    # Panning state
    panning = False
    pan_last_mouse = (0, 0)

    status_message = "Ready"

    def image_to_screen(ix, iy):
        return ix * zoom + offset_x, iy * zoom + offset_y

    def screen_to_image(sx, sy):
        return (sx - offset_x) / zoom, (sy - offset_y) / zoom

    def reset_history():
        undo_stack.clear()
        redo_stack.clear()

    def add_dot(ix, iy):
        dots.append((ix, iy))
        undo_stack.append(("add", (ix, iy)))
        redo_stack.clear()

    def remove_dot_at_index(idx):
        pt = dots.pop(idx)
        undo_stack.append(("remove", pt, idx))
        redo_stack.clear()

    def undo():
        nonlocal status_message
        if not undo_stack:
            status_message = "Nothing to undo"
            return

        action = undo_stack.pop()
        kind = action[0]

        if kind == "add":
            pt = action[1]
            # Remove the last matching point (closest to stack semantics)
            for i in range(len(dots) - 1, -1, -1):
                if dots[i] == pt:
                    dots.pop(i)
                    break
            redo_stack.append(action)
            status_message = "Undo: add dot"

        elif kind == "remove":
            pt, idx = action[1], action[2]
            idx = clamp(idx, 0, len(dots))
            dots.insert(idx, pt)
            redo_stack.append(action)
            status_message = "Undo: remove dot"

    def redo():
        nonlocal status_message
        if not redo_stack:
            status_message = "Nothing to redo"
            return

        action = redo_stack.pop()
        kind = action[0]

        if kind == "add":
            pt = action[1]
            dots.append(pt)
            undo_stack.append(action)
            status_message = "Redo: add dot"

        elif kind == "remove":
            pt, _old_idx = action[1], action[2]
            # Remove one matching point
            removed = False
            for i in range(len(dots) - 1, -1, -1):
                if dots[i] == pt:
                    dots.pop(i)
                    removed = True
                    break
            if removed:
                undo_stack.append(action)
                status_message = "Redo: remove dot"

    def save_annotations():
        nonlocal status_message
        if image is None:
            status_message = "Import an image first"
            return

        default_name = "annotations.json"
        if image_path:
            stem = os.path.splitext(os.path.basename(image_path))[0]
            default_name = f"{stem}_annotations.json"

        out_path = save_json_dialog(default_name=default_name)
        if not out_path:
            status_message = "Save canceled"
            return

        payload = {
            "image_path": image_path,
            "image_size": [image_rect.width, image_rect.height] if image_rect else None,
            "dots": [{"x": float(x), "y": float(y)} for x, y in dots],
        }

        try:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            status_message = f"Saved {len(dots)} dots"
        except OSError:
            status_message = "Failed to save JSON"

    def load_annotations():
        nonlocal status_message
        path = load_json_dialog()
        if not path:
            status_message = "Load canceled"
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except (OSError, json.JSONDecodeError):
            status_message = "Invalid JSON file"
            return

        raw_dots = payload.get("dots", [])
        loaded = []
        for item in raw_dots:
            if isinstance(item, dict) and "x" in item and "y" in item:
                try:
                    loaded.append((float(item["x"]), float(item["y"])))
                except (TypeError, ValueError):
                    pass

        dots.clear()
        dots.extend(loaded)
        reset_history()
        status_message = f"Loaded {len(dots)} dots"

    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()

        hovered_import = import_btn.contains(mouse_pos)
        hovered_save = save_btn.contains(mouse_pos)
        hovered_load = load_btn.contains(mouse_pos)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                mods = pygame.key.get_mods()
                ctrl = bool(mods & pygame.KMOD_CTRL)
                shift = bool(mods & pygame.KMOD_SHIFT)

                if ctrl and event.key == pygame.K_z and not shift:
                    undo()
                elif ctrl and (event.key == pygame.K_y or (event.key == pygame.K_z and shift)):
                    redo()

            elif event.type == pygame.MOUSEWHEEL:
                mx, my = pygame.mouse.get_pos()
                if mx < VIEWPORT_WIDTH:
                    # Zoom around mouse cursor
                    old_zoom = zoom
                    if event.y > 0:
                        zoom = clamp(zoom * ZOOM_STEP, MIN_ZOOM, MAX_ZOOM)
                    elif event.y < 0:
                        zoom = clamp(zoom / ZOOM_STEP, MIN_ZOOM, MAX_ZOOM)

                    if zoom != old_zoom:
                        ix, iy = screen_to_image(mx, my)
                        offset_x = mx - ix * zoom
                        offset_y = my - iy * zoom
                        status_message = f"Zoom: {zoom:.2f}x"

            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos

                # Menu panel click
                if mx >= VIEWPORT_WIDTH:
                    if event.button == 1:
                        if import_btn.contains((mx, my)):
                            selected = open_image_dialog()
                            if selected and os.path.exists(selected):
                                try:
                                    loaded = pygame.image.load(selected).convert_alpha()
                                    image = loaded
                                    image_rect = image.get_rect()
                                    image_path = selected

                                    # Reset transform and dots for newly imported image
                                    dots.clear()
                                    offset_x = 0.0
                                    offset_y = 0.0
                                    zoom = 1.0
                                    reset_history()
                                    status_message = f"Loaded image: {os.path.basename(selected)}"
                                except pygame.error:
                                    status_message = "Failed to load image"

                        elif save_btn.contains((mx, my)):
                            save_annotations()

                        elif load_btn.contains((mx, my)):
                            load_annotations()
                    continue

                # Viewport interactions
                in_viewport = mx < VIEWPORT_WIDTH and 0 <= my < VIEWPORT_HEIGHT
                if not in_viewport:
                    continue

                # Start pan with middle mouse OR Shift + left click
                if event.button == 2 or (event.button == 1 and (pygame.key.get_mods() & pygame.KMOD_SHIFT)):
                    panning = True
                    pan_last_mouse = (mx, my)
                    continue

                if image is None:
                    continue

                # Left click -> add dot in image space if click hits image bounds
                if event.button == 1:
                    img_x, img_y = screen_to_image(mx, my)
                    if 0 <= img_x < image_rect.width and 0 <= img_y < image_rect.height:
                        add_dot(img_x, img_y)
                        status_message = f"Dot added ({len(dots)})"

                # Right click -> remove nearest dot within threshold
                elif event.button == 3:
                    if dots:
                        nearest_idx = None
                        nearest_dist2 = None

                        for i, (dx, dy) in enumerate(dots):
                            sx, sy = image_to_screen(dx, dy)
                            dist2 = (sx - mx) ** 2 + (sy - my) ** 2

                            if nearest_dist2 is None or dist2 < nearest_dist2:
                                nearest_dist2 = dist2
                                nearest_idx = i

                        if (
                            nearest_idx is not None
                            and nearest_dist2 is not None
                            and nearest_dist2 <= DOT_REMOVE_THRESHOLD ** 2
                        ):
                            remove_dot_at_index(nearest_idx)
                            status_message = f"Dot removed ({len(dots)})"

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button in (1, 2):
                    panning = False

            elif event.type == pygame.MOUSEMOTION:
                if panning:
                    mx, my = event.pos
                    dx = mx - pan_last_mouse[0]
                    dy = my - pan_last_mouse[1]
                    pan_last_mouse = (mx, my)

                    offset_x += dx
                    offset_y += dy

        # ---------- Draw ----------
        screen.fill(BG_COLOR)

        # Viewport
        viewport_rect = pygame.Rect(0, 0, VIEWPORT_WIDTH, VIEWPORT_HEIGHT)
        pygame.draw.rect(screen, VIEWPORT_BG, viewport_rect)

        # Image + dots (clipped to viewport)
        prev_clip = screen.get_clip()
        screen.set_clip(viewport_rect)

        if image is not None:
            # Scale image for zoom rendering
            scaled_w = max(1, int(image_rect.width * zoom))
            scaled_h = max(1, int(image_rect.height * zoom))
            scaled_image = pygame.transform.smoothscale(image, (scaled_w, scaled_h))
            screen.blit(scaled_image, (offset_x, offset_y))

            dot_radius = max(2, int(BASE_DOT_RADIUS * max(0.8, min(2.0, zoom))))
            for dx, dy in dots:
                sx, sy = image_to_screen(dx, dy)
                pygame.draw.circle(screen, DOT_COLOR, (int(sx), int(sy)), dot_radius)

        else:
            empty_text = small_font.render("Import an image to begin.", True, MUTED_TEXT)
            screen.blit(empty_text, (24, 24))

        screen.set_clip(prev_clip)

        # Divider
        pygame.draw.line(screen, (90, 90, 100), (VIEWPORT_WIDTH, 0), (VIEWPORT_WIDTH, WINDOW_HEIGHT), 2)

        # Menu panel
        menu_rect = pygame.Rect(VIEWPORT_WIDTH, 0, MENU_WIDTH, WINDOW_HEIGHT)
        pygame.draw.rect(screen, MENU_BG, menu_rect)

        title = font.render("Menu", True, TEXT_COLOR)
        screen.blit(title, (VIEWPORT_WIDTH + 40, 20))

        import_btn.draw(screen, small_font, hovered_import)
        save_btn.draw(screen, small_font, hovered_save)
        load_btn.draw(screen, small_font, hovered_load)

        dots_text = font.render(f"Dots: {len(dots)}", True, TEXT_COLOR)
        screen.blit(dots_text, (VIEWPORT_WIDTH + 40, 248))

        zoom_text = small_font.render(f"Zoom: {zoom:.2f}x", True, MUTED_TEXT)
        screen.blit(zoom_text, (VIEWPORT_WIDTH + 40, 282))

        if image_path:
            name = os.path.basename(image_path)
            img_label = small_font.render("Loaded image:", True, MUTED_TEXT)
            img_name = small_font.render(name, True, TEXT_COLOR)
            screen.blit(img_label, (VIEWPORT_WIDTH + 40, 320))
            screen.blit(img_name, (VIEWPORT_WIDTH + 40, 344))

        status_label = small_font.render("Status:", True, MUTED_TEXT)
        status_text = small_font.render(status_message, True, TEXT_COLOR)
        screen.blit(status_label, (VIEWPORT_WIDTH + 40, WINDOW_HEIGHT - 172))
        screen.blit(status_text, (VIEWPORT_WIDTH + 40, WINDOW_HEIGHT - 148))

        help_1 = small_font.render("Pan: middle drag", True, MUTED_TEXT)
        help_2 = small_font.render("or Shift + left drag", True, MUTED_TEXT)
        help_3 = small_font.render("Zoom: mouse wheel", True, MUTED_TEXT)
        help_4 = small_font.render("Undo/Redo: Ctrl+Z / Ctrl+Y", True, MUTED_TEXT)

        screen.blit(help_1, (VIEWPORT_WIDTH + 40, WINDOW_HEIGHT - 112))
        screen.blit(help_2, (VIEWPORT_WIDTH + 40, WINDOW_HEIGHT - 90))
        screen.blit(help_3, (VIEWPORT_WIDTH + 40, WINDOW_HEIGHT - 66))
        screen.blit(help_4, (VIEWPORT_WIDTH + 40, WINDOW_HEIGHT - 44))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
