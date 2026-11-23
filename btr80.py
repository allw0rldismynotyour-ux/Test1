import math
import pygame


class BTR80:
    """Упрощённая модель БТР-80 для top-down игры на Pygame.

    Интерфейс совместим с Soldier:
        vehicle.update(dt, move_vec, colliders)
        vehicle.draw(surface, camera)

    move_vec — направление движения (x, y), обычно от джойстика.
    colliders — список pygame.Rect препятствий.
    """

    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.speed = 130.0
        self.max_speed = 130.0
        self.radius = 34
        self.width = 62
        self.length = 100
        self.angle = 0.0

        # Прямоугольник столкновения — консервативный AABB корпуса.
        self.rect = pygame.Rect(0, 0, self.width, self.length)
        self.rect.center = (round(self.x), round(self.y))

    @staticmethod
    def _collides(rect, colliders):
        return any(rect.colliderect(collider) for collider in colliders)

    def update(self, dt, move_vec, colliders):
        """Движение с проверкой столкновений отдельно по X и Y."""
        mx, my = move_vec
        magnitude = math.hypot(mx, my)

        if magnitude <= 0.1:
            return

        if magnitude > 1.0:
            mx /= magnitude
            my /= magnitude

        self.angle = math.atan2(my, mx)
        distance_x = mx * self.speed * dt
        distance_y = my * self.speed * dt

        # Проверяем оси независимо, чтобы можно было скользить вдоль стен.
        if distance_x:
            test_rect = self.rect.copy()
            test_rect.centerx = round(self.x + distance_x)
            if not self._collides(test_rect, colliders):
                self.x += distance_x
                self.rect.centerx = round(self.x)

        if distance_y:
            test_rect = self.rect.copy()
            test_rect.centery = round(self.y + distance_y)
            if not self._collides(test_rect, colliders):
                self.y += distance_y
                self.rect.centery = round(self.y)

    def _world_point(self, forward, side, center_x, center_y, zoom):
        """Преобразует локальную точку корпуса в экранные координаты."""
        ca = math.cos(self.angle)
        sa = math.sin(self.angle)

        # forward направлен вдоль продольной оси машины.
        wx = center_x + (forward * ca - side * sa) * zoom
        wy = center_y + (forward * sa + side * ca) * zoom
        return (round(wx), round(wy))

    def _polygon(self, surface, color, points, center, zoom, width=0):
        screen_points = [
            self._world_point(fwd, side, center[0], center[1], zoom)
            for fwd, side in points
        ]
        pygame.draw.polygon(surface, color, screen_points, width)

    def draw(self, surface, camera):
        sx, sy = camera.world_to_screen(self.x, self.y)
        zoom = camera.zoom

        if zoom <= 0:
            return

        # Не тратим время на отрисовку далеко за пределами экрана.
        if sx < -150 or sx > surface.get_width() + 150:
            return
        if sy < -150 or sy > surface.get_height() + 150:
            return

        center = (sx, sy)

        # Тень.
        shadow = [
            (-43, -25), (-43, 25), (-30, 34), (30, 34),
            (43, 25), (43, -25), (30, -34), (-30, -34)
        ]
        self._polygon(surface, (18, 22, 18), shadow,
                      (sx + 3 * zoom, sy + 4 * zoom), zoom)

        # Восемь колёс по бокам.
        wheel_color = (25, 27, 25)
        wheel_edge = (8, 10, 8)
        for forward in (-31, -10, 11, 32):
            for side in (-32, 32):
                p = self._world_point(forward, side, sx, sy, zoom)
                pygame.draw.circle(surface, wheel_color, p,
                                   max(2, round(8 * zoom)))
                pygame.draw.circle(surface, wheel_edge, p,
                                   max(1, round(8 * zoom)), max(1, round(2 * zoom)))

        # Основной бронекорпус.
        hull = [
            (-49, -20), (-42, -29), (30, -29), (48, -17),
            (50, 0), (48, 17), (30, 29), (-42, 29), (-49, 20)
        ]
        self._polygon(surface, (73, 88, 62), hull, center, zoom)
        self._polygon(surface, (103, 119, 82),
                      [(-39, -18), (-33, -23), (27, -23),
                       (40, -13), (42, 0), (40, 13),
                       (27, 23), (-33, 23), (-39, 18)],
                      center, zoom)
        self._polygon(surface, (43, 55, 40),
                      [(-42, -5), (34, -5), (42, 0), (34, 5), (-42, 5)],
                      center, zoom)

        # Носовая часть и смотровые приборы.
        self._polygon(surface, (57, 70, 51),
                      [(32, -18), (48, -12), (50, 0), (48, 12), (32, 18)],
                      center, zoom)
        for side in (-12, 12):
            p = self._world_point(38, side, sx, sy, zoom)
            pygame.draw.circle(surface, (35, 55, 58), p, max(2, round(4 * zoom)))

        # Башня и погон.
        turret_center = self._world_point(-2, 0, sx, sy, zoom)
        pygame.draw.circle(surface, (48, 59, 43), turret_center,
                           max(4, round(15 * zoom)))
        pygame.draw.circle(surface, (93, 106, 72), turret_center,
                           max(3, round(12 * zoom)))
        pygame.draw.circle(surface, (35, 42, 32), turret_center,
                           max(2, round(5 * zoom)))

        # Пушка направлена по курсу машины.
        gun_start = self._world_point(3, 0, sx, sy, zoom)
        gun_end = self._world_point(31, 0, sx, sy, zoom)
        pygame.draw.line(surface, (31, 35, 29), gun_start, gun_end,
                         max(2, round(6 * zoom)))
        pygame.draw.circle(surface, (25, 28, 24), gun_end,
                           max(1, round(3 * zoom)))

        # Небольшие детали крыши и кормовые люки.
        for side in (-12, 12):
            p = self._world_point(-27, side, sx, sy, zoom)
            pygame.draw.circle(surface, (54, 65, 48), p, max(2, round(5 * zoom)))
        pygame.draw.line(
            surface, (35, 45, 33),
            self._world_point(-40, -17, sx, sy, zoom),
            self._world_point(-40, 17, sx, sy, zoom),
            max(1, round(2 * zoom))
        )
