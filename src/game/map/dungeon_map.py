import arcade
import os
from game.logic.map.generation import generate_dungeon
from game.logic.map.storage import rebuild_metadata


class DungeonMap:
    def __init__(self, map_width, map_height, tile_size, game_cfg, spawn_corner=None, map_payload=None, map_name="current"):
        self.map_width = map_width
        self.map_height = map_height
        self.tile_size = tile_size
        self.spawn_corner = spawn_corner
        self.map_name = map_name
        self.map_data = []
        self.rooms = []
        self.room_tile_map = {}
        self.corridor_tiles = set()
        self.exit_pos = None
        self.exit_room_idx = None
        self.exit_door_positions = []  # Позиции прохода в комнату с выходом для закрытия
        self.exit_door_closed = False  # Флаг закрытия прохода
        self.collision_groups = {}
        self.valid_spawn_coords = None # Кэшированный список допустимых координат появления

        self.textures = {}
        self._load_textures()

        if map_payload:
            self._apply_payload(map_payload)
        else:
            self.generate(game_cfg, spawn_corner)

    def create_collision_groups(self):
        visited = set()
        group_id = 0

        for y in range(self.map_height):
            for x in range(self.map_width):
                if (x, y) not in visited and not self.is_walkable(x, y):
                    group = []
                    stack = [(x, y)]

                    while stack:
                        curr_x, curr_y = stack.pop()

                        if (curr_x, curr_y) in visited:
                            continue

                        if not (0 <= curr_x < self.map_width and 0 <= curr_y < self.map_height):
                            continue

                        if self.is_walkable(curr_x, curr_y):
                            continue

                        visited.add((curr_x, curr_y))
                        group.append((curr_x, curr_y))

                        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                            next_x, next_y = curr_x + dx, curr_y + dy
                            if ((next_x, next_y) not in visited and
                                0 <= next_x < self.map_width and
                                0 <= next_y < self.map_height and
                                    not self.is_walkable(next_x, next_y)):
                                stack.append((next_x, next_y))

                    if group:  # Добавлять только непустые группы
                        self.collision_groups[group_id] = group
                        group_id += 1

    def get_collision_groups(self):
        if not self.collision_groups:
            self.create_collision_groups()
        return self.collision_groups

    def _load_textures(self):
        # Пол по умолчанию
        self.textures[0] = self._load_tex("tile_0000.png")  # Коридор
        self.textures[2] = self._load_tex("tile_0000.png")  # Пол комнаты
        
        # Стены
        self.textures[1] = self._load_tex("tile_0040.png")
        
        # Варианты пола (Проходимые)
        self.textures[10] = self._load_tex("tile_0024.png")
        self.textures[11] = self._load_tex("tile_0094.png")
        
        # Декорации (Непроходимые)
        self.textures[20] = self._load_tex("tile_0082.png")
        self.textures[21] = self._load_tex("tile_0065.png")
        self.textures[22] = self._load_tex("tile_0063.png")

        # Выход
        # Оставить цвет выхода по умолчанию или загрузить текстуру, если необходимо. 
        # Пока мы полагаемся на цвета draw_map для выхода (3), но мы можем добавить текстуру, если она доступна.
    
    def _load_tex(self, name):
        path = os.path.join("resources", "map", name)
        if os.path.exists(path):
            return arcade.load_texture(path)
        return None

    def generate(self, game_cfg, spawn_corner=None):
        result = generate_dungeon(
            self.map_width, self.map_height, game_cfg, spawn_corner)
        if len(result) == 7:  # Текущая функция возвращает 7 значений
            (self.map_data, self.rooms, self.room_tile_map,
             self.corridor_tiles, self.exit_pos, self.exit_room_idx,
             self.exit_door_positions) = result
        else:  # Резервный вариант для других возвращаемых значений
            (self.map_data, self.rooms, self.room_tile_map,
             self.corridor_tiles, self.exit_pos, self.exit_room_idx) = result

        # self.create_collision_groups()

    def _apply_payload(self, payload):
        """Загружает данные карты и метаданные из подготовленной полезной нагрузки вместо генерации."""
        self.map_data = payload.get("map_data", [])
        self.map_height = len(self.map_data)
        self.map_width = len(self.map_data[0]) if self.map_data else 0

        self.rooms = payload.get("rooms", [])

        raw_room_tile_map = payload.get("room_tile_map", {})
        normalized_tile_map = {}
        for key, val in (raw_room_tile_map or {}).items():
            if isinstance(key, str):
                try:
                    x_str, y_str = key.split(",")
                    normalized_tile_map[(int(x_str), int(y_str))] = val
                    continue
                except Exception:
                    pass
            normalized_tile_map[key] = val
        self.room_tile_map = normalized_tile_map

        # self.corridor_tiles = set(payload.get("corridor_tiles", set()))
        # Безопасная загрузка corridor_tiles (преобразование из list в tuple для set)
        raw_corridors = payload.get("corridor_tiles", [])
        self.corridor_tiles = set()
        for t in raw_corridors:
            if isinstance(t, (list, tuple)) and len(t) >= 2:
                self.corridor_tiles.add((int(t[0]), int(t[1])))

        exit_pos = payload.get("exit_pos")
        self.exit_pos = tuple(exit_pos) if exit_pos else None
        self.exit_room_idx = payload.get("exit_room_idx")
        # Загружаем позиции прохода в комнату с выходом
        exit_door_raw = payload.get("exit_door_positions", [])
        if exit_door_raw:
            self.exit_door_positions = [tuple(p) if isinstance(
                p, (list, tuple)) else p for p in exit_door_raw]
        else:
            self.exit_door_positions = []
        self.exit_door_closed = payload.get("exit_door_closed", False)

        if not self.rooms or not self.room_tile_map or not self.corridor_tiles:
            rebuilt = rebuild_metadata(
                self.map_data, self.exit_pos, payload.get("spawn_corner"))
            self.rooms = rebuilt.get("rooms", [])
            self.room_tile_map = rebuilt.get("room_tile_map", {})
            self.corridor_tiles = rebuilt.get("corridor_tiles", set())
            self.exit_pos = rebuilt.get("exit_pos")
            self.exit_room_idx = rebuilt.get("exit_room_idx")

    def get_tile_value(self, x, y):
        if 0 <= x < self.map_width and 0 <= y < self.map_height:
            return self.map_data[y][x]
        return None

    def get_wall_coords(self):
        """Возвращает список всех координат стен в структурированном формате."""
        if not self.wall_list:
            self._cache_map_data()
        return self.wall_list

    def get_room_coords(self):
        """Возвращает список всех координат центров комнат в структурированном формате."""
        if not self.room_center_list:
            self._cache_map_data()
        return self.room_center_list

    def is_walkable(self, x, y):
        tile_value = self.get_tile_value(x, y)
        # 0, 2: Стандартные полы
        # 3: Выход
        # 10, 11: Варианты пола
        return tile_value in (0, 2, 3, 10, 11)

    def get_room_id(self, x, y):
        return self.room_tile_map.get((x, y))

    def is_corridor(self, x, y):
        return (x, y) in self.corridor_tiles

    def close_exit_door(self):
        """Закрывает проход в комнату с выходом"""
        if self.exit_door_closed or not self.exit_door_positions:
            return

        for x, y in self.exit_door_positions:
            if 0 <= x < self.map_width and 0 <= y < self.map_height:
                # Меняем тайл пола на стену (1)
                self.map_data[y][x] = 1
                
                # Если используем группы коллизий, нужно их обновить
                # Но пока просто пересоздадим
        
        self.exit_door_closed = True
        self.create_collision_groups()  # Обновляем коллизии

    def get_valid_spawn_coords(self):
        """Возвращает список всех допустимых координат появления."""
        if not self.valid_spawn_coords:
            self._cache_map_data()
        return self.valid_spawn_coords

    def _cache_map_data(self):
        self.wall_list = []
        self.room_center_list = []
        self.valid_spawn_coords = []
        
        for y in range(self.map_height):
            for x in range(self.map_width):
                if not self.is_walkable(x, y):
                    self.wall_list.append((x, y))
                else:
                    self.valid_spawn_coords.append((x, y))
                    
        for room in self.rooms:
            # Вычислить центр
            if isinstance(room, dict):
                cx = (room.get('x1', 0) + room.get('x2', 0)) // 2
                cy = (room.get('y1', 0) + room.get('y2', 0)) // 2
                self.room_center_list.append((cx, cy))
            elif hasattr(room, 'center'):
                self.room_center_list.append(room.center)
            elif hasattr(room, 'cx'):
                 self.room_center_list.append((room.cx, room.cy))

    def has_line_of_sight(self, start, end):
        """Checks if there is a direct walkable line between start and end (grid coordinates)."""
        x0, y0 = start
        x1, y1 = end
        
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        x, y = x0, y0
        sx = -1 if x0 > x1 else 1
        sy = -1 if y0 > y1 else 1
        
        if dx > dy:
            err = dx / 2.0
            while x != x1:
                if not self.is_walkable(x, y):
                    return False
                err -= dy
                if err < 0:
                    y += sy
                    err += dx
                x += sx
        else:
            err = dy / 2.0
            while y != y1:
                if not self.is_walkable(x, y):
                    return False
                err -= dx
                if err < 0:
                    x += sx
                    err += dy
                y += sy
                
        # Также проверяем конечную точку (хотя обычно цель проходима, если мы хотим туда попасть)
        if not self.is_walkable(x1, y1):
            return False
            
        return True

