import math
import sys

import pygame

from btr80 import BTR80


SCREEN_W, SCREEN_H = 960, 540
WORLD_W, WORLD_H = 1600, 1000
FPS = 60


class Camera:
    def __init__(self):
        self.x = WORLD_W / 2
        self.y = WORLD_H / 2
        self.zoom = 1.0

    def follow(self, target):
        self.x = target.x
        self.y = target.y

    def world_to_screen(self, x, y):
        sx = (x - self.x) * self.zoom + SCREEN_W / 2
        sy = (y - self.y) * self.zoom + SCREEN_H / 2
        return round(sx), round(sy)


def draw_world(screen, camera, obstacles):
    screen.fill((91, 111, 77))

    # Grid helps to see movement and zoom.
    step = 50
    left = camera.x - SCREEN_W / (2 * camera.zoom)
    right = camera.x + SCREEN_W / (2 * camera.zoom)
    top = camera.y - SCREEN_H / (2 * camera.zoom)
    bottom = camera.y + SCREEN_H / (2 * camera.zoom)

    start_x = max(0, int(left // step) * step)
    end_x = min(WORLD_W, int(right // step + 1) * step)
    start_y = max(0, int(top // step) * step)
    end_y = min(WORLD_H, int(bottom // step + 1) * step)

    for x in range(start_x, end_x + 1, step):
        a = camera.world_to_screen(x, 0)
        b = camera.world_to_screen(x, WORLD_H)
        pygame.draw.line(screen, (101, 121, 86), a, b, 1)
    for y in range(start_y, end_y + 1, step):
        a = camera.world_to_screen(0, y)
        b = camera.world_to_screen(WORLD_W, y)
        pygame.draw.line(screen, (101, 121, 86), a, b, 1)

    for rect in obstacles:
        p = camera.world_to_screen(rect.x, rect.y)
        scaled = pygame.Rect(
            p[0], p[1],
            max(1, round(rect.width * camera.zoom)),
            max(1, round(rect.height * camera.zoom)),
        )
        pygame.draw.rect(screen, (76, 68, 58), scaled)
        pygame.draw.rect(screen, (42, 39, 34), scaled, max(1, round(3 * camera.zoom)))

    border_a = camera.world_to_screen(0, 0)
    border_b = camera.world_to_screen(WORLD_W, WORLD_H)
    border = pygame.Rect(
        border_a[0], border_a[1],
        border_b[0] - border_a[0],
        border_b[1] - border_a[1],
    )
    pygame.draw.rect(screen, (35, 45, 32), border, max(1, round(5 * camera.zoom)))


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("BTR-80 test — Broken Arrow 2D")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 24)

    btr = BTR80(WORLD_W / 2, WORLD_H / 2)
    camera = Camera()

    obstacles = [
        pygame.Rect(650, 350, 180, 45),
        pygame.Rect(900, 560, 55, 210),
        pygame.Rect(430, 650, 240, 55),
        pygame.Rect(1120, 260, 70, 180),
    ]

    running = True
    while running:
        dt = min(clock.tick(FPS) / 1000.0, 0.05)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                    camera.zoom = min(2.5, camera.zoom * 1.15)
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    camera.zoom = max(0.4, camera.zoom / 1.15)

        keys = pygame.key.get_pressed()
        move_x = float(keys[pygame.K_d] or keys[pygame.K_RIGHT]) - float(
            keys[pygame.K_a] or keys[pygame.K_LEFT]
        )
        move_y = float(keys[pygame.K_s] or keys[pygame.K_DOWN]) - float(
            keys[pygame.K_w] or keys[pygame.K_UP]
        )

        btr.update(dt, (move_x, move_y), obstacles)

        # Keep the vehicle inside the world.
        btr.x = max(55, min(WORLD_W - 55, btr.x))
        btr.y = max(55, min(WORLD_H - 55, btr.y))
        btr.rect.center = (round(btr.x), round(btr.y))

        camera.follow(btr)
        draw_world(screen, camera, obstacles)
        btr.draw(screen, camera)

        help_lines = [
            "WASD / arrows: move   |   +/-: zoom   |   ESC: quit",
            f"Position: {int(btr.x)}, {int(btr.y)}   Speed: {btr.speed:.0f}   Zoom: {camera.zoom:.2f}x",
            "Drive into the dark blocks to test collision.",
        ]
        for i, line in enumerate(help_lines):
            image = font.render(line, True, (245, 245, 230))
            screen.blit(image, (12, 10 + i * 23))

        pygame.display.flip()

    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
