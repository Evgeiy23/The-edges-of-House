import arcade
import arcade.gui
import arcade.camera as arcade_camera
import pyglet
import os
import json
from project import ProjectSettings
from utils import get_config_path, get_savegame_path
from game.logic.music import find_music_file, play_loop, stop_player
from game.logic.map.generation import generate_dungeon


class GameWindow(arcade.View):
    DIFFICULTY_EASY = ProjectSettings.Game.DIFFICULTY_EASY
    DIFFICULTY_MEDIUM = ProjectSettings.Game.DIFFICULTY_MEDIUM
    DIFFICULTY_HARD = ProjectSettings.Game.DIFFICULTY_HARD

    def __init__(self, difficulty=None, load_save=False):
        super().__init__()

        self.screen_width = 0
        self.screen_height = 0
        self.map_width = 0
        self.map_height = 0
        self.tile_size = ProjectSettings.Game.TILE_SIZE

        self.map_data = []
        self.room_tile_map = {}
        self.rooms = []
        self.halls = []
        self.player_pos = [0, 0]
        self.player_draw_pos = [0.0, 0.0]
        self.visible_tiles = set()
        self.explored_tiles = set()
        self.revealed_rooms = set()
        self.exit_pos = None
        self.exit_room_idx = None
        self.level = 1
        self.suspense_player = None
        self.camera = None
        self.corridor_tiles = set()
        self.move_hold = {"up": False, "down": False,
                          "left": False, "right": False}
        self.move_cooldown = 0.1
        self.move_timer = 0.0
        self.exit_music_played = False
        self.frame_limit = ProjectSettings.Game.DEFAULT_FRAME_LIMIT

        self.manager = arcade.gui.UIManager()
        self.manager.disable()

        self.pause_manager = arcade.gui.UIManager()
        self.pause_manager.disable()

        self.music_volume = 1.0
        self.sound_volume = 1.0

        self.game_music_sound = None
        self.game_music_player = None

        self.difficulty = difficulty or self.DIFFICULTY_EASY
        self.show_pause_menu = False

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
            base_width = game_cfg.SCREEN_WIDTH // game_cfg.TILE_SIZE
            base_height = game_cfg.SCREEN_HEIGHT // game_cfg.TILE_SIZE

            self.map_width = base_width * game_cfg.MAP_WIDTH_MULTIPLIER
            self.map_height = base_height * game_cfg.MAP_HEIGHT_MULTIPLIER

            (self.map_data, self.rooms, self.room_tile_map,
             self.corridor_tiles, self.exit_pos, self.exit_room_idx) = generate_dungeon(
                self.map_width, self.map_height, game_cfg)

            self.halls = []
            self.visible_tiles = set()
            self.explored_tiles = set()
            self.revealed_rooms = set()
            self.exit_music_played = False

            self.place_player()
            self.update_visibility()

            if self.camera is None and hasattr(self, 'window') and self.window:
                self.camera = arcade_camera.Camera2D()
                tile_size = self.tile_size
                if self.player_pos and len(self.player_pos) >= 2:
                    start_cam_x = self.player_pos[0] * \
                        tile_size + tile_size // 2
                    start_cam_y = self.player_pos[1] * \
                        tile_size + tile_size // 2
                    self.camera.position = (start_cam_x, start_cam_y)
        except Exception as e:
            print(f"Ошибка при генерации карты: {e}")
            import traceback
            traceback.print_exc()
            self.map_width = 32
            self.map_height = 24
            self.map_data = [
                [1 for _ in range(self.map_width)] for _ in range(self.map_height)]
            self.rooms = []
            self.room_tile_map = {}
            self.corridor_tiles = set()
            self.exit_pos = None
            self.exit_room_idx = None
            self.place_player()
            self.update_visibility()

            if self.camera is None and hasattr(self, 'window') and self.window:
                self.camera = arcade_camera.Camera2D()
                tile_size = self.tile_size
                if self.player_pos and len(self.player_pos) >= 2:
                    start_cam_x = self.player_pos[0] * \
                        tile_size + tile_size // 2
                    start_cam_y = self.player_pos[1] * \
                        tile_size + tile_size // 2
                    self.camera.position = (start_cam_x, start_cam_y)

    def generate_rooms_and_halls(self):
        return generate_dungeon(self.map_width, self.map_height, ProjectSettings.Game)

    def connect_rooms(self, room_a, room_b, is_hall=False):
        return

    def place_player(self):
        center_x = self.map_width // 2
        start_y = self.map_height // 2

        player_placed = False
        for y in range(max(1, start_y - 5), min(self.map_height - 1, start_y + 5)):
            for x in range(max(1, center_x - 5), min(self.map_width - 1, center_x + 5)):
                if self.map_data[y][x] in (0, 2):
                    self.player_pos = [x, y]
                    self.player_draw_pos = [
                        x * self.tile_size + self.tile_size / 2,
                        y * self.tile_size + self.tile_size / 2
                    ]
                    self.visible_tiles.add((x, y))
                    self.explored_tiles.add((x, y))
                    player_placed = True
                    break
            if player_placed:
                break

        if not player_placed:
            self.player_pos = [center_x, start_y]
            self.player_draw_pos = [
                center_x * self.tile_size + self.tile_size / 2,
                start_y * self.tile_size + self.tile_size / 2
            ]
            if self.map_data[start_y][center_x] == 1:
                self.map_data[start_y][center_x] = 0
            self.visible_tiles.add((center_x, start_y))
            self.explored_tiles.add((center_x, start_y))

    def update_visibility(self):
        self.visible_tiles.clear()

        if self.corridor_tiles:
            self.visible_tiles.update(self.corridor_tiles)
            self.explored_tiles.update(self.corridor_tiles)

        if self.revealed_rooms and self.rooms:
            for idx in self.revealed_rooms:
                if 0 <= idx < len(self.rooms):
                    r = self.rooms[idx]
                    room_tiles = {
                        (rx, ry)
                        for ry in range(r["y1"], r["y2"])
                        for rx in range(r["x1"], r["x2"])
                    }
                    self.visible_tiles.update(room_tiles)
                    self.explored_tiles.update(room_tiles)

    def save_game(self):
        if self.difficulty != self.DIFFICULTY_EASY:
            return False

        save_file = get_savegame_path()
        try:
            game_data = {
                "level": self.level,
                "player_pos": self.player_pos,
                "player_draw_pos": self.player_draw_pos,
                "revealed_rooms": list(self.revealed_rooms),
                "visible_tiles": list(self.visible_tiles),
                "explored_tiles": list(self.explored_tiles),
                "map_data": self.map_data,
                "rooms": self.rooms,
                "room_tile_map": {f"{k[0]},{k[1]}": v for k, v in self.room_tile_map.items()},
                "corridor_tiles": list(self.corridor_tiles),
                "exit_pos": self.exit_pos,
                "exit_room_idx": self.exit_room_idx,
                "exit_music_played": self.exit_music_played,
                "music_volume": self.music_volume,
                "sound_volume": self.sound_volume,
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
                        self.player_pos = game_data.get("player_pos", [0, 0])
                        self.player_draw_pos = game_data.get(
                            "player_draw_pos", [0.0, 0.0])
                        map_data_loaded = game_data.get("map_data", [])
                        if map_data_loaded:
                            self.map_data = map_data_loaded
                            self.map_height = len(self.map_data)
                            self.map_width = len(
                                self.map_data[0]) if self.map_height > 0 else 0
                        else:
                            return False
                        self.revealed_rooms = set(
                            game_data.get("revealed_rooms", []))
                        self.visible_tiles = set(
                            [tuple(t) for t in game_data.get("visible_tiles", [])])
                        self.explored_tiles = set(
                            [tuple(t) for t in game_data.get("explored_tiles", [])])
                        self.map_data = game_data.get("map_data", [])
                        self.rooms = game_data.get("rooms", [])
                        self.room_tile_map = {
                            tuple(map(int, k.split(","))): v
                            for k, v in game_data.get("room_tile_map", {}).items()
                        }
                        self.corridor_tiles = set(
                            [tuple(t) for t in game_data.get("corridor_tiles", [])])
                        self.exit_pos = tuple(
                            game_data.get("exit_pos")) if game_data.get("exit_pos") else None
                        self.exit_room_idx = game_data.get(
                            "exit_room_idx", None)
                        self.exit_music_played = game_data.get(
                            "exit_music_played", False)
                        self.music_volume = game_data.get(
                            "music_volume", self.music_volume)
                        self.sound_volume = game_data.get(
                            "sound_volume", self.sound_volume)
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

        if self.difficulty == self.DIFFICULTY_EASY:
            save_button = arcade.gui.UIFlatButton(
                text="Сохранить игру",
                width=settings.SETTINGS_PANEL_WIDTH - 20,
                height=settings.BUTTON_HEIGHT
            )
            save_button.style = {
                "normal": {
                    "bg_color": arcade.color.DARK_GREEN,
                    "border_color": arcade.color.WHITE,
                    "border_width": 2
                },
                "hover": {
                    "bg_color": arcade.color.GREEN,
                    "border_color": arcade.color.WHITE,
                    "border_width": 2
                },
                "press": {
                    "bg_color": arcade.color.DARK_GREEN,
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
            if self.player_pos and len(self.player_pos) >= 2:
                start_cam_x = self.player_pos[0] * tile_size + tile_size // 2
                start_cam_y = self.player_pos[1] * tile_size + tile_size // 2
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

        self.move_timer -= delta_time
        if self.move_timer <= 0:
            dx = (1 if self.move_hold["right"] else 0) - \
                (1 if self.move_hold["left"] else 0)
            dy = (1 if self.move_hold["up"] else 0) - \
                (1 if self.move_hold["down"] else 0)
            if dx != 0 or dy != 0:
                self.try_move_player(dx, dy)
                self.move_timer = self.move_cooldown

        if self.camera and self.window:
            tile_size = self.tile_size
            map_pixel_w = self.map_width * tile_size
            map_pixel_h = self.map_height * tile_size
            target_x = self.player_pos[0] * tile_size + tile_size // 2
            target_y = self.player_pos[1] * tile_size + tile_size // 2
            px, py = self.player_draw_pos
            player_lerp = min(0.35, delta_time * 12.0)
            self.player_draw_pos[0] = px + (target_x - px) * player_lerp
            self.player_draw_pos[1] = py + (target_y - py) * player_lerp

            half_w = self.screen_width // 2
            half_h = self.screen_height // 2
            cam_x = max(half_w, min(map_pixel_w - half_w, target_x))
            cam_y = max(half_h, min(map_pixel_h - half_h, target_y))
            cur_x, cur_y = self.camera.position
            smoothing = min(0.25, delta_time * 8.0)
            new_x = cur_x + (cam_x - cur_x) * smoothing
            new_y = cur_y + (cam_y - cur_y) * smoothing
            new_x = max(half_w, min(map_pixel_w - half_w, new_x))
            new_y = max(half_h, min(map_pixel_h - half_h, new_y))
            self.camera.position = (new_x, new_y)

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
        elif key in (arcade.key.S, arcade.key.DOWN):
            self.move_hold["down"] = True
        elif key in (arcade.key.A, arcade.key.LEFT):
            self.move_hold["left"] = True
        elif key in (arcade.key.D, arcade.key.RIGHT):
            self.move_hold["right"] = True
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

    def try_move_player(self, dx, dy):
        prev_room_id = self.room_tile_map.get(
            (self.player_pos[0], self.player_pos[1]))
        new_x = self.player_pos[0] + dx
        new_y = self.player_pos[1] + dy
        if 0 <= new_x < self.map_width and 0 <= new_y < self.map_height:
            tile_value = self.map_data[new_y][new_x]
            if tile_value in (0, 2, 3):
                self.player_pos = [new_x, new_y]
                room_id = self.room_tile_map.get((new_x, new_y))
                if room_id is not None and room_id not in self.revealed_rooms:
                    self.revealed_rooms.add(room_id)
                    self.update_visibility()

                if self.exit_room_idx is not None:
                    if room_id == self.exit_room_idx and not self.exit_music_played:
                        self.play_suspense_music()
                        self.exit_music_played = True

                if self.exit_pos and (new_x, new_y) == self.exit_pos:
                    self.advance_level()

                if self.exit_room_idx is not None:
                    if prev_room_id == self.exit_room_idx and room_id != self.exit_room_idx:
                        self.stop_suspense_music()
                        self.exit_music_played = False
                        self.play_game_music()

    def advance_level(self):
        self.level += 1
        self.revealed_rooms.clear()
        self.visible_tiles.clear()
        self.explored_tiles.clear()
        self.room_tile_map = {}
        self.stop_suspense_music()
        self.exit_room_idx = None
        self.exit_music_played = False
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
        if not self.map_data or not self.camera:
            return

        tile_size = self.tile_size
        cam_x, cam_y = self.camera.position
        half_w = (self.window.width // 2) if self.window else 0
        half_h = (self.window.height // 2) if self.window else 0

        view_left = max(0, int((cam_x - half_w) / tile_size) - 1)
        view_right = min(self.map_width, int((cam_x + half_w) / tile_size) + 2)
        view_bottom = max(0, int((cam_y - half_h) / tile_size) - 1)
        view_top = min(self.map_height, int((cam_y + half_h) / tile_size) + 2)

        batches = {
            'visible_wall': [],
            'visible_floor': [],
            'visible_exit': [],
            'explored_wall': [],
            'explored_floor': [],
            'black': []
        }

        for y in range(view_bottom, view_top):
            if y < 0 or y >= self.map_height:
                continue
            row = self.map_data[y]
            for x in range(view_left, view_right):
                if x < 0 or x >= self.map_width:
                    continue

                value = row[x]
                tile_pos = (x, y)
                visible = tile_pos in self.visible_tiles
                explored = tile_pos in self.explored_tiles

                screen_x = x * tile_size
                screen_y = y * tile_size
                left = screen_x
                right = screen_x + tile_size
                bottom = screen_y
                top = screen_y + tile_size

                if visible:
                    if value == 1:
                        batches['visible_wall'].append(
                            (left, right, bottom, top))
                    elif value == 3:
                        batches['visible_exit'].append(
                            (left, right, bottom, top))
                    else:
                        batches['visible_floor'].append(
                            (left, right, bottom, top))
                elif explored:
                    if value == 1:
                        batches['explored_wall'].append(
                            (left, right, bottom, top))
                    else:
                        batches['explored_floor'].append(
                            (left, right, bottom, top))
                else:
                    batches['black'].append((left, right, bottom, top))

        if batches['visible_wall']:
            for rect in batches['visible_wall']:
                arcade.draw_lrbt_rectangle_filled(
                    rect[0], rect[1], rect[2], rect[3], arcade.color.DIM_GRAY)
        if batches['visible_floor']:
            for rect in batches['visible_floor']:
                arcade.draw_lrbt_rectangle_filled(
                    rect[0], rect[1], rect[2], rect[3], arcade.color.LIGHT_GRAY)
        if batches['visible_exit']:
            for rect in batches['visible_exit']:
                arcade.draw_lrbt_rectangle_filled(
                    rect[0], rect[1], rect[2], rect[3], (180, 60, 40))
        if batches['explored_wall']:
            for rect in batches['explored_wall']:
                arcade.draw_lrbt_rectangle_filled(
                    rect[0], rect[1], rect[2], rect[3], arcade.color.BLACK_OLIVE)
        if batches['explored_floor']:
            for rect in batches['explored_floor']:
                arcade.draw_lrbt_rectangle_filled(
                    rect[0], rect[1], rect[2], rect[3], (40, 40, 40))
        if batches['black']:
            for rect in batches['black']:
                arcade.draw_lrbt_rectangle_filled(
                    rect[0], rect[1], rect[2], rect[3], arcade.color.BLACK)

        player_screen_x = self.player_draw_pos[0] - tile_size / 2
        player_screen_y = self.player_draw_pos[1] - tile_size / 2
        shrink = tile_size * 0.6
        half = shrink / 2
        arcade.draw_lrbt_rectangle_filled(
            player_screen_x + tile_size / 2 - half,
            player_screen_x + tile_size / 2 + half,
            player_screen_y + tile_size / 2 - half,
            player_screen_y + tile_size / 2 + half,
            arcade.color.AMARANTH_PURPLE
        )
