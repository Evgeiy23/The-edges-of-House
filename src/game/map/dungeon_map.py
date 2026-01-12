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

                    if group:  # Only add non-empty groups
                        self.collision_groups[group_id] = group
                        group_id += 1

    def get_collision_groups(self):
        if not self.collision_groups:
            self.create_collision_groups()
        return self.collision_groups

    def _load_textures(self):
        # Default floor
        self.textures[0] = self._load_tex("tile_0000.png")  # Corridor
        self.textures[2] = self._load_tex("tile_0000.png")  # Room Floor
        
        # Walls
        self.textures[1] = self._load_tex("tile_0040.png")
        
        # Floor variants (Walkable)
        self.textures[10] = self._load_tex("tile_0024.png")
        self.textures[11] = self._load_tex("tile_0094.png")
        
        # Decorations (Unwalkable)
        self.textures[20] = self._load_tex("tile_0082.png")
        self.textures[21] = self._load_tex("tile_0065.png")
        self.textures[22] = self._load_tex("tile_0063.png")

        # Exit
        # Keep default exit color or load texture if needed. 
        # For now we rely on draw_map colors for exit (3), but we can add texture if available.
    
    def _load_tex(self, name):
        path = os.path.join("resources", "map", name)
        if os.path.exists(path):
            return arcade.load_texture(path)
        return None

    def generate(self, game_cfg, spawn_corner=None):
        result = generate_dungeon(
            self.map_width, self.map_height, game_cfg, spawn_corner)
        if len(result) == 7:  # Current function returns 7 values
            (self.map_data, self.rooms, self.room_tile_map,
             self.corridor_tiles, self.exit_pos, self.exit_room_idx,
             exit_door_positions) = result
        else:  # Fallback for different return values
            (self.map_data, self.rooms, self.room_tile_map,
             self.corridor_tiles, self.exit_pos, self.exit_room_idx) = result

        # self.create_collision_groups()

    def _apply_payload(self, payload):
        """Load map data and metadata from a prepared payload instead of generating."""
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

        self.corridor_tiles = set(payload.get("corridor_tiles", set()))
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

    def is_walkable(self, x, y):
        tile_value = self.get_tile_value(x, y)
        # 0, 2: Standard floors
        # 3: Exit
        # 10, 11: Floor variants
        return tile_value in (0, 2, 3, 10, 11)

    def get_room_id(self, x, y):
        return self.room_tile_map.get((x, y))

    def is_corridor(self, x, y):
        return (x, y) in self.corridor_tiles
