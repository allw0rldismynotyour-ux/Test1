import pygame
import random
import math
import json
import os
import copy

# Карта всегда лежит рядом с этим файлом, откуда бы ни запускалась игра
MAP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "custom_map.json")

# Символы клеток в компактном формате карты
CHARS = {"wall": "#", "window": "=", "wood": "w", "water": "~",
         "dirt": "d", "asphalt": "a", "tree": "T", "crate": "C"}
TO_TYPE = {v: k for k, v in CHARS.items()}


class GameMap:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.walls = []
        self.props = []
        self.floors = []

        if os.path.exists(MAP_PATH):
            self.load_map()
        else:
            self.generate_default()

    def generate_default(self):
        self.floors.append({"rect": pygame.Rect(300, 200, 400, 300), "type": "wood"})
        t = 20
        self.walls.append({"rect": pygame.Rect(300, 200, 400, t), "type": "wall"})
        self.walls.append({"rect": pygame.Rect(300, 200, t, 300), "type": "wall"})
        self.walls.append({"rect": pygame.Rect(300, 480, 400, t), "type": "wall"})
        self.walls.append({"rect": pygame.Rect(680, 200, t, 100), "type": "wall"})
        self.walls.append({"rect": pygame.Rect(680, 300, t, 100), "type": "window"})
        self.walls.append({"rect": pygame.Rect(680, 400, t, 100), "type": "wall"})
        self.walls.append({"rect": pygame.Rect(480, 200, t, 100), "type": "wall"})
        self.walls.append({"rect": pygame.Rect(480, 340, t, 160), "type": "wall"})
        self.props.append({"rect": pygame.Rect(340, 240, 20, 20), "type": "crate"})
        self.props.append({"rect": pygame.Rect(600, 400, 20, 20), "type": "crate"})
        self.update_colliders()

    def update_colliders(self):
        self.colliders = [w["rect"] for w in self.walls] + \
                         [p["rect"] for p in self.props if p["type"] in ("tree", "crate")]

    @staticmethod
    def _rle_encode(row):
        """Кодирует строку повторами: '####..' -> '4#2.'"""
        out, i = [], 0
        while i < len(row):
            j = i
            while j < len(row) and row[j] == row[i]:
                j += 1
            n = j - i
            out.append(row[i] if n == 1 else f"{n}{row[i]}")
            i = j
        return "".join(out)

    @staticmethod
    def _rle_decode(row):
        """Разворачивает RLE-строку: '4#2.' -> '####..'"""
        out, num = [], ""
        for ch in row:
            if ch.isdigit():
                num += ch
            else:
                out.append(ch * (int(num) if num else 1))
                num = ""
        return "".join(out)

    def save_map(self):
        all_r = [it["rect"] for it in self.walls + self.props + self.floors]
        if not all_r:
            data = {"format": "grid", "cell": 20, "x": 0, "y": 0, "rle": True, "rows": []}
        else:
            min_x = min(r.x for r in all_r)
            min_y = min(r.y for r in all_r)
            max_x = max(r.x + r.w for r in all_r)
            max_y = max(r.y + r.h for r in all_r)
            cols, rows_n = (max_x - min_x) // 20, (max_y - min_y) // 20
            grid = [["."] * cols for _ in range(rows_n)]
            # полы рисуем первыми — стены и объекты их перекрывают
            for layer in (self.floors, self.walls, self.props):
                for it in layer:
                    r = it["rect"]
                    for gx in range(r.x, r.x + r.w, 20):
                        for gy in range(r.y, r.y + r.h, 20):
                            grid[(gy - min_y) // 20][(gx - min_x) // 20] = CHARS.get(it["type"], ".")
            data = {"format": "grid", "cell": 20, "x": min_x, "y": min_y, "rle": True,
                    "rows": [self._rle_encode("".join(row)) for row in grid]}
        with open(MAP_PATH, "w") as f:
            json.dump(data, f, separators=(",", ":"))

    def load_map(self):
        try:
            with open(MAP_PATH, "r") as f:
                data = json.load(f)
            self.walls, self.props, self.floors = [], [], []
            if data.get("format") == "grid":
                ox, oy = data["x"], data["y"]
                buckets = {"#": self.walls, "=": self.walls,
                           "T": self.props, "C": self.props}
                for j, raw in enumerate(data["rows"]):
                    row = self._rle_decode(raw) if data.get("rle") else raw
                    for i, ch in enumerate(row):
                        if ch == ".":
                            continue
                        cell = {"rect": pygame.Rect(ox + i * 20, oy + j * 20, 20, 20),
                                "type": TO_TYPE.get(ch, "wood")}
                        if ch in buckets:
                            buckets[ch].append(cell)
                        else:
                            # полы (w, ~, d, a)
                            self.floors.append(cell)
            else:
                # старый формат со списками прямоугольников — тоже читаем
                def unpack(raw_list, target):
                    for obj in raw_list:
                        r = obj["rect"]
                        x, y, w, h = r if len(r) == 4 else (r[0], r[1], 20, 20)
                        for gx in range(x, x + w, 20):
                            for gy in range(y, y + h, 20):
                                target.append({"rect": pygame.Rect(gx, gy, 20, 20),
                                               "type": obj["type"]})
                unpack(data.get("walls", []), self.walls)
                unpack(data.get("props", []), self.props)
                unpack(data.get("floors", []), self.floors)
            self.update_colliders()
        except Exception as e:
            print("Ошибка загрузки:", e)
            self.generate_default()

    def draw(self, surface, camera):
        surface.fill((70, 100, 60))
        for i in range(30):
            px = (i * 137) % self.width
            py = (i * 241) % self.height
            sx, sy = camera.world_to_screen(px, py)
            if -200 < sx < 1160 and -200 < sy < 740:
                pygame.draw.circle(surface, (65, 95, 55), (int(sx), int(sy)), max(1, int(200 * camera.zoom)))

        for f in self.floors:
            r = f["rect"]
            sx, sy = camera.world_to_screen(r.x, r.y)
            sw, sh = r.w * camera.zoom, r.h * camera.zoom
            if sw > 0 and sh > 0:
                if f["type"] == "wood": col = (80, 70, 60)
                elif f["type"] == "water": col = (30, 80, 150)
                elif f["type"] == "dirt": col = (120, 100, 80)
                elif f["type"] == "asphalt": col = (50, 50, 50)
                else: col = (80, 70, 60)
                pygame.draw.rect(surface, col, (sx, sy, sw+1, sh+1))

        wall_positions = {(w["rect"].x, w["rect"].y) for w in self.walls}
        for w in self.walls:
            r = w["rect"]
            sx, sy = camera.world_to_screen(r.x, r.y)
            sw, sh = r.w * camera.zoom, r.h * camera.zoom
            if sw > 0 and sh > 0:
                if w["type"] == "wall":
                    pygame.draw.rect(surface, (100, 100, 100), (sx, sy, sw+1, sh+1))
                    line_color = (30, 30, 30)
                elif w["type"] == "window":
                    pygame.draw.rect(surface, (50, 150, 200), (sx, sy, sw+1, sh+1))
                    line_color = (255, 255, 255)

                lw = max(1, int(2 * camera.zoom))
                if r.w == 20 and r.h == 20:
                    if (r.x, r.y - 20) not in wall_positions:
                        pygame.draw.line(surface, line_color, (sx, sy), (sx+sw, sy), lw)
                    if (r.x, r.y + 20) not in wall_positions:
                        pygame.draw.line(surface, line_color, (sx, sy+sh), (sx+sw, sy+sh), lw)
                    if (r.x - 20, r.y) not in wall_positions:
                        pygame.draw.line(surface, line_color, (sx, sy), (sx, sy+sh), lw)
                    if (r.x + 20, r.y) not in wall_positions:
                        pygame.draw.line(surface, line_color, (sx+sw, sy), (sx+sw, sy+sh), lw)

        for p in self.props:
            r = p["rect"]
            sx, sy = camera.world_to_screen(r.x, r.y)
            sw, sh = r.w * camera.zoom, r.h * camera.zoom
            if sw > 0 and sh > 0:
                if p["type"] == "tree":
                    cx, cy = sx + sw/2, sy + sh/2
                    r_tree = max(1, int((sw / 2) * 1.5))
                    pygame.draw.ellipse(surface, (40, 60, 40), (int(cx - r_tree*1.1), int(cy - r_tree*0.9), int(r_tree*2.2), int(r_tree*1.8)))
                    pygame.draw.circle(surface, (35, 75, 35), (int(cx), int(cy)), r_tree)
                elif p["type"] == "crate":
                    pygame.draw.rect(surface, (139, 90, 43), (sx, sy, sw+1, sh+1))
                    pygame.draw.rect(surface, (80, 50, 20), (sx, sy, sw+1, sh+1), max(1, int(2*camera.zoom)))


class MapEditor:
    def __init__(self, game_map):
        self.map = game_map
        self.active = False
        self.tool = "wall"
        self.drawing = False
        self.brush_size = 1

        self.history = []  # История для Undo
        self.backup_walls = []
        self.backup_props = []
        self.backup_floors = []

        self.tools = [
            ("wall", "Стена", (100, 100, 100)),
            ("window", "Окно", (50, 150, 200)),
            ("floor", "Дерево", (80, 70, 60)),
            ("dirt", "Грунт", (120, 100, 80)),
            ("asphalt", "Асфальт", (50, 50, 50)),
            ("water", "Вода", (30, 80, 150)),
            ("tree", "Дерево", (35, 75, 35)),
            ("crate", "Ящик", (139, 90, 43)),
            ("erase", "Ластик", (200, 50, 50))
        ]

    def handle_ui(self, vx, vy):
        if not self.active: return False

        # Инструменты
        for i, (t_id, t_name, t_col) in enumerate(self.tools):
            if pygame.Rect(10, 60 + i*28, 140, 25).collidepoint(vx, vy):
                self.tool = t_id
                return True

        # Размер кисти (1-10) - 2 ряда по 5 кнопок
        base_y = 60 + len(self.tools)*28 + 20
        for i in range(1, 11):
            row = (i-1) // 5
            col = (i-1) % 5
            if pygame.Rect(10 + col*28, base_y + row*28, 25, 25).collidepoint(vx, vy):
                self.brush_size = i
                return True

        # Кнопки Отмена и Сохранить
        btn_y = base_y + 2*28 + 10
        if pygame.Rect(10, btn_y, 65, 30).collidepoint(vx, vy):
            self.undo()
            return True
        if pygame.Rect(85, btn_y, 65, 30).collidepoint(vx, vy):
            self.map.save_map()
            return True

        return False

    def undo(self):
        if self.history:
            state = self.history.pop()
            self.map.walls = copy.deepcopy(state[0])
            self.map.props = copy.deepcopy(state[1])
            self.map.floors = copy.deepcopy(state[2])
            self.map.update_colliders()

    def start_draw(self, vx, vy, camera):
        self.drawing = True
        self.backup_walls = copy.deepcopy(self.map.walls)
        self.backup_props = copy.deepcopy(self.map.props)
        self.backup_floors = copy.deepcopy(self.map.floors)

        # Сохраняем в историю
        self.history.append((self.backup_walls, self.backup_props, self.backup_floors))
        if len(self.history) > 20:
            self.history.pop(0)

        self._apply_tool(vx, vy, camera)

    def update_draw(self, vx, vy, camera):
        if self.drawing:
            self._apply_tool(vx, vy, camera)

    def rollback(self):
        if self.drawing:
            # Удаляем неудачную попытку из истории
            if self.history:
                self.history.pop()

            self.map.walls = copy.deepcopy(self.backup_walls)
            self.map.props = copy.deepcopy(self.backup_props)
            self.map.floors = copy.deepcopy(self.backup_floors)
            self.drawing = False
            self.map.update_colliders()

    def end_draw(self):
        self.drawing = False
        self.map.update_colliders()

    def _apply_tool(self, vx, vy, camera):
        wx, wy = camera.screen_to_world(vx, vy)
        base_gx = int(wx / 20) * 20
        base_gy = int(wy / 20) * 20

        offset_left = -((self.brush_size - 1) // 2)
        offset_right = self.brush_size // 2

        for dx in range(offset_left, offset_right + 1):
            for dy in range(offset_left, offset_right + 1):
                gx = base_gx + dx * 20
                gy = base_gy + dy * 20

                # УДАЛЯЕМ СТАРЫЙ БЛОК, ЧТОБЫ ПОСТАВИТЬ НОВЫЙ
                if self.tool in ("wall", "window"):
                    self.map.walls = [w for w in self.map.walls if not (w["rect"].x == gx and w["rect"].y == gy)]
                    self.map.walls.append({"rect": pygame.Rect(gx, gy, 20, 20), "type": self.tool})

                elif self.tool in ("floor", "water", "dirt", "asphalt"):
                    self.map.floors = [f for f in self.map.floors if not (f["rect"].x == gx and f["rect"].y == gy)]
                    ftype = "wood" if self.tool == "floor" else self.tool
                    self.map.floors.append({"rect": pygame.Rect(gx, gy, 20, 20), "type": ftype})

                elif self.tool in ("tree", "crate"):
                    self.map.props = [p for p in self.map.props if not (p["rect"].x == gx and p["rect"].y == gy)]
                    self.map.props.append({"rect": pygame.Rect(gx, gy, 20, 20), "type": self.tool})

                elif self.tool == "erase":
                    erase_rect = pygame.Rect(gx, gy, 20, 20)
                    self.map.walls = [w for w in self.map.walls if not w["rect"].colliderect(erase_rect)]
                    self.map.props = [p for p in self.map.props if not p["rect"].colliderect(erase_rect)]
                    self.map.floors = [f for f in self.map.floors if not f["rect"].colliderect(erase_rect)]

    def draw_ui(self, surface, font):
        if not self.active: return
        pygame.draw.rect(surface, (30, 35, 45), (0, 60, 160, 460))

        # Инструменты
        for i, (t_id, t_name, t_col) in enumerate(self.tools):
            r = pygame.Rect(10, 60 + i*28, 140, 25)
            is_active = (self.tool == t_id)
            bg_color = (70, 130, 180) if is_active else (50, 55, 65)
            pygame.draw.rect(surface, bg_color, r, border_radius=5)
            pygame.draw.rect(surface, t_col, (r.x, r.y, 10, 25), border_top_left_radius=5, border_bottom_left_radius=5)
            text = font.render(t_name, True, (255, 255, 255))
            surface.blit(text, text.get_rect(center=r.center))

        # Размер кисти
        base_y = 60 + len(self.tools)*28 + 20
        text = font.render("Кисть:", True, (200, 200, 200))
        surface.blit(text, (10, base_y - 20))

        for i in range(1, 11):
            row = (i-1) // 5
            col = (i-1) % 5
            r = pygame.Rect(10 + col*28, base_y + row*28, 25, 25)
            is_active = (self.brush_size == i)
            bg_color = (70, 130, 180) if is_active else (50, 55, 65)
            pygame.draw.rect(surface, bg_color, r, border_radius=5)
            text = font.render(str(i), True, (255, 255, 255))
            surface.blit(text, text.get_rect(center=r.center))

        # Кнопки Отмена и Сохранить
        btn_y = base_y + 2*28 + 10
        undo_rect = pygame.Rect(10, btn_y, 65, 30)
        save_rect = pygame.Rect(85, btn_y, 65, 30)

        pygame.draw.rect(surface, (200, 100, 50), undo_rect, border_radius=5)
        text = font.render("Отмена", True, (255, 255, 255))
        surface.blit(text, text.get_rect(center=undo_rect.center))

        pygame.draw.rect(surface, (50, 150, 50), save_rect, border_radius=5)
        text = font.render("Сохранить", True, (255, 255, 255))
        surface.blit(text, text.get_rect(center=save_rect.center))
