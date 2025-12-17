import arcade
import arcade.gui
import arcade.camera as arcade_camera
import pyglet
import os
import json
from project import ProjectSettings
from utils import get_config_path, get_savegame_path
from game.logic.music import find_music_file, play_loop, stop_player
from game.logic.map.storage import generate_and_store_map
from game.entities.player import Player
from game.map.dungeon_map import DungeonMap


class GameWindow(arcade.View):
    DIFFICULTY_EASY = ProjectSettings.Game.DIFFICULTY_EASY
    DIFFICULTY_MEDIUM = ProjectSettings.Game.DIFFICULTY_MEDIUM
    DIFFICULTY_HARD = ProjectSettings.Game.DIFFICULTY_HARD

    @staticmethod
    def compute_map_dimensions(level, game_cfg):
        base_width = game_cfg.SCREEN_WIDTH // game_cfg.TILE_SIZE
        base_height = game_cfg.SCREEN_HEIGHT // game_cfg.TILE_SIZE

        width_mult = min(game_cfg.MAX_MAP_MULTIPLIER,
                         game_cfg.MAP_WIDTH_MULTIPLIER +
                         (level - 1) * game_cfg.MAP_GROWTH_PER_LEVEL)
        height_mult = min(game_cfg.MAX_MAP_MULTIPLIER,
                          game_cfg.MAP_HEIGHT_MULTIPLIER +
                          (level - 1) * game_cfg.MAP_GROWTH_PER_LEVEL)

        map_width = int(base_width * width_mult * game_cfg.MAP_SCALE)
        map_height = int(base_height * height_mult * game_cfg.MAP_SCALE)
        return map_width, map_height

    def __init__(self, difficulty=None, load_save=False, map_payload=None, map_name="current", level_override=None, spawn_corner=None):
        super().__init__()

        self.screen_width = 0
        self.screen_height = 0
        self.map_width = 0
        self.map_height = 0
        self.tile_size = ProjectSettings.Game.TILE_SIZE

        self.dungeon_map = None
        self.player = None
        self.visible_tiles = set()
        self.explored_tiles = set()
        self.visibility_grid = None
        self.explored_grid = None
        self.use_fov = False
        self.view_radius = 8
        self.hard_save_used = False
        self.save_point_pos = None
        self.save_point_used = False
        self.level = level_override or 1
        self.suspense_player = None
        self.camera = None
        self.move_hold = {"up": False, "down": False,
                          "left": False, "right": False}
        self.is_running = False
        self.move_cooldown = 0.1  # This is for the easy mode
        self.move_timer = 0.0
        self.exit_music_played = False
        self.frame_limit = ProjectSettings.Game.DEFAULT_FRAME_LIMIT
        # Сохраняем выбранный угол спавна, чтобы подобрать выход диагонально
        self.spawn_corner = spawn_corner
        self.map_payload = map_payload
        self.map_name = map_name
        # Отдельная камера для UI/миникарты (без смещения игровой камеры)
        self.ui_camera = arcade_camera.Camera2D()
        # Плавное отображение игрока на миникарте
        self.minimap_player_draw_pos = None

        # Variables for slippery movement (inertia)
        self.velocity_x = 0.0
        self.velocity_y = 0.0
        # For slippery effect (1.0 = no friction, 0.0 = immediate stop)
        self.friction = 0.85  # Lower friction means more sliding
        self.acceleration = 0.1  # Lower acceleration means slower base movement

        self.manager = arcade.gui.UIManager()
        self.manager.disable()

        self.pause_manager = arcade.gui.UIManager()
        self.pause_manager.disable()

        self.music_volume = 1.0
        self.sound_volume = 1.0

        self.game_music_sound = None
        self.game_music_player = None

        # Плавная анимация перемещения по клеткам
        self.move_anim_time = 0.0
        self.move_anim_duration = 0.15
        self.move_anim_start = [0.0, 0.0]
        self.move_anim_target = [0.0, 0.0]

        self.difficulty = difficulty or self.DIFFICULTY_EASY
        self.show_pause_menu = False
        self.hard_save_used = False

        self._setup_difficulty_visibility()

        self.load_settings()
        if load_save:
            if not self.load_game():
                self.setup_game()
            else:
                self.update_visibility()
        else:
            self.setup_game()
        self.play_game_music()
        self.apply_frame_limit()

    def load_settings(self):
        config_file = get_config_path()
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.music_volume = config.get('music_volume', 1.0)
                    self.sound_volume = config.get('sound_volume', 1.0)
                    self.frame_limit = config.get(
                        'frame_limit', ProjectSettings.Game.DEFAULT_FRAME_LIMIT)
            except Exception as e:
                print(f"Ошибка загрузки настроек: {e}")

    def find_music_file(self, preferred_filename=None, folder_path=None):
        return find_music_file(preferred_filename, folder_path)

    def play_game_music(self):
        path = self.find_music_file(
            "dark-grim-horror-ambience-for-gaming-166948.mp3")
        self.stop_game_music()
        self.game_music_player, self.game_music_sound = play_loop(
            path, self.music_volume)
        self.apply_frame_limit()

    def stop_game_music(self):
        stop_player(self.game_music_player)
        self.game_music_player = None
        self.game_music_sound = None

    def setup_game(self):
        try:
            game_cfg = ProjectSettings.Game
            map_width, map_height = self.compute_map_dimensions(
                self.level, game_cfg)

            payload = self.map_payload
            if not payload:
                import random
                if self.spawn_corner is None:
                    self.spawn_corner = random.choice(
                        ["bottom_left", "bottom_right"])
                payload = generate_and_store_map(
                    map_width, map_height, game_cfg, self.spawn_corner, map_name=self.map_name)

            self._apply_map_payload(payload, game_cfg)
            # После использования — сбрасываем, чтобы уровни генерировались заново
            self.map_payload = None
        except Exception as e:
            print(f"Ошибка при генерации карты: {e}")
            import traceback
            traceback.print_exc()
            game_cfg = ProjectSettings.Game
            try:
                self.map_width = 32
                self.map_height = 24
                self.spawn_corner = self.spawn_corner or "bottom_left"
                fallback_payload = generate_and_store_map(
                    self.map_width, self.map_height, game_cfg, self.spawn_corner, map_name=self.map_name)
                self._apply_map_payload(fallback_payload, game_cfg)
            except Exception:
                self.dungeon_map = DungeonMap(
                    32, 24, self.tile_size, game_cfg, self.spawn_corner)
                self.player = Player(self.tile_size)
                self.visible_tiles = set()
                self.explored_tiles = set()
                self.exit_music_played = False
                self.save_point_used = False
                self.save_point_pos = None
                self.explored_grid = None
                self.visibility_grid = None
                self.move_anim_time = 0.0
                self.place_player()
                self.update_visibility()

                if self.camera is None and hasattr(self, 'window') and self.window:
                    self.camera = arcade_camera.Camera2D()
                    tile_size = self.tile_size
                    if self.player and self.player.pos:
                        start_cam_x = self.player.pos[0] * \
                            tile_size + tile_size // 2
                        start_cam_y = self.player.pos[1] * \
                            tile_size + tile_size // 2
                        self.camera.position = (start_cam_x, start_cam_y)

    def _apply_map_payload(self, payload, game_cfg):
        if not payload or not payload.get("map_data"):
            raise ValueError("Нет данных карты для загрузки")

        map_data = payload.get("map_data")
        self.map_height = len(map_data)
        self.map_width = len(map_data[0]) if self.map_height > 0 else 0
        self.spawn_corner = payload.get("spawn_corner", self.spawn_corner)

        self.dungeon_map = DungeonMap(
            self.map_width, self.map_height, self.tile_size, game_cfg, self.spawn_corner, map_payload=payload)

        self.player = Player(self.tile_size)

        self.visible_tiles = set()
        self.explored_tiles = set()
        self.visibility_grid = None
        self.explored_grid = None
        self.exit_music_played = False
        self.save_point_used = False
        # Сброс анимации движения
        self.move_anim_time = 0.0
        if self.player and hasattr(self.player, "draw_pos"):
            self.move_anim_start = list(self.player.draw_pos)
            self.move_anim_target = list(self.player.draw_pos)
        if self.difficulty in (self.DIFFICULTY_MEDIUM, self.DIFFICULTY_HARD):
            self.place_save_point()
        else:
            self.save_point_pos = None

        self.place_player()
        self.update_visibility()

        if self.camera is None and hasattr(self, 'window') and self.window:
            self.camera = arcade_camera.Camera2D()
            tile_size = self.tile_size
            if self.player and self.player.pos:
                start_cam_x = self.player.pos[0] * tile_size + tile_size // 2
                start_cam_y = self.player.pos[1] * tile_size + tile_size // 2
                self.camera.position = (start_cam_x, start_cam_y)

    def connect_rooms(self, room_a, room_b, is_hall=False):
        return

    def place_save_point(self):
        if not self.dungeon_map or not self.dungeon_map.rooms or len(self.dungeon_map.rooms) < 2:
            self.save_point_pos = None
            return

        available_rooms = []
        for i, room in enumerate(self.dungeon_map.rooms):
            if i != 0 and i != self.dungeon_map.exit_room_idx:
                available_rooms.append((i, room))

        if not available_rooms:
            self.save_point_pos = None
            return

        import random
        room_idx, room = random.choice(available_rooms)

        if isinstance(room, dict):
            x1 = room.get("x1", 0)
            y1 = room.get("y1", 0)
            x2 = room.get("x2", 0)
            y2 = room.get("y2", 0)
            save_x = (x1 + x2) // 2
            save_y = (y1 + y2) // 2
        else:
            x, y, w, h = room
            save_x = x + w // 2
            save_y = y + h // 2

        if 0 <= save_x < self.dungeon_map.map_width and 0 <= save_y < self.dungeon_map.map_height:
            self.save_point_pos = (save_x, save_y)
        else:
            self.save_point_pos = None

    def place_player(self):
        if not self.dungeon_map or not self.player:
            return

        # Ставим игрока ближе к центру карты: ищем проходимый тайл вокруг центра
        center_x = self.dungeon_map.map_width // 2
        center_y = self.dungeon_map.map_height // 2

        def is_free(x, y):
            return (0 <= x < self.dungeon_map.map_width and
                    0 <= y < self.dungeon_map.map_height and
                    self.dungeon_map.is_walkable(x, y))

        spawn_pos = None
        # Поиск по возрастающим радиусам от центра (до краёв карты)
        max_radius = max(center_x, center_y)
        for r in range(0, max_radius + 1):
            found = False
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    x = center_x + dx
                    y = center_y + dy
                    if is_free(x, y):
                        spawn_pos = (x, y)
                        found = True
                        break
                if found:
                    break
            if spawn_pos:
                break

        if not spawn_pos:
            # На крайний случай — левый верхний угол
            spawn_pos = (1, 1)

        self.player.set_pos(*spawn_pos)
        self.visible_tiles.add(spawn_pos)
        # Инициализируем позицию для плавной миникарты
        self.minimap_player_draw_pos = (
            float(spawn_pos[0]), float(spawn_pos[1]))

    def is_blocking(self, x, y):
        if not self.dungeon_map:
            return True
        if x < 0 or x >= self.dungeon_map.map_width or y < 0 or y >= self.dungeon_map.map_height:
            return True
        return self.dungeon_map.get_tile_value(x, y) == 1

    def _get_wall_rotation_angle(self, x, y):
        if not self.dungeon_map:
            return 0

        neighbors = {
            'north': self.dungeon_map.get_tile_value(x, y + 1) if y + 1 < self.dungeon_map.map_height else None,
            'south': self.dungeon_map.get_tile_value(x, y - 1) if y - 1 >= 0 else None,
            'east': self.dungeon_map.get_tile_value(x + 1, y) if x + 1 < self.dungeon_map.map_width else None,
            'west': self.dungeon_map.get_tile_value(x - 1, y) if x - 1 >= 0 else None,
        }

        east_walkable = neighbors['east'] != 1 and neighbors['east'] is not None
        west_walkable = neighbors['west'] != 1 and neighbors['west'] is not None
        north_wall = neighbors['north'] == 1
        south_wall = neighbors['south'] == 1

        if east_walkable and west_walkable:
            return 90

        if neighbors['north'] != 1 and neighbors['west'] != 1:
            return 90
        if neighbors['north'] != 1 and neighbors['east'] != 1:
            return 0
        if neighbors['south'] != 1 and neighbors['west'] != 1:
            return 0
        if neighbors['south'] != 1 and neighbors['east'] != 1:
            return 90

        return 0

    def cast_ray(self, start_x, start_y, end_x, end_y):
        visible = set()

        if start_x == end_x and start_y == end_y:
            visible.add((start_x, start_y))
            return visible

        dx = abs(end_x - start_x)
        dy = abs(end_y - start_y)
        sx = 1 if start_x < end_x else -1
        sy = 1 if start_y < end_y else -1
        err = dx - dy

        x, y = start_x, start_y
        max_steps = dx + dy + 1

        for _ in range(max_steps):
            if not self.dungeon_map or x < 0 or x >= self.dungeon_map.map_width or y < 0 or y >= self.dungeon_map.map_height:
                break

            visible.add((x, y))

            if x == end_x and y == end_y:
                break

            if self.is_blocking(x, y):
                break

            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy

        return visible

    def calculate_fov(self, center_x, center_y, radius):
        visible = set()
        visible.add((center_x, center_y))

        min_y = max(0, center_y - radius)
        max_y = min(self.dungeon_map.map_height, center_y + radius + 1)
        min_x = max(0, center_x - radius)
        max_x = min(self.dungeon_map.map_width, center_x + radius + 1)

        checked = set()

        for y in range(min_y, max_y):
            for x in range(min_x, max_x):
                dx = x - center_x
                dy = y - center_y
                distance_sq = dx * dx + dy * dy

                if distance_sq > radius * radius:
                    continue

                if distance_sq <= 2:
                    visible.add((x, y))
                else:
                    ray_visible = self.cast_ray(center_x, center_y, x, y)
                    visible.update(ray_visible)

        return visible

    def _setup_difficulty_visibility(self):
        if self.difficulty == self.DIFFICULTY_EASY:
            self.view_radius = 12
            self.use_fov = False
        elif self.difficulty == self.DIFFICULTY_MEDIUM:
            self.view_radius = 8
            self.use_fov = False
        else:
            self.view_radius = 5
            self.use_fov = True

    def update_visibility(self):
        self.visible_tiles.clear()

        if not self.player or not self.dungeon_map:
            return

        player_x, player_y = self.player.pos

        if self.use_fov:
            fov_tiles = self.calculate_fov(
                player_x, player_y, self.view_radius)

            for x, y in fov_tiles:
                if 0 <= x < self.dungeon_map.map_width and 0 <= y < self.dungeon_map.map_height:
                    self.visible_tiles.add((x, y))
        else:
            current_room_id = self.dungeon_map.get_room_id(player_x, player_y)

            min_y = max(0, player_y - self.view_radius)
            max_y = min(self.dungeon_map.map_height,
                        player_y + self.view_radius + 1)
            min_x = max(0, player_x - self.view_radius)
            max_x = min(self.dungeon_map.map_width,
                        player_x + self.view_radius + 1)

            # Pre-calculate player position related values
            player_radius_sq = self.view_radius * self.view_radius

            for y in range(min_y, max_y):
                for x in range(min_x, max_x):
                    if 0 <= x < self.dungeon_map.map_width and 0 <= y < self.dungeon_map.map_height:
                        tile_value = self.dungeon_map.get_tile_value(x, y)
                        tile_room_id = self.dungeon_map.get_room_id(x, y)
                        is_corridor = self.dungeon_map.is_corridor(x, y)

                        if is_corridor:
                            dx = x - player_x
                            dy = y - player_y
                            distance_sq = dx * dx + dy * dy
                            if distance_sq <= player_radius_sq:
                                self.visible_tiles.add((x, y))
                        elif tile_room_id is not None:
                            if tile_room_id == current_room_id:
                                self.visible_tiles.add((x, y))
                        elif tile_value == 1:
                            is_room_wall = False
                            neighbor_room_id = None
                            has_corridor_neighbor = False
                            is_corridor_wall = False

                            # Check neighbors in a more efficient way
                            for dx_check in [-1, 0, 1]:
                                for dy_check in [-1, 0, 1]:
                                    if dx_check == 0 and dy_check == 0:
                                        continue
                                    check_x = x + dx_check
                                    check_y = y + dy_check
                                    if 0 <= check_x < self.dungeon_map.map_width and 0 <= check_y < self.dungeon_map.map_height:
                                        neighbor_room_id_check = self.dungeon_map.get_room_id(
                                            check_x, check_y)
                                        if neighbor_room_id_check is not None:
                                            is_room_wall = True
                                            if neighbor_room_id is None:
                                                neighbor_room_id = neighbor_room_id_check
                                        if self.dungeon_map.is_corridor(check_x, check_y):
                                            has_corridor_neighbor = True
                                            is_corridor_wall = True

                            if is_room_wall:
                                if neighbor_room_id == current_room_id:
                                    self.visible_tiles.add((x, y))
                            elif is_corridor_wall and has_corridor_neighbor:
                                dx = x - player_x
                                dy = y - player_y
                                distance_sq = dx * dx + dy * dy
                                if distance_sq <= 2:
                                    self.visible_tiles.add((x, y))
                        elif tile_value == 3:
                            if tile_room_id == current_room_id:
                                self.visible_tiles.add((x, y))

        if self.dungeon_map and self.dungeon_map.map_width > 0 and self.dungeon_map.map_height > 0:
            width = self.dungeon_map.map_width
            height = self.dungeon_map.map_height

            # Полное обновление сеток видимости/исследования
            self.visibility_grid = [[False] * width for _ in range(height)]
            if (not self.explored_grid or
                    len(self.explored_grid) != height or
                    len(self.explored_grid[0]) != width):
                self.explored_grid = [[False] * width for _ in range(height)]

            # Отмечаем текущую видимость и копим исследованные тайлы
            for x, y in self.visible_tiles:
                if 0 <= x < width and 0 <= y < height:
                    self.visibility_grid[y][x] = True
                    self.explored_grid[y][x] = True
                    self.explored_tiles.add((x, y))

            # Синхронизируем сетку исследованных с накопленным множеством (на случай загрузки сейва)
            for x, y in self.explored_tiles:
                if 0 <= x < width and 0 <= y < height:
                    self.explored_grid[y][x] = True

    def save_game(self):
        if self.difficulty == self.DIFFICULTY_EASY:
            save_file = get_savegame_path()
        elif self.difficulty == self.DIFFICULTY_MEDIUM:
            save_file = get_savegame_path()
        elif self.difficulty == self.DIFFICULTY_HARD:
            if self.hard_save_used:
                return False
            save_file = get_savegame_path()
            self.hard_save_used = True
        else:
            return False

        try:
            game_data = {
                "level": self.level,
                "player_pos": self.player.pos if self.player else [0, 0],
                "player_draw_pos": self.player.draw_pos if self.player else [0.0, 0.0],
                "visible_tiles": list(self.visible_tiles),
                "explored_tiles": list(self.explored_tiles),
                "map_data": self.dungeon_map.map_data if self.dungeon_map else [],
                "rooms": self.dungeon_map.rooms if self.dungeon_map else [],
                "room_tile_map": {f"{k[0]},{k[1]}": v for k, v in (self.dungeon_map.room_tile_map.items() if self.dungeon_map else {})},
                "corridor_tiles": list(self.dungeon_map.corridor_tiles if self.dungeon_map else set()),
                "exit_pos": self.dungeon_map.exit_pos if self.dungeon_map else None,
                "exit_room_idx": self.dungeon_map.exit_room_idx if self.dungeon_map else None,
                "exit_music_played": self.exit_music_played,
                "music_volume": self.music_volume,
                "sound_volume": self.sound_volume,
                "hard_save_used": self.hard_save_used,
                "save_point_pos": self.save_point_pos,
                "save_point_used": self.save_point_used,
            }
            save_data = {
                'difficulty': self.difficulty,
                'game_data': game_data
            }

            with open(save_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)

            return True

        except Exception as e:
            print(f"Ошибка сохранения игры: {e}")
            return False

    def load_game(self):
        save_file = get_savegame_path()
        if os.path.exists(save_file):
            try:
                with open(save_file, 'r', encoding='utf-8') as f:
                    save_data = json.load(f)
                    self.difficulty = save_data.get(
                        'difficulty', self.DIFFICULTY_EASY)

                    game_data = save_data.get('game_data', {})

                    if game_data:
                        self.level = game_data.get("level", 1)
                        player_pos = game_data.get("player_pos", [0, 0])
                        player_draw_pos = game_data.get(
                            "player_draw_pos", [0.0, 0.0])
                        map_data_loaded = game_data.get("map_data", [])
                        if map_data_loaded:
                            map_height = len(map_data_loaded)
                            map_width = len(
                                map_data_loaded[0]) if map_height > 0 else 0
                            game_cfg = ProjectSettings.Game
                            self.dungeon_map = DungeonMap(
                                map_width, map_height, self.tile_size, game_cfg, self.spawn_corner)
                            self.dungeon_map.map_data = map_data_loaded
                            self.dungeon_map.rooms = game_data.get("rooms", [])
                            self.dungeon_map.room_tile_map = {
                                tuple(map(int, k.split(","))): v
                                for k, v in game_data.get("room_tile_map", {}).items()
                            }
                            self.dungeon_map.corridor_tiles = set(
                                [tuple(t) for t in game_data.get("corridor_tiles", [])])
                            self.dungeon_map.exit_pos = tuple(
                                game_data.get("exit_pos")) if game_data.get("exit_pos") else None
                            self.dungeon_map.exit_room_idx = game_data.get(
                                "exit_room_idx", None)
                            self.map_width = map_width
                            self.map_height = map_height
                        else:
                            return False
                        self.visible_tiles = set(
                            [tuple(t) for t in game_data.get("visible_tiles", [])])
                        self.explored_tiles = set(
                            [tuple(t) for t in game_data.get("explored_tiles", [])]) if game_data.get("explored_tiles") else set()
                        self.player = Player(self.tile_size)
                        self.player.set_pos(player_pos[0], player_pos[1])
                        self.player.draw_pos = player_draw_pos
                        self.exit_music_played = game_data.get(
                            "exit_music_played", False)
                        self.music_volume = game_data.get(
                            "music_volume", self.music_volume)
                        self.sound_volume = game_data.get(
                            "sound_volume", self.sound_volume)
                        self.hard_save_used = game_data.get(
                            "hard_save_used", False)
                        self.save_point_pos = tuple(
                            game_data.get("save_point_pos")) if game_data.get("save_point_pos") else None
                        self.save_point_used = game_data.get(
                            "save_point_used", False)
                        self._setup_difficulty_visibility()
                        self.update_visibility()
                    else:
                        return False

                    return True

            except Exception as e:
                print(f"Ошибка загрузки игры: {e}")

        return False

    def setup_pause_menu(self):
        self.pause_manager.clear()
        settings = ProjectSettings.Settings

        main_box = arcade.gui.UIBoxLayout(vertical=True, space_between=15)

        title_label = arcade.gui.UILabel(
            text="ПАУЗА",
            font_size=32,
            text_color=arcade.color.WHITE,
            width=settings.SETTINGS_PANEL_WIDTH,
            align="center"
        )
        main_box.add(title_label)

        difficulty_info_label = arcade.gui.UILabel(
            text=f"Текущая сложность: {self.get_difficulty_text()}",
            font_size=settings.LABEL_FONT_SIZE,
            text_color=arcade.color.LIGHT_GRAY,
            width=settings.SETTINGS_PANEL_WIDTH
        )
        main_box.add(difficulty_info_label)

        buttons_box = arcade.gui.UIBoxLayout(vertical=True, space_between=15)

        change_difficulty_button = arcade.gui.UIFlatButton(
            text="Изменить уровень сложности",
            width=settings.SETTINGS_PANEL_WIDTH - 20,
            height=settings.BUTTON_HEIGHT
        )
        change_difficulty_button.style = {
            "normal": {
                "bg_color": arcade.color.DARK_GRAY,
                "border_color": arcade.color.WHITE,
                "border_width": 2
            },
            "hover": {
                "bg_color": arcade.color.GRAY,
                "border_color": arcade.color.WHITE,
                "border_width": 2
            },
            "press": {
                "bg_color": arcade.color.BLUE,
                "border_color": arcade.color.WHITE,
                "border_width": 2
            }
        }
        change_difficulty_button.on_click = self.on_change_difficulty_click
        buttons_box.add(change_difficulty_button)

        if self.difficulty in (self.DIFFICULTY_EASY, self.DIFFICULTY_MEDIUM, self.DIFFICULTY_HARD):
            save_text = "Сохранить игру"
            if self.difficulty == self.DIFFICULTY_HARD:
                if self.hard_save_used:
                    save_text = "Сохранить игру (использовано)"
                else:
                    save_text = "Сохранить игру (1 раз на уровень)"

            save_button = arcade.gui.UIFlatButton(
                text=save_text,
                width=settings.SETTINGS_PANEL_WIDTH - 20,
                height=settings.BUTTON_HEIGHT
            )
            save_button.style = {
                "normal": {
                    "bg_color": arcade.color.DARK_GREEN if not (self.difficulty == self.DIFFICULTY_HARD and self.hard_save_used) else arcade.color.DARK_GRAY,
                    "border_color": arcade.color.WHITE,
                    "border_width": 2
                },
                "hover": {
                    "bg_color": arcade.color.GREEN if not (self.difficulty == self.DIFFICULTY_HARD and self.hard_save_used) else arcade.color.GRAY,
                    "border_color": arcade.color.WHITE,
                    "border_width": 2
                },
                "press": {
                    "bg_color": arcade.color.DARK_GREEN if not (self.difficulty == self.DIFFICULTY_HARD and self.hard_save_used) else arcade.color.DARK_GRAY,
                    "border_color": arcade.color.WHITE,
                    "border_width": 2
                }
            }
            save_button.on_click = self.on_save_game_click
            buttons_box.add(save_button)

        menu_button = arcade.gui.UIFlatButton(
            text="Выйти в главное меню",
            width=settings.SETTINGS_PANEL_WIDTH - 20,
            height=settings.BUTTON_HEIGHT
        )
        menu_button.style = {
            "normal": {
                "bg_color": arcade.color.DARK_RED,
                "border_color": arcade.color.WHITE,
                "border_width": 2
            },
            "hover": {
                "bg_color": arcade.color.RED,
                "border_color": arcade.color.WHITE,
                "border_width": 2
            },
            "press": {
                "bg_color": arcade.color.DARK_RED,
                "border_color": arcade.color.WHITE,
                "border_width": 2
            }
        }
        menu_button.on_click = self.on_return_to_menu_click
        buttons_box.add(menu_button)

        main_box.add(buttons_box)

        anchor_layout = arcade.gui.UIAnchorLayout()
        anchor_layout.add(
            child=main_box,
            anchor_x="center_x",
            anchor_y="center_y"
        )
        self.pause_manager.add(anchor_layout)

    def get_difficulty_text(self):
        if self.difficulty == self.DIFFICULTY_EASY:
            return "Легкий"
        elif self.difficulty == self.DIFFICULTY_MEDIUM:
            return "Средний"
        else:
            return "Сложный"

    def on_change_difficulty_click(self, event):
        if self.window:
            from windows.difficulty_dialog import DifficultyDialog
            dialog = DifficultyDialog(self.difficulty, self)
            self.window.show_view(dialog)

    def on_save_game_click(self, event):
        if self.save_game():
            print("Игра сохранена!")
        else:
            print("Ошибка сохранения игры!")

    def on_return_to_menu_click(self, event):
        self.stop_game_music()
        if self.window:
            from windows.start_window import StartWindow
            start_view = StartWindow()
            start_view.play_main_music()
            self.window.show_view(start_view)

    def on_resume_click(self, event):
        self.show_pause_menu = False
        self.pause_manager.disable()
        self.manager.disable()

    def on_show_view(self):
        self.manager.disable()
        arcade.set_background_color(ProjectSettings.BACKGROUND_COLOR)

        if self.window:
            if self.camera is None:
                self.camera = arcade_camera.Camera2D()
            self.screen_width = self.window.width
            self.screen_height = self.window.height
            tile_size = self.tile_size
            if self.player and self.player.pos:
                start_cam_x = self.player.pos[0] * tile_size + tile_size // 2
                start_cam_y = self.player.pos[1] * tile_size + tile_size // 2
                self.camera.position = (start_cam_x, start_cam_y)
            self.apply_frame_limit()

            if hasattr(self, 'game_music_player') and self.game_music_player:
                try:
                    self.game_music_player.volume = self.music_volume
                except Exception:
                    pass

        self.show_pause_menu = False
        self.pause_manager.disable()

    def on_hide_view(self):
        self.manager.disable()
        self.pause_manager.disable()

    def on_draw(self):
        self.clear()

        if self.camera:
            self.camera.use()
            if not self.show_pause_menu:
                arcade.set_background_color(
                    ProjectSettings.BACKGROUND_COLOR)
                self.draw_map()

        if self.window:
            try:
                pyglet.gl.glViewport(
                    0, 0, self.window.width, self.window.height)
                pyglet.gl.glMatrixMode(pyglet.gl.GL_PROJECTION)
                pyglet.gl.glLoadIdentity()
                pyglet.gl.glOrtho(0, self.window.width, 0,
                                  self.window.height, -1, 1)
                pyglet.gl.glMatrixMode(pyglet.gl.GL_MODELVIEW)
                pyglet.gl.glLoadIdentity()
            except Exception:
                pass

        if self.show_pause_menu:
            arcade.set_background_color(arcade.color.DARK_GRAY)
            self.pause_manager.draw()

    def on_update(self, delta_time):
        if self.window:
            current_width = self.window.width
            current_height = self.window.height
            if current_width != self.screen_width or current_height != self.screen_height:
                self.screen_width = current_width
                self.screen_height = current_height
                if self.camera is None:
                    self.camera = arcade_camera.Camera2D()
                self.apply_frame_limit()

        if hasattr(self, 'game_music_player') and self.game_music_player:
            try:
                if hasattr(self.game_music_player, 'volume'):
                    self.game_music_player.volume = self.music_volume
            except Exception:
                pass

        if self.show_pause_menu:
            self.pause_manager.on_update(delta_time)

        self._update_player_state_from_keys()

        # Handle slippery movement for medium and hard difficulty
        if self.difficulty in (self.DIFFICULTY_MEDIUM, self.DIFFICULTY_HARD):
            # Calculate desired movement direction
            desired_dx = (1 if self.move_hold["right"] else 0) - \
                (1 if self.move_hold["left"] else 0)
            desired_dy = (1 if self.move_hold["up"] else 0) - \
                (1 if self.move_hold["down"] else 0)

            if desired_dx != 0 and desired_dy != 0:
                desired_dx = 0
                desired_dy = 0

            # Apply acceleration to velocity
            self.velocity_x += desired_dx * self.acceleration
            self.velocity_y += desired_dy * self.acceleration

            # Apply friction to velocity (this simulates sliding)
            self.velocity_x *= self.friction
            self.velocity_y *= self.friction

            # Limit max velocity
            max_velocity = 0.5  # Lower max velocity for slower base movement
            self.velocity_x = max(-max_velocity,
                                  min(max_velocity, self.velocity_x))
            self.velocity_y = max(-max_velocity,
                                  min(max_velocity, self.velocity_y))

            # Convert velocity to integer movement for tile-based movement
            move_x = int(round(self.velocity_x))
            move_y = int(round(self.velocity_y))

            # Only move if we have significant velocity
            if abs(move_x) >= 0.5 or abs(move_y) >= 0.5:
                # Try to move based on velocity
                if move_x != 0 or move_y != 0:
                    # Try to move in x direction first, then y if x fails
                    if move_x != 0:
                        if self.can_move_to(self.player.pos[0] + move_x, self.player.pos[1]):
                            self.try_move_player(move_x, 0)
                    if move_y != 0:
                        if self.can_move_to(self.player.pos[0], self.player.pos[1] + move_y):
                            self.try_move_player(0, move_y)
        else:
            # Original movement logic for easy mode
            dx = (1 if self.move_hold["right"] else 0) - \
                (1 if self.move_hold["left"] else 0)
            dy = (1 if self.move_hold["up"] else 0) - \
                (1 if self.move_hold["down"] else 0)

            if dx != 0 and dy != 0:
                dx = 0
                dy = 0

            self.move_timer -= delta_time
            if self.move_timer <= 0:
                if dx != 0 or dy != 0:
                    self.try_move_player(dx, dy)
                    self.move_timer = self.move_cooldown

        if self.camera and self.window and self.player and self.dungeon_map:
            tile_size = self.tile_size
            # Pre-calculate values to avoid repeated calculations
            player_pos_x, player_pos_y = self.player.pos[0], self.player.pos[1]
            map_pixel_w = self.dungeon_map.map_width * tile_size
            map_pixel_h = self.dungeon_map.map_height * tile_size
            target_x = player_pos_x * tile_size + tile_size // 2
            target_y = player_pos_y * tile_size + tile_size // 2

            # Плавная интерполяция позиции спрайта игрока
            if self.move_anim_time > 0:
                self.move_anim_time = max(0.0, self.move_anim_time - delta_time)
                t = 1.0 - (self.move_anim_time / max(0.0001, self.move_anim_duration))
                # smoothstep
                t = t * t * (3 - 2 * t)
                sx, sy = self.move_anim_start
                tx, ty = self.move_anim_target
                self.player.draw_pos[0] = sx + (tx - sx) * t
                self.player.draw_pos[1] = sy + (ty - sy) * t
            else:
                px, py = self.player.draw_pos
                player_lerp = min(0.25, delta_time * 10.0)
                self.player.draw_pos[0] = px + (target_x - px) * player_lerp
                self.player.draw_pos[1] = py + (target_y - py) * player_lerp

            self.player.update_animation(delta_time)

            # Optimize camera movement
            half_w = self.screen_width // 2
            half_h = self.screen_height // 2
            # Constrain target position to map bounds
            constrained_target_x = max(
                half_w, min(map_pixel_w - half_w, target_x))
            constrained_target_y = max(
                half_h, min(map_pixel_h - half_h, target_y))
            cur_x, cur_y = self.camera.position
            smoothing = min(0.2, delta_time * 6.0)
            new_x = cur_x + (constrained_target_x - cur_x) * smoothing
            new_y = cur_y + (constrained_target_y - cur_y) * smoothing
            # Ensure camera stays within bounds after smoothing
            final_x = max(half_w, min(map_pixel_w - half_w, new_x))
            final_y = max(half_h, min(map_pixel_h - half_h, new_y))
            self.camera.position = (final_x, final_y)

    def draw_minimap(self):
        """Draw a small minimap showing the dungeon layout and player position"""
        if not self.dungeon_map or not self.player:
            return

        # Используем отдельную камеру для UI, чтобы не зависеть от основного смещения
        if self.ui_camera:
            self.ui_camera.use()

        # Minimap parameters
        max_dim = max(self.dungeon_map.map_width, self.dungeon_map.map_height)
        # Увеличиваем миникарту: целевой размер ~420 px по большей стороне
        minimap_scale = max(2.0, min(5.0, 420 / max(1, max_dim)))
        minimap_width = int(self.dungeon_map.map_width * minimap_scale)
        minimap_height = int(self.dungeon_map.map_height * minimap_scale)
        # Position minimap in top-right corner with margins
        minimap_x = self.window.width - minimap_width - 15
        minimap_y = self.window.height - 15

        # Draw minimap background
        arcade.draw_lrbt_rectangle_filled(minimap_x, minimap_x + minimap_width,
                                          minimap_y - minimap_height, minimap_y,
                                          # Semi-transparent black background
                                          (0, 0, 0, 180))

        # Draw dungeon layout on minimap (только видимые или исследованные для оптимизации)
        use_grid = self.visibility_grid is not None
        use_explored = self.explored_grid is not None
        for y in range(self.dungeon_map.map_height):
            for x in range(self.dungeon_map.map_width):
                tile_value = self.dungeon_map.get_tile_value(x, y)
                if tile_value is None:
                    continue

                visible = False
                explored = False
                if use_grid:
                    visible = self.visibility_grid[y][x]
                else:
                    visible = (x, y) in self.visible_tiles
                if use_explored:
                    explored = self.explored_grid[y][x]
                else:
                    explored = visible or (x, y) in getattr(self, "explored_tiles", set())

                if not visible and not explored:
                    continue

                mini_x = minimap_x + x * minimap_scale
                mini_y = minimap_y - y * minimap_scale  # Flip Y axis

                if visible:
                    if tile_value == 0:
                        color = arcade.color.LIGHT_GRAY
                    elif tile_value == 1:
                        color = arcade.color.DIM_GRAY
                    elif tile_value == 2:
                        color = arcade.color.LIGHT_BLUE
                    elif tile_value == 3:
                        color = (220, 90, 60)
                    else:
                        color = arcade.color.WHITE
                else:
                    color = (50, 50, 70, 170)

                arcade.draw_lrbt_rectangle_filled(mini_x,
                                                  mini_x + minimap_scale,
                                                  mini_y - minimap_scale,
                                                  mini_y, color)

        # Draw player position on minimap
        player_mini_x = minimap_x + self.player.pos[0] * minimap_scale
        player_mini_y = minimap_y - \
            self.player.pos[1] * minimap_scale  # Flip Y axis
        # Плавное смещение индикатора игрока
        if self.minimap_player_draw_pos is None:
            self.minimap_player_draw_pos = (
                float(player_mini_x), float(player_mini_y))
        else:
            lerp = 0.25
            cur_x, cur_y = self.minimap_player_draw_pos
            cur_x += (player_mini_x - cur_x) * lerp
            cur_y += (player_mini_y - cur_y) * lerp
            self.minimap_player_draw_pos = (cur_x, cur_y)
            player_mini_x, player_mini_y = cur_x, cur_y
        arcade.draw_circle_filled(
            player_mini_x, player_mini_y, minimap_scale * 0.8, arcade.color.YELLOW)

    def _update_player_state_from_keys(self):
        dx = (1 if self.move_hold["right"] else 0) - \
            (1 if self.move_hold["left"] else 0)
        dy = (1 if self.move_hold["up"] else 0) - \
            (1 if self.move_hold["down"] else 0)

        if dx != 0 and dy != 0:
            dx = 0
            dy = 0

        if self.player:
            if dx != 0 or dy != 0:
                if dy != 0:
                    if dy > 0:
                        self.player.facing = 'back'
                    else:
                        self.player.facing = 'front'
                else:
                    if dx > 0:
                        self.player.facing = 'right'
                    else:
                        self.player.facing = 'left'

                if self.is_running:
                    self.player.set_state('running')
                else:
                    self.player.set_state('walking')
            else:
                self.player.set_state('idle')

    def apply_frame_limit(self):
        if not self.window:
            return
        limit = str(self.frame_limit or "").lower()
        if limit == "vsync":
            try:
                self.window.set_vsync(True)
            except Exception:
                pass
            try:
                self.window.set_update_rate(None)
            except Exception:
                pass
        elif limit == "unlimited":
            try:
                self.window.set_vsync(False)
            except Exception:
                pass
            try:
                self.window.set_update_rate(None)
            except Exception:
                pass
        else:
            try:
                hz = float(limit)
            except Exception:
                hz = 240.0
            hz = max(240.0, hz)
            try:
                self.window.set_vsync(False)
            except Exception:
                pass
            try:
                self.window.set_update_rate(1.0 / hz)
            except Exception:
                pass

    def on_key_press(self, key, modifiers):
        if key == arcade.key.ESCAPE:
            if self.show_pause_menu:
                self.show_pause_menu = False
                self.pause_manager.disable()
                self.manager.disable()
            else:
                self.show_pause_menu = True
                self.manager.disable()
                arcade.set_background_color(arcade.color.DARK_GRAY)
                self.setup_pause_menu()
                self.pause_manager.enable()
            return

        if self.show_pause_menu:
            return

        if key in (arcade.key.W, arcade.key.UP):
            self.move_hold["up"] = True
            self._update_player_state_from_keys()
        elif key in (arcade.key.S, arcade.key.DOWN):
            self.move_hold["down"] = True
            self._update_player_state_from_keys()
        elif key in (arcade.key.A, arcade.key.LEFT):
            self.move_hold["left"] = True
            self._update_player_state_from_keys()
        elif key in (arcade.key.D, arcade.key.RIGHT):
            self.move_hold["right"] = True
            self._update_player_state_from_keys()
        elif key in (arcade.key.LSHIFT, arcade.key.RSHIFT):
            self.is_running = True
            if self.player and (self.move_hold["up"] or self.move_hold["down"] or
                                self.move_hold["left"] or self.move_hold["right"]):
                self.player.set_state('running')
        elif key in (arcade.key.LSHIFT, arcade.key.RSHIFT):
            self.is_running = True
            if self.player and (self.move_hold["up"] or self.move_hold["down"] or
                                self.move_hold["left"] or self.move_hold["right"]):
                self.player.set_state('running')
        elif key == arcade.key.SPACE:
            dx = (1 if self.move_hold["right"] else 0) - \
                (1 if self.move_hold["left"] else 0)
            dy = (1 if self.move_hold["up"] else 0) - \
                (1 if self.move_hold["down"] else 0)
            if dx != 0 or dy != 0:
                self.try_move_player(dx, dy)
                self.move_timer = self.move_cooldown

    def on_key_release(self, key, modifiers):
        if key in (arcade.key.W, arcade.key.UP):
            self.move_hold["up"] = False
        elif key in (arcade.key.S, arcade.key.DOWN):
            self.move_hold["down"] = False
        elif key in (arcade.key.A, arcade.key.LEFT):
            self.move_hold["left"] = False
        elif key in (arcade.key.D, arcade.key.RIGHT):
            self.move_hold["right"] = False
        elif key in (arcade.key.LSHIFT, arcade.key.RSHIFT):
            self.is_running = False
            if self.player:
                if self.move_hold["up"] or self.move_hold["down"] or \
                   self.move_hold["left"] or self.move_hold["right"]:
                    self.player.set_state('walking')
                else:
                    self.player.set_state('idle')

    def on_mouse_press(self, x, y, button, modifiers):
        if self.show_pause_menu:
            return

        if button == arcade.MOUSE_BUTTON_LEFT:
            if self.player and not self.player.is_attacking:
                self.player.move_hold = self.move_hold
                self.player.is_running = self.is_running
                self.player.attack()

    def try_move_player(self, dx, dy):
        if not self.player or not self.dungeon_map:
            return

        prev_room_id = self.dungeon_map.get_room_id(
            self.player.pos[0], self.player.pos[1])
        new_x = self.player.pos[0] + dx
        new_y = self.player.pos[1] + dy
        if 0 <= new_x < self.dungeon_map.map_width and 0 <= new_y < self.dungeon_map.map_height:
            if self.dungeon_map.is_walkable(new_x, new_y):
                # Запускаем анимацию перемещения
                tile_size = self.tile_size
                if hasattr(self.player, "draw_pos"):
                    self.move_anim_start = list(self.player.draw_pos)
                else:
                    self.move_anim_start = [self.player.pos[0] * tile_size + tile_size // 2,
                                            self.player.pos[1] * tile_size + tile_size // 2]
                target_px = new_x * tile_size + tile_size // 2
                target_py = new_y * tile_size + tile_size // 2
                self.move_anim_target = [target_px, target_py]
                self.move_anim_time = self.move_anim_duration

                self.player.move(dx, dy)
                # Обновляем направление и состояние сразу, чтобы анимация не залипала при смене направления
                if dy != 0:
                    self.player.facing = 'back' if dy > 0 else 'front'
                elif dx != 0:
                    self.player.facing = 'right' if dx > 0 else 'left'
                self.player.set_state('running' if self.is_running else 'walking')

                room_id = self.dungeon_map.get_room_id(new_x, new_y)

                self.update_visibility()

                if self.save_point_pos and not self.save_point_used:
                    save_x, save_y = self.save_point_pos
                    if new_x == save_x and new_y == save_y:
                        if self.save_game():
                            self.save_point_used = True
                            print("Игра сохранена через точку сохранения!")

                if self.dungeon_map.exit_room_idx is not None:
                    if room_id == self.dungeon_map.exit_room_idx and not self.exit_music_played:
                        self.play_suspense_music()
                        self.exit_music_played = True

                if self.dungeon_map.exit_pos and (new_x, new_y) == self.dungeon_map.exit_pos:
                    self.advance_level()

                if self.dungeon_map.exit_room_idx is not None:
                    if prev_room_id == self.dungeon_map.exit_room_idx and room_id != self.dungeon_map.exit_room_idx:
                        self.stop_suspense_music()
                        self.exit_music_played = False
                        self.play_game_music()

    def can_move_to(self, x, y):
        """Check if player can move to the specified coordinates"""
        if not self.dungeon_map:
            return False
        if 0 <= x < self.dungeon_map.map_width and 0 <= y < self.dungeon_map.map_height:
            return self.dungeon_map.is_walkable(x, y)
        return False

    def advance_level(self):
        self.level += 1
        self.visible_tiles.clear()
        self.explored_tiles.clear()
        self.stop_suspense_music()
        self.exit_music_played = False
        if self.difficulty == self.DIFFICULTY_HARD:
            self.hard_save_used = False
        self.save_point_used = False
        self.map_payload = None
        self.spawn_corner = None
        self.explored_grid = None
        self.visibility_grid = None
        self.setup_game()
        self.play_game_music()

    def play_suspense_music(self):
        path = self.find_music_file("suspense-horror-music-loop-382813.mp3")
        if not path:
            return
        try:
            self.stop_game_music()
        except Exception:
            pass
        self.suspense_player, _ = play_loop(path, self.music_volume)

    def stop_suspense_music(self):
        stop_player(self.suspense_player)
        self.suspense_player = None

    def draw_map(self):
        if not self.dungeon_map or not self.camera:
            return

        tile_size = self.tile_size
        cam_x, cam_y = self.camera.position
        half_w = (self.window.width // 2) if self.window else 0
        half_h = (self.window.height // 2) if self.window else 0

        view_left = max(0, int((cam_x - half_w) / tile_size) - 1)
        view_right = min(self.dungeon_map.map_width,
                         int((cam_x + half_w) / tile_size) + 2)
        view_bottom = max(0, int((cam_y - half_h) / tile_size) - 1)
        view_top = min(self.dungeon_map.map_height,
                       int((cam_y + half_h) / tile_size) + 2)

        # Only calculate view bounds if needed
        batches = {
            'visible_wall': [],
            'visible_floor': [],
            'visible_floor_textured': [],
            'visible_exit': [],
            'seen_wall': [],
            'seen_floor': [],
            'seen_exit': []
        }

        use_grid = self.visibility_grid is not None
        use_explored = self.explored_grid is not None

        view_bottom_clamped = max(0, view_bottom)
        view_top_clamped = min(self.dungeon_map.map_height, view_top)
        view_left_clamped = max(0, view_left)
        view_right_clamped = min(self.dungeon_map.map_width, view_right)

        # Pre-calculate commonly used values
        tile_size_float = float(tile_size)

        for y in range(view_bottom_clamped, view_top_clamped):
            vis_row = self.visibility_grid[y] if use_grid else None
            screen_y = y * tile_size_float
            bottom = screen_y
            top = screen_y + tile_size_float

            for x in range(view_left_clamped, view_right_clamped):
                if use_grid:
                    visible = vis_row[x]
                else:
                    visible = (x, y) in self.visible_tiles

                explored = False
                if use_explored:
                    explored = self.explored_grid[y][x]
                else:
                    explored = visible or (x, y) in getattr(self, "explored_tiles", set())

                if not visible and not explored:
                    continue

                value = self.dungeon_map.get_tile_value(x, y)
                if value is None:  # Skip invalid tiles
                    continue

                screen_x = x * tile_size_float
                left = screen_x
                right = screen_x + tile_size_float

                if value == 1:
                    key = 'visible_wall' if visible else 'seen_wall'
                    batches[key].append((left, right, bottom, top))
                elif value == 3:
                    key = 'visible_exit' if visible else 'seen_exit'
                    batches[key].append((left, right, bottom, top))
                else:
                    if self.dungeon_map.floor_texture:
                        key = 'visible_floor_textured' if visible else 'seen_floor'
                        batches[key].append(
                            (left, right, bottom, top, x, y))
                    else:
                        key = 'visible_floor' if visible else 'seen_floor'
                        batches[key].append(
                            (left, right, bottom, top))

        # Рисуем пол простыми прямоугольниками — быстрее, чем создавать спрайты
        if (batches['visible_floor_textured'] or batches['seen_floor']) and self.dungeon_map:
            color_floor_vis = arcade.color.LIGHT_GRAY
            color_floor_seen = (180, 180, 200)
            for left, right, bottom, top, tile_x, tile_y in batches['visible_floor_textured']:
                arcade.draw_lrbt_rectangle_filled(
                    left, right, bottom, top, color_floor_vis)
            for left, right, bottom, top, tile_x, tile_y in batches['seen_floor']:
                arcade.draw_lrbt_rectangle_filled(
                    left, right, bottom, top, color_floor_seen)

        color_batches = {
            arcade.color.DIM_GRAY: batches['visible_wall'],
            arcade.color.LIGHT_GRAY: batches['visible_floor'],
            (180, 60, 40): batches['visible_exit'],
            (110, 110, 120): batches['seen_wall'],
            (140, 140, 160): batches['seen_exit'],
        }

        for color, rects in color_batches.items():
            if rects:
                for left, right, bottom, top in rects:
                    arcade.draw_lrbt_rectangle_filled(
                        left, right, bottom, top, color)

        # Fog of war только в пределах видимой области экрана
        if self.visibility_grid:
            for y in range(view_bottom_clamped, view_top_clamped):
                vis_row = self.visibility_grid[y]
                exp_row = self.explored_grid[y] if self.explored_grid else None
                screen_y = y * tile_size
                bottom = screen_y
                top = screen_y + tile_size
                for x in range(view_left_clamped, view_right_clamped):
                    if vis_row[x]:
                        continue
                    explored = exp_row[x] if exp_row else False
                    screen_x = x * tile_size
                    # Прям чёрный туман войны
                    fog_color = (0, 0, 0, 255)
                    arcade.draw_lrbt_rectangle_filled(
                        screen_x, screen_x + tile_size, bottom, top, fog_color)

        if self.save_point_pos:
            save_x, save_y = self.save_point_pos
            if use_grid and self.dungeon_map and 0 <= save_x < self.dungeon_map.map_width and 0 <= save_y < self.dungeon_map.map_height:
                if self.visibility_grid[save_y][save_x] or (self.explored_grid and self.explored_grid[save_y][save_x]):
                    save_screen_x = save_x * tile_size
                    save_screen_y = save_y * tile_size
                    if not self.save_point_used:
                        arcade.draw_circle_filled(
                            save_screen_x + tile_size / 2,
                            save_screen_y + tile_size / 2,
                            tile_size * 0.3,
                            arcade.color.CYAN
                        )
                    else:
                        arcade.draw_circle_filled(
                            save_screen_x + tile_size / 2,
                            save_screen_y + tile_size / 2,
                            tile_size * 0.3,
                            arcade.color.DARK_GRAY
                        )
            elif not use_grid and (save_x, save_y) in self.visible_tiles:
                save_screen_x = save_x * tile_size
                save_screen_y = save_y * tile_size
                if not self.save_point_used:
                    arcade.draw_circle_filled(
                        save_screen_x + tile_size / 2,
                        save_screen_y + tile_size / 2,
                        tile_size * 0.3,
                        arcade.color.CYAN
                    )
                else:
                    arcade.draw_circle_filled(
                        save_screen_x + tile_size / 2,
                        save_screen_y + tile_size / 2,
                        tile_size * 0.3,
                        arcade.color.DARK_GRAY
                    )

        if self.player:
            self.player.draw()

        # Draw minimap in top-right corner
        self.draw_minimap()

    def can_move_to(self, x, y):
        """Check if player can move to the specified coordinates"""
        if not self.dungeon_map:
            return False
        if 0 <= x < self.dungeon_map.map_width and 0 <= y < self.dungeon_map.map_height:
            return self.dungeon_map.is_walkable(x, y)
        return False
