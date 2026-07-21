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
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 750
MENU_WIDTH = 300
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
DOT_RADIUS = 4
DOT_REMOVE_THRESHOLD = 8  # in screen pixels


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


def open_file_dialog():
    """Open native file dialog and return selected image path or None."""
    if tk is None or filedialog is None:
        return None

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    filetypes = [
        ("Image files", "*.png *.jpg *.jpeg *.bmp *.gif *.webp"),
        ("All files", "*.*"),
    ]
    path = filedialog.askopenfilename(title="Select an image", filetypes=filetypes)

    root.destroy()
    return path if path else None


def main():
    pygame.init()
    pygame.display.set_caption("Kazu - Image Dot Annotator")

    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    clock = pygame.time.Clock()

    # Fonts
    font = pygame.font.SysFont("arial", 24)
    small_font = pygame.font.SysFont("arial", 18)

    # Right menu button
    import_btn = Button(
        rect=pygame.Rect(VIEWPORT_WIDTH + 40, 60, MENU_WIDTH - 80, 52),
        label="Import Image",
    )

    # Image state
    image = None
    image_rect = None
    image_path = None

    # Pan offset (where image top-left is drawn in viewport coordinates)
    offset_x = 0
    offset_y = 0

    # Dots stored in image coordinates (float/int image-space x, y)
    dots = []

    # Panning state
    panning = False
    pan_last_mouse = (0, 0)

    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        hovered_import = import_btn.contains(mouse_pos)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos

                # Menu panel click
                if mx >= VIEWPORT_WIDTH:
                    if event.button == 1 and import_btn.contains((mx, my)):
                        selected = open_file_dialog()
                        if selected and os.path.exists(selected):
                            try:
                                loaded = pygame.image.load(selected).convert_alpha()
                                image = loaded
                                image_rect = image.get_rect()
                                image_path = selected

                                # Reset pan and dots for newly imported image
                                dots.clear()
                                offset_x = 0
                                offset_y = 0
                            except pygame.error:
                                # Ignore invalid image
                                pass
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
                    img_x = mx - offset_x
                    img_y = my - offset_y
                    if 0 <= img_x < image_rect.width and 0 <= img_y < image_rect.height:
                        dots.append((img_x, img_y))

                # Right click -> remove nearest dot within threshold
                elif event.button == 3:
                    if dots:
                        nearest_idx = None
                        nearest_dist2 = None

                        for i, (dx, dy) in enumerate(dots):
                            sx = dx + offset_x
                            sy = dy + offset_y
                            dist2 = (sx - mx) ** 2 + (sy - my) ** 2

                            if nearest_dist2 is None or dist2 < nearest_dist2:
                                nearest_dist2 = dist2
                                nearest_idx = i

                        if (
                            nearest_idx is not None
                            and nearest_dist2 is not None
                            and nearest_dist2 <= DOT_REMOVE_THRESHOLD ** 2
                        ):
                            dots.pop(nearest_idx)

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
            screen.blit(image, (offset_x, offset_y))

            for dx, dy in dots:
                sx = int(dx + offset_x)
                sy = int(dy + offset_y)
                pygame.draw.circle(screen, DOT_COLOR, (sx, sy), DOT_RADIUS)

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

        dots_text = font.render(f"Dots: {len(dots)}", True, TEXT_COLOR)
        screen.blit(dots_text, (VIEWPORT_WIDTH + 40, 140))

        if image_path:
            name = os.path.basename(image_path)
            img_label = small_font.render("Loaded image:", True, MUTED_TEXT)
            img_name = small_font.render(name, True, TEXT_COLOR)
            screen.blit(img_label, (VIEWPORT_WIDTH + 40, 190))
            screen.blit(img_name, (VIEWPORT_WIDTH + 40, 214))

        help_1 = small_font.render("Pan: middle drag", True, MUTED_TEXT)
        help_2 = small_font.render("or Shift + left drag", True, MUTED_TEXT)
        help_3 = small_font.render("Left click: add dot", True, MUTED_TEXT)
        help_4 = small_font.render("Right click: remove dot", True, MUTED_TEXT)

        screen.blit(help_1, (VIEWPORT_WIDTH + 40, WINDOW_HEIGHT - 130))
        screen.blit(help_2, (VIEWPORT_WIDTH + 40, WINDOW_HEIGHT - 106))
        screen.blit(help_3, (VIEWPORT_WIDTH + 40, WINDOW_HEIGHT - 76))
        screen.blit(help_4, (VIEWPORT_WIDTH + 40, WINDOW_HEIGHT - 52))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
