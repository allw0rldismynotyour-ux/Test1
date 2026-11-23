import pygame
import math

class Soldier:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.speed = 200.0
        self.radius = 14

        # Хитбокс для проверки стен (квадрат вокруг центра)
        self.rect = pygame.Rect(0, 0, self.radius * 2, self.radius * 2)
        self.rect.center = (self.x, self.y)

        self.angle = 0.0

    def update(self, dt, move_vec, colliders):
        mx, my = move_vec
        mag = math.hypot(mx, my)

        if mag > 0.1:
            if mag > 1.0:
                mx, my = mx/mag, my/mag
            self.angle = math.atan2(my, mx)

            # --- Движение по оси X ---
            new_x = self.x + mx * self.speed * dt
            test_rect = self.rect.copy()
            test_rect.centerx = new_x

            if not self._check_collision(test_rect, colliders):
                self.x = new_x
                self.rect.centerx = self.x

            # --- Движение по оси Y ---
            new_y = self.y + my * self.speed * dt
            test_rect = self.rect.copy()
            test_rect.centery = new_y

            if not self._check_collision(test_rect, colliders):
                self.y = new_y
                self.rect.centery = self.y

    def _check_collision(self, rect, colliders):
        for col in colliders:
            if rect.colliderect(col):
                return True
        return False

    def draw(self, surface, camera):
        sx, sy = camera.world_to_screen(self.x, self.y)
        z = camera.zoom
        r = self.radius * z

        # Векторы направления и перпендикуляра
        dx, dy = math.cos(self.angle), math.sin(self.angle)
        px, py = -dy, dx

        # 1. Тень (смещена вниз для объема)
        pygame.draw.ellipse(surface, (15, 15, 20), (sx - r*1.2, sy + r*0.4, r*2.4, r*1.2))

        # 2. Рюкзак (сзади)
        back_x = sx - dx * r * 0.7
        back_y = sy - dy * r * 0.7
        pygame.draw.circle(surface, (50, 65, 50), (int(back_x), int(back_y)), int(r * 0.7))

        # 3. Руки
        arm_col = (80, 100, 80)
        # Левая рука (поддерживает автомат)
        la_x = sx + dx*r*0.8 + px*r*0.4
        la_y = sy + dy*r*0.8 + py*r*0.4
        pygame.draw.circle(surface, arm_col, (int(la_x), int(la_y)), int(r*0.35))
        # Правая рука (на спусковом крючке)
        ra_x = sx + dx*r*0.5 - px*r*0.5
        ra_y = sy + dy*r*0.5 - py*r*0.5
        pygame.draw.circle(surface, arm_col, (int(ra_x), int(ra_y)), int(r*0.35))

        # 4. Оружие (Автомат, ствол смотрит вперед)
        g_start = (sx + dx*r*0.5, sy + dy*r*0.5)
        g_end = (sx + dx*r*2.2, sy + dy*r*2.2)
        pygame.draw.line(surface, (20, 20, 20), g_start, g_end, max(2, int(6*z)))
        # Приклад автомата
        pygame.draw.line(surface, (40, 30, 20), (sx + dx*r*0.2, sy + dy*r*0.2), g_start, max(2, int(8*z)))

        # 5. Тело (Бронежилет)
        pygame.draw.circle(surface, (60, 80, 60), (int(sx), int(sy)), int(r))
        # Разгрузка (полоски)
        pygame.draw.line(surface, (40, 60, 40), (sx - px*r*0.8, sy - py*r*0.8), (sx + px*r*0.8, sy + py*r*0.8), max(1, int(3*z)))

        # 6. Каска
        pygame.draw.circle(surface, (45, 60, 45), (int(sx), int(sy)), int(r * 0.65))
        # Блик на каске
        pygame.draw.circle(surface, (90, 120, 90), (int(sx + dx*r*0.2), int(sy + dy*r*0.2)), int(r * 0.25))
