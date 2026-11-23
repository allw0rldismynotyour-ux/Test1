import os
os.environ['SDL_VIDEO_CENTERED'] = '1'

import pygame
import math
import sys
import traceback
import datetime

def log_crash(exc_type, exc_value, exc_traceback):
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    paths = ["/sdcard/Download/crash_log.txt", "crash_log.txt"]
    for path in paths:
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(f"\n--- CRASH: {datetime.datetime.now()} ---\n")
                f.write(error_msg)
                f.write("-" * 50 + "\n")
            break
        except: pass
    sys.exit(1)

sys.excepthook = log_crash

from map import GameMap, MapEditor
from soldier import Soldier
from btr80 import BTR80

pygame.init()

IS_ANDROID = (sys.platform == 'android') or ('ANDROID_ARGUMENT' in os.environ)
try:
    if IS_ANDROID:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    else:
        screen = pygame.display.set_mode((1280, 720))
except Exception:
    screen = pygame.display.set_mode((1280, 720))

SW, SH = screen.get_size()
IS_PORTRAIT = SH > SW
VW, VH = 960, 540
canvas = pygame.Surface((VW, VH))
FPS = 60
WORLD_W, WORLD_H = 2400, 1600

pygame.display.set_caption("Broken Arrow 2D")
clock = pygame.time.Clock()

class Camera:
    def __init__(self):
        self.x = WORLD_W / 2
        self.y = WORLD_H / 2
        self.zoom = 1.0
        self.min_zoom = 0.4
        self.max_zoom = 2.5
    def world_to_screen(self, wx, wy):
        return ((wx - self.x) * self.zoom + VW / 2, (wy - self.y) * self.zoom + VH / 2)
    def screen_to_world(self, sx, sy):
        return ((sx - VW / 2) / self.zoom + self.x, (sy - VH / 2) / self.zoom + self.y)
    def follow(self, tx, ty, dt):
        k = 1 - math.exp(-8 * dt)
        self.x += (tx - self.x) * k
        self.y += (ty - self.y) * k
    def zoom_by(self, factor):
        self.zoom = max(self.min_zoom, min(self.max_zoom, self.zoom * factor))

class FloatingJoystick:
    def __init__(self):
        self.active = False
        self.origin = (0, 0)
        self.vector = (0.0, 0.0)
        self.radius = 70
        self.base = pygame.Surface((self.radius*2, self.radius*2), pygame.SRCALPHA)
        pygame.draw.circle(self.base, (255,255,255, 40), (self.radius, self.radius), self.radius)
        pygame.draw.circle(self.base, (255,255,255, 120), (self.radius, self.radius), self.radius, 2)
    def start(self, pos):
        self.active = True
        self.origin = pos
        self.vector = (0.0, 0.0)
    def move(self, pos):
        if not self.active: return
        dx = pos[0] - self.origin[0]
        dy = pos[1] - self.origin[1]
        dist = math.hypot(dx, dy)
        if dist > self.radius:
            dx, dy = dx/dist * self.radius, dy/dist * self.radius
            dist = self.radius
        self.vector = (dx / self.radius, dy / self.radius) if dist >= 8 else (0, 0)
    def release(self):
        self.active = False
        self.vector = (0.0, 0.0)
    def draw(self, surf):
        if not self.active: return
        surf.blit(self.base, (self.origin[0] - self.radius, self.origin[1] - self.radius))
        knob_x = self.origin[0] + self.vector[0] * self.radius
        knob_y = self.origin[1] + self.vector[1] * self.radius
        pygame.draw.circle(surf, (220,220,230), (int(knob_x), int(knob_y)), 25)

def main():
    game_map = GameMap(WORLD_W, WORLD_H)
    player = Soldier(WORLD_W//2, WORLD_H//2)
    btr = BTR80(player.x + 150, player.y)
    cam = Camera()
    cam.x, cam.y = player.x, player.y
    joy = FloatingJoystick()
    editor = MapEditor(game_map)

    running = True
    fingers = {}
    pinch_dist = 0.0
    pinch_center = (0, 0)
    btn_cooldown = 0.0

    waiting_to_draw = False
    touch_timer = 0.0
    initial_touch_pos = (0, 0)

    font = pygame.font.SysFont("Arial", 16, bold=True)

    def get_vpos(pos):
        sx, sy = pos
        if IS_PORTRAIT: return (sy / SH) * VW, (1.0 - sx / SW) * VH
        return (sx / SW) * VW, (sy / SH) * VH

    while running:
        dt = min(clock.tick(FPS) / 1000.0, 0.05)
        btn_cooldown -= dt

        if waiting_to_draw:
            touch_timer += dt
            if touch_timer > 0.15:
                waiting_to_draw = False
                if editor.active:
                    editor.start_draw(initial_touch_pos[0], initial_touch_pos[1], cam)
                else:
                    joy.start(initial_touch_pos)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                continue

            if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION, pygame.MOUSEBUTTONUP):
                vx, vy = get_vpos(event.pos)
            elif event.type in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
                vx, vy = get_vpos((event.x * SW, event.y * SH))
            else:
                vx, vy = -1, -1

            # Кнопка РЕДАКТОР / ИГРА
            if event.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
                if btn_cooldown <= 0 and pygame.Rect(10, 10, 120, 40).collidepoint(vx, vy):
                    editor.active = not editor.active
                    btn_cooldown = 0.4
                    joy.release()
                    editor.end_draw()
                    waiting_to_draw = False
                    continue

            # --- МУЛЬТИТАЧ ---
            if event.type == pygame.FINGERDOWN:
                fingers[event.finger_id] = (vx, vy)
                if len(fingers) == 1:
                    if editor.active and editor.handle_ui(vx, vy):
                        waiting_to_draw = False
                    else:
                        waiting_to_draw = True
                        touch_timer = 0.0
                        initial_touch_pos = (vx, vy)
                elif len(fingers) == 2:
                    waiting_to_draw = False
                    editor.rollback()
                    joy.release()

                    pts = list(fingers.values())
                    pinch_dist = math.hypot(pts[0][0]-pts[1][0], pts[0][1]-pts[1][1])
                    pinch_center = ((pts[0][0]+pts[1][0])/2, (pts[0][1]+pts[1][1])/2)

            elif event.type == pygame.FINGERMOTION:
                if event.finger_id in fingers:
                    fingers[event.finger_id] = (vx, vy)

                    if len(fingers) == 1:
                        if waiting_to_draw:
                            waiting_to_draw = False
                            if editor.active:
                                editor.start_draw(initial_touch_pos[0], initial_touch_pos[1], cam)
                                editor.update_draw(vx, vy, cam)
                            else:
                                joy.start(initial_touch_pos)
                                joy.move((vx, vy))
                        else:
                            if editor.active:
                                editor.update_draw(vx, vy, cam)
                            else:
                                joy.move((vx, vy))
                    elif len(fingers) == 2:
                        pts = list(fingers.values())
                        new_dist = math.hypot(pts[0][0]-pts[1][0], pts[0][1]-pts[1][1])
                        new_center = ((pts[0][0]+pts[1][0])/2, (pts[0][1]+pts[1][1])/2)

                        if pinch_dist > 0 and new_dist > 0:
                            cam.zoom_by(new_dist / pinch_dist)
                            dx = new_center[0] - pinch_center[0]
                            dy = new_center[1] - pinch_center[1]
                            cam.x -= dx / cam.zoom
                            cam.y -= dy / cam.zoom

                        pinch_dist = new_dist
                        pinch_center = new_center

            elif event.type == pygame.FINGERUP:
                if event.finger_id in fingers:
                    del fingers[event.finger_id]
                if len(fingers) < 2:
                    pinch_dist = 0.0
                if len(fingers) == 0:
                    waiting_to_draw = False
                    editor.end_draw()

            # Для ПК
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if editor.active:
                    if not editor.handle_ui(vx, vy):
                        editor.start_draw(vx, vy, cam)
                else:
                    joy.start((vx, vy))
            elif event.type == pygame.MOUSEMOTION:
                if event.buttons[0]:
                    if editor.active:
                        editor.update_draw(vx, vy, cam)
                    elif joy.active:
                        joy.move((vx, vy))
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if editor.active:
                    editor.end_draw()
                else:
                    joy.release()

        if not editor.active:
            keys = pygame.key.get_pressed()
            kx = float(bool(keys[pygame.K_d] or keys[pygame.K_RIGHT])) - float(bool(keys[pygame.K_a] or keys[pygame.K_LEFT]))
            ky = float(bool(keys[pygame.K_s] or keys[pygame.K_DOWN])) - float(bool(keys[pygame.K_w] or keys[pygame.K_UP]))
            mx = joy.vector[0] + kx
            my = joy.vector[1] + ky
            player.update(dt, (mx, my), game_map.colliders)
            cam.follow(player.x, player.y, dt)
        else:
            cam.x = max(0, min(WORLD_W, cam.x))
            cam.y = max(0, min(WORLD_H, cam.y))

        game_map.draw(canvas, cam)

        if not editor.active:
            btr.draw(canvas, cam)
            player.draw(canvas, cam)
            joy.draw(canvas)

        btn_rect = pygame.Rect(10, 10, 120, 40)
        btn_col = (200, 50, 50) if editor.active else (50, 150, 50)
        pygame.draw.rect(canvas, btn_col, btn_rect, border_radius=5)
        btn_text = font.render("ИГРА" if editor.active else "РЕДАКТОР", True, (255, 255, 255))
        canvas.blit(btn_text, btn_text.get_rect(center=btn_rect.center))

        editor.draw_ui(canvas, font)

        screen.fill((0,0,0))
        if IS_PORTRAIT:
            scaled = pygame.transform.scale(canvas, (SH, SW))
            rotated = pygame.transform.rotate(scaled, -90)
            screen.blit(rotated, (0,0))
        else:
            scaled = pygame.transform.scale(canvas, (SW, SH))
            screen.blit(scaled, (0,0))

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
