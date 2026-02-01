import arcade
import arcade.gui
import arcade.camera as arcade_camera
import os
import json
import math
import random
import time
import uuid
import edge_tts
from game.logic.music_manager import MusicManager
from project import ProjectSettings
from utils import get_config_path, get_savegame_path
from game.logic.music import find_music_file, play_loop, stop_player
from game.logic.map.storage import generate_and_store_map
from game.logic.logger import GameLogger
from game.entities.player import Player
from game.entities.boss import Boss
from game.entities.vendors.sage import SageNPC
from game.entities.vendors.merchant import MerchantNPC
from game.entities.vendors.mage import MageNPC
from game.entities.ghost import Ghost
from game.logic.ghost_manager import GhostManager
from windows.mage_dialog import MageDialog
from windows.game_over_view import GameOverView
from windows.end_game_view import EndGameView

from windows.end_game_view import EndGameView
from game.map.dungeon_map import DungeonMap
from game.items.effects import ITEM_EFFECTS
from game.items.explosives import Bomb, Dynamite, Explosion, ExplosionParticle
from windows.game_window_rendering import GameWindowRendering
from windows.game_window_inventory import GameWindowInventory
from windows.game_window_story import GameWindowStory
from windows.game_window_music import GameWindowMusic


class GameWindow(arcade.View, GameWindowRendering, GameWindowInventory, 
                 GameWindowStory, GameWindowMusic):
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

    def __init__(self, load_save=False, map_payload=None, map_name="current", level_override=None, spawn_corner=None, difficulty=None):
        super().__init__()
        
        # Всегда использовать легкую сложность
        self.DIFFICULTY_EASY = ProjectSettings.Game.DIFFICULTY_EASY
        self.difficulty = difficulty or ProjectSettings.Game.DIFFICULTY_EASY

        self.cheats_one_hit_kill = ProjectSettings.CHEATS_ENABLED

        self.cheat_block_enabled = False
        self.shield_active = False
        self.shield_duration = 4.0
        self.shield_timer = 0.0
        self.shield_cooldown = 5.0
        self.shield_cooldown_timer = 0.0

        self.screen_width = 0
        self.screen_height = 0
        self.map_width = 0
        self.map_height = 0
        self.tile_size = ProjectSettings.Game.TILE_SIZE

        self.dungeon_map = None
        self.player = None
        self.sage = None
        self.merchant = None
        self.mages = []  # Список магов NPC
        self.mage_spawned = False
        self.mage_dialog = MageDialog(self)
        self.bosses = []  # Список боссов
        self.ghost_manager = GhostManager(self.tile_size)
        self.ghosts = self.ghost_manager.ghosts
        self.visible_tiles = set()
        self.explored_tiles = set()
        self.visibility_grid = None
        self.explored_grid = None
        self.use_fov = False
        self.view_radius = 8
        self.save_point_pos = None
        self.save_point_used = False
        self.level = level_override or 1
        self.suspense_player = None
        self.camera = None
        self.ui_camera = arcade_camera.Camera2D()
        self.camera_lerp_speed = 0.12  # Скорость следования камеры

        self.move_hold = {"up": False, "down": False,
                          "left": False, "right": False}
        self._last_valid_pos = None  # Последняя валидная позиция для коллизий
        self.is_running = False
        self.mage_spawned = False  # Флаг спавна уникального мага
        self.move_cooldown = 0.1
        self.move_timer = 0.0
        self.exit_music_played = False
        self.frame_limit = ProjectSettings.Game.DEFAULT_FRAME_LIMIT
        self.spawn_corner = spawn_corner
        self.map_payload = map_payload
        
        self.current_fps = 0

        self.map_name = map_name
        self.minimap_player_draw_pos = None
        self.boss_room_ids = set()
        self.ambient_sprites = arcade.SpriteList()
        self.chest_sprites = arcade.SpriteList()
        self.dropped_item_sprites = arcade.SpriteList()
        self.visible_boss_ids = set()
        self.visible_chests = arcade.SpriteList()
        self.visible_dropped_items = arcade.SpriteList()
        self.inventory = []
        self.selected_slot = 0
        self.item_textures = {}
        self.valid_item_ids = set()
        self.player_damage_multiplier = 1.0
        self.player_damage_flat = 0
        self.player_move_speed_multiplier = 1.0
        self.passage_opening_effect = None
        self.player_attack_duration_multiplier = 1.0
        self.player_dodge_chance = 0.0
        self.damage_buff_timer = 0.0
        self.damage_buff_multiplier = 1.0

        self.velocity_x = 0.0
        self.velocity_y = 0.0
        self.friction = 0.85
        self.acceleration = 0.1

        self.camera_window_width = 0
        self.camera_window_height = 0
        self.camera_lerp_speed = 0.1  # Более плавное движение камеры
        self.camera_target_pos = None

        # Переменные тряски камеры
        self.camera_shake_intensity = 0
        self.camera_shake_duration = 0
        self.camera_original_pos = None

        # Эффекты смерти босса
        self.dying_bosses = []
        self.screen_flash_duration = 0.0
        self.screen_flash_timer = 0.0
        self.screen_flash_color = arcade.color.WHITE

        # Переменные отображения истории
        self.story_showing = False
        self.story_buttons_enabled = False

        # Инициализация менеджеров
        self.manager = arcade.gui.UIManager()
        self.manager.disable()

        self.pause_manager = arcade.gui.UIManager()
        self.pause_manager.disable()

        # Менеджер интерфейса истории - должен быть создан перед setup_story_ui
        self.story_manager = arcade.gui.UIManager()
        self.story_manager.disable()

        # Инициализация текста истории
        self.display_story_text()
        # Настройка интерфейса истории, но не показываем его изначально
        if self.window:
            self.setup_story_ui()

        self.inner_window_multiplier = 0.7
        self.outer_window_multiplier = 1.3
        self.max_camera_speed_multiplier = 2.0
        self.min_camera_speed_multiplier = 0.3

        self.music_volume = 1.0
        self.sound_volume = 1.0

        self.move_anim_time = 0.0
        self.move_anim_duration = 0.15
        self.move_anim_start = [0.0, 0.0]
        self.move_anim_target = [0.0, 0.0]

        self.show_pause_menu = False
        self.player_dead_message = None  # Сообщение о смерти игрока
        self.death_message_timer = 0.0  # Таймер для отображения сообщения

        # Переменные истории
        self.story_lines = []
        self.current_story_line = None
        self.current_story_text_object = None  # Для оптимизации отрисовки
        self.story_line_timer = 0.0
        self.story_display_duration = 15.0  # Секунд на строку
        self.story_audio_player = None
        self.pending_audio_path = None
        self.camera_lerp_speed = 0.1

        # Настройка видимости
        self.use_fov = True
        self.view_radius = 8  # Уменьшенный радиус обзора

        self.load_settings()
        if load_save:
            if not self.load_game():
                self.setup_game()
            else:
                self.update_visibility()
        else:
            self.setup_game()
        self.setup_pause_menu()
        self.play_game_music()

        self.loading_overlay_active = False
        self.loading_overlay_timer = 0.0
        self.loading_overlay_duration = 4.0
        self.loading_overlay_fade_in = 0.4
        self.loading_overlay_fade_out = 0.4
        self.loading_spinner_angle = 0.0
        self.loading_spinner_speed = 180.0

        self.game_over = False
        self.death_sequence_timer = 0.0

        # Statistics
        self.chest_open_count = 0
        self.cheat_activation_count = 0

        # End Game Sequence
        self.end_game_active = False
        self.end_game_phase = 0 # 0: None, 1: Video, 2: End Screen
        self.end_video_player = None
        self.end_video_texture = None
        self.end_video_path = os.path.join("resources", "videos", "theend.mp4")
        self.end_music_player = None
        self.end_stats_visible = False # Toggle for stats on end screen

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
                pass
                # print(f"Ошибка загрузки настроек: {e}")

    def find_music_file(self, preferred_filename=None, folder_path=None):
        return find_music_file(preferred_filename, folder_path)

    def play_game_music(self):
        """Воспроизведение игровой музыки"""
        # Используем реализацию из GameWindowMusic
        super().play_game_music()

    def play_suspense_music(self):
        """Воспроизводит музыку в комнате с боссом"""
        # Используем реализацию из GameWindowMusic
        super().play_suspense_music()

    def stop_suspense_music(self):
        """Останавливает музыку комнаты с выходом"""
        # Используем реализацию из GameWindowMusic
        super().stop_suspense_music()

    def stop_game_music(self):
        """Останавливает игровую музыку"""
        # Используем реализацию из GameWindowMusic
        super().stop_game_music()

    def close_exit_door(self):
        """Закрывает проход в комнату с выходом"""
        if not self.dungeon_map:
            return

        # Используем метод из DungeonMap, который обновляет данные карты и коллизии
        self.dungeon_map.close_exit_door()
        
        self.update_visibility()

    def open_exit_passage(self):
        """Открывает проход после смерти босса"""
        if not self.dungeon_map or not self.dungeon_map.exit_door_closed:
            return

        # Открываем проход - убираем стены на позициях прохода
        for x, y in self.dungeon_map.exit_door_positions:
            if 0 <= x < self.dungeon_map.map_width and 0 <= y < self.dungeon_map.map_height:
                if self.dungeon_map.exit_pos and (x, y) == self.dungeon_map.exit_pos:
                    # Восстановить плитку выхода, если это был выход
                    self.dungeon_map.map_data[y][x] = 3
                elif self.dungeon_map.get_tile_value(x, y) != 3:
                    self.dungeon_map.map_data[y][x] = 0  # Делаем полом
                    # Добавляем в коридоры
                    self.dungeon_map.corridor_tiles.add((x, y))

        self.dungeon_map.exit_door_closed = False
        self.update_visibility()
        
        # Красный квадрат портала выхода будет отрисован в on_draw на основе состояния exit_door_closed
        
        # Визуальные и звуковые эффекты открытия прохода
        self.trigger_passage_opening_effects()
        # print("Проход открыт! Босс повержен!")

    def trigger_passage_opening_effects(self):
        """Запускает визуальные и звуковые эффекты открытия прохода"""
        # Визуальный эффект - создаем частицы или вспышку
        self.passage_opening_effect = {
            'active': True,
            'start_time': time.time(),
            'duration': 2.0,  # Длительность эффекта в секундах
            'particles': []
        }
        return # Отключено: убрать все партиклы
        
        # Звуковой эффект
        try:
            # Загружаем звук открытия прохода
            passage_sound = arcade.load_sound("resources/sounds/passage_open.wav")
            arcade.play_sound(passage_sound, volume=0.7)
        except Exception:
            # Если звук не найден, используем стандартный звук
            try:
                success_sound = arcade.load_sound("resources/sounds/success.wav")
                arcade.play_sound(success_sound, volume=0.5)
            except Exception:
                pass  # Если звуки не загружены, просто продолжаем


    def setup_game(self):
        self.move_hold = {"up": False, "down": False, "left": False, "right": False}
        self.is_running = False
        try:
            # Захват инвентаря с предыдущего уровня
            old_inventory = []
            if hasattr(self, 'player') and self.player:
                old_inventory = self.player.inventory

            game_cfg = ProjectSettings.Game
            map_width, map_height = self.compute_map_dimensions(
                self.level, game_cfg)

            payload = self.map_payload
            if not payload:
                import random
                # Генерация уникального ID для генерации этого подземелья
                unique_id = str(uuid.uuid4())
                self.last_seed = unique_id
                # Использование уникального ID для генерации детерминированного целочисленного сида
                seed = int(uuid.UUID(unique_id).int & (1<<64)-1)
                
                print(f"Starting map generation with Unique ID: {unique_id} (Seed: {seed})")
                
                # Принудительный спавн в левом нижнем углу согласно требованиям
                self.spawn_corner = "bottom_left"
                    
                payload = generate_and_store_map(
                    map_width, map_height, game_cfg, self.spawn_corner, map_name=self.map_name, seed=seed)
                
                # Логирование генерации подземелья
                logger = GameLogger()
                rooms_count = len(payload.get("rooms", []))
                corridors_count = len(payload.get("corridor_tiles", []))
                # Позиции игрока/мага будут записаны после размещения
                logger.log_dungeon_generation(seed, rooms_count, corridors_count, "Pending", "Pending", unique_id=unique_id)

            self._apply_map_payload(payload, game_cfg)
            self.map_payload = None
            
            # Сброс спрайта выхода
            self.exit_sprite = None

            # Списки взрывчатки
            self.explosives_list = arcade.SpriteList()
            self.explosions_list = arcade.SpriteList()

            # Восстановление инвентаря
            if hasattr(self, 'player') and self.player:
                self.player.inventory = old_inventory
                self.apply_inventory_effects()
            
            self.game_over = False
            self.death_sequence_timer = 0.0
            
        except Exception as e:
            # print(f"Ошибка при генерации карты: {e}")
            # import traceback
            # traceback.print_exc()
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
                try:
                    self.player.sound_volume = self.sound_volume
                except Exception:
                    pass
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

                self.game_over = False
                self.death_sequence_timer = 0.0

                if self.camera is None and hasattr(self, 'window') and self.window:
                    self.camera = arcade_camera.Camera2D()
                    tile_size = self.tile_size
                    if self.player and self.player.pos:
                        start_cam_x = self.player.pos[0] * \
                            tile_size + tile_size // 2
                        start_cam_y = self.player.pos[1] * \
                            tile_size + tile_size // 2
                        self.camera.position = (start_cam_x, start_cam_y)
                        self.camera_target_pos = (start_cam_x, start_cam_y)

    def _apply_map_payload(self, payload, game_cfg):
        if not payload or not payload.get("map_data"):
            raise ValueError("Нет данных карты для загрузки")

        map_data = payload.get("map_data")
        self.map_height = len(map_data)
        self.map_width = len(map_data[0]) if self.map_height > 0 else 0
        self.spawn_corner = payload.get("spawn_corner", self.spawn_corner)

        self.dungeon_map = DungeonMap(
            self.map_width, self.map_height, self.tile_size, game_cfg, self.spawn_corner, map_payload=payload)

        # Создаем игрока с правильным контекстом OpenGL
        self.player = Player(self.tile_size)
        try:
            self.player.sound_volume = self.sound_volume
        except Exception:
            pass

        self.visible_tiles = set()
        self.explored_tiles = set()
        self.visibility_grid = None
        self.explored_grid = None
        self.exit_music_played = False
        self.save_point_used = False
        self.move_anim_time = 0.0
        if self.player and hasattr(self.player, "draw_pos"):
            self.move_anim_start = list(self.player.draw_pos)
            self.move_anim_target = list(self.player.draw_pos)
        # Легкая сложность - без точек сохранения
        self.save_point_pos = None

        self.place_player()
        self.place_bosses()
        self.place_ambient()
        self.init_items()
        self.place_chests()
        self.update_visibility()

        if self.camera is None and hasattr(self, 'window') and self.window:
            self.camera = arcade_camera.Camera2D()
            tile_size = self.tile_size
            if self.player and self.player.pos:
                start_cam_x = self.player.pos[0] * tile_size + tile_size // 2
                start_cam_y = self.player.pos[1] * tile_size + tile_size // 2
                self.camera.position = (start_cam_x, start_cam_y)
                self.camera_target_pos = (start_cam_x, start_cam_y)

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

    def find_spawn_pos(self):
        if not self.dungeon_map:
            return (1, 1)

        force_bottom_left = getattr(self, "spawn_corner", None) == "bottom_left"
        
        if force_bottom_left:
            # Простое сканирование с нижнего левого угла (2, 2)
            # Сканирование диагоналей от нижнего левого угла
            max_dim = max(self.dungeon_map.map_width, self.dungeon_map.map_height)
            for r in range(max_dim):
                for i in range(r + 1):
                    x = 2 + i
                    y = 2 + (r - i)
                    if (0 <= x < self.dungeon_map.map_width and 
                        0 <= y < self.dungeon_map.map_height and 
                        self.dungeon_map.is_walkable(x, y)):
                        return (x, y)
        
        center_x = self.dungeon_map.map_width // 2
        center_y = self.dungeon_map.map_height // 2

        def is_free(x, y):
            return (0 <= x < self.dungeon_map.map_width and
                    0 <= y < self.dungeon_map.map_height and
                    self.dungeon_map.is_walkable(x, y))

        spawn_pos = None
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
            spawn_pos = (1, 1)
            
        return spawn_pos

    def place_sage(self, spawn_pos=None):
        if not self.dungeon_map:
            return
            
        if self.player and hasattr(self.player, "pos"):
            spawn_pos = tuple(self.player.pos)
        elif spawn_pos is None:
            spawn_pos = self.find_spawn_pos()

        px, py = spawn_pos
        # Ставим Мудреца на ту же клетку, что и игрок, если она валидна и не (0,0)
        valid_same = (px != 0 or py != 0) and self.dungeon_map.is_walkable(px, py)
        target_pos = None
        if valid_same:
            target_pos = spawn_pos
        else:
            found = None
            distances = [1, 2, 3]
            for dist in distances:
                candidates = []
                for dx in range(-dist, dist + 1):
                    candidates.append((px + dx, py + dist))
                    candidates.append((px + dx, py - dist))
                for dy in range(-dist + 1, dist):
                    candidates.append((px + dist, py + dy))
                    candidates.append((px - dist, py + dy))
                for cx, cy in candidates:
                    if 0 <= cx < self.dungeon_map.map_width and 0 <= cy < self.dungeon_map.map_height:
                        if self.dungeon_map.is_walkable(cx, cy) and (cx, cy) != (px, py):
                            occupied = False
                            for boss in getattr(self, "bosses", []):
                                if boss and tuple(boss.pos) == (cx, cy):
                                    occupied = True
                                    break
                            if not occupied:
                                found = (cx, cy)
                                break
                if found:
                    break
            target_pos = found if found else self.find_spawn_pos()

        self.sage = SageNPC(self.tile_size, target_pos)
        if self.sage and self.sage.sprite:
            self.sage.alpha = 0
            try:
                self.sage.sprite.alpha = 0
            except Exception:
                pass
            start_px = self.player.draw_pos[0] if self.player else (px * self.tile_size + self.tile_size // 2)
            start_py = self.player.draw_pos[1] if self.player else (py * self.tile_size + self.tile_size // 2)
            self.sage.start_draw_pos = [start_px, start_py]
            self.sage.target_draw_pos = [target_pos[0] * self.tile_size + self.tile_size // 2,
                                         target_pos[1] * self.tile_size + self.tile_size // 2]
            self.sage.spawn_anim_active = True
    
    def _get_occupied_grid_positions(self):
        occupied = set()
        if self.player and hasattr(self.player, "pos"):
            occupied.add(tuple(self.player.pos))
        if self.sage:
            occupied.add(tuple(self.sage.pos))
        if self.merchant:
            occupied.add(tuple(self.merchant.pos))
        for mage in self.mages:
            if mage:
                occupied.add(tuple(mage.pos))
        for boss in getattr(self, "bosses", []):
            if boss:
                occupied.add(tuple(boss.pos))
        if self.chest_sprites:
            for chest in self.chest_sprites:
                gx = int(chest.center_x / self.tile_size)
                gy = int(chest.center_y / self.tile_size)
                occupied.add((gx, gy))
        if self.dropped_item_sprites:
            for item in self.dropped_item_sprites:
                gx = int(item.center_x / self.tile_size)
                gy = int(item.center_y / self.tile_size)
                occupied.add((gx, gy))
        return occupied
    
    def _is_reachable(self, start, target):
        if not self.dungeon_map or not start or not target:
            return False
        sx, sy = start
        tx, ty = target
        w, h = self.dungeon_map.map_width, self.dungeon_map.map_height
        if not (0 <= sx < w and 0 <= sy < h and 0 <= tx < w and 0 <= ty < h):
            return False
        if not self.dungeon_map.is_walkable(tx, ty):
            return False
        from collections import deque
        q = deque()
        q.append((sx, sy))
        visited = set()
        visited.add((sx, sy))
        dirs = [(1,0),(-1,0),(0,1),(0,-1)]
        while q:
            x, y = q.popleft()
            if (x, y) == (tx, ty):
                return True
            for dx, dy in dirs:
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in visited:
                    if self.dungeon_map.is_walkable(nx, ny):
                        visited.add((nx, ny))
                        q.append((nx, ny))
        return False
    
    def _compute_reachable_from_player(self):
        if not self.player or not self.dungeon_map:
            return set()
        sx, sy = self.player.pos
        w, h = self.dungeon_map.map_width, self.dungeon_map.map_height
        from collections import deque
        q = deque()
        q.append((sx, sy))
        visited = set()
        visited.add((sx, sy))
        dirs = [(1,0),(-1,0),(0,1),(0,-1)]
        while q:
            x, y = q.popleft()
            for dx, dy in dirs:
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in visited:
                    if self.dungeon_map.is_walkable(nx, ny):
                        visited.add((nx, ny))
                        q.append((nx, ny))
        return visited
    
    def find_random_corridor_spawn(self, exclude_borders_margin=0):
        """
        Находит валидную точку спавна в коридорах.
        
        Args:
            exclude_borders_margin (int): Отступ от границ карты, который нужно исключить.
            
        Алгоритм:
        1. Собирает все тайлы коридоров.
        2. Фильтрует кандидатов на основе:
           - Отступа от границ.
           - Проходимости (должен быть пол).
           - Отсутствия других сущностей (игрок, боссы и т.д.).
        3. Вычисляет достижимые тайлы от игрока с помощью BFS для гарантии доступности.
        4. Выбирает случайного достижимого кандидата.
        5. Fallback: возвращает ближайшего валидного кандидата, если достижимых нет.
        """
        if not self.dungeon_map:
            return None
        tiles = list(self.dungeon_map.corridor_tiles or [])
        if not tiles:
            return None
        occ = self._get_occupied_grid_positions()
        w, h = self.dungeon_map.map_width, self.dungeon_map.map_height
        base_candidates = []
        for (x, y) in tiles:
            if exclude_borders_margin > 0:
                if x < exclude_borders_margin or x >= w - exclude_borders_margin:
                    continue
                if y < exclude_borders_margin or y >= h - exclude_borders_margin:
                    continue
            
            if 0 <= x < w and 0 <= y < h and self.dungeon_map.is_walkable(x, y) and (x, y) not in occ:
                base_candidates.append((x, y))
        if not base_candidates:
            return None
        # Требуем достижимость от игрока (один BFS для всей области)
        reachable = []
        reach_set = self._compute_reachable_from_player()
        if reach_set:
            reachable = [c for c in base_candidates if c in reach_set]
        import random
        if reachable:
            return random.choice(reachable)
        # Если нет достижимых, берём ближайший по Манхэттену из базовых
        if self.player and hasattr(self.player, "pos"):
            px, py = self.player.pos
            base_candidates.sort(key=lambda c: abs(c[0]-px)+abs(c[1]-py))
            return base_candidates[0] if base_candidates else None
        return None
    
    def place_sage_in_corridor(self):
        if not self.dungeon_map:
            return
        target = self.find_random_corridor_spawn()
        if target is None:
            if self.player and hasattr(self.player, "pos"):
                target = tuple(self.player.pos)
            else:
                target = self.find_spawn_pos()
        # print(f"[SageSpawn] выбранная позиция: {target}")
        self.sage = SageNPC(self.tile_size, target)
        if self.sage and self.sage.sprite:
            self.sage.alpha = 0
            try:
                self.sage.sprite.alpha = 0
            except Exception:
                pass
            tx, ty = target
            px = self.player.draw_pos[0] if self.player else (tx * self.tile_size + self.tile_size // 2)
            py = self.player.draw_pos[1] if self.player else (ty * self.tile_size + self.tile_size // 2)
            self.sage.start_draw_pos = [px, py]
            self.sage.target_draw_pos = [tx * self.tile_size + self.tile_size // 2,
                                         ty * self.tile_size + self.tile_size // 2]
            self.sage.spawn_anim_active = True

    def place_merchant(self):
        if not self.dungeon_map:
            return
            
        # 1. Получение валидных координат спавна (кешировано)
        valid_coords = self.dungeon_map.get_valid_spawn_coords()
        if not valid_coords:
             # Запасной вариант
             self.merchant = MerchantNPC(self.tile_size, self.find_spawn_pos())
             return

        target = None
        player_pos = self.player.pos if self.player else (0, 0)
        
        # 2. Попытка найти валидное место с ограничениями по дистанции
        # Оптимизация: Фильтрация valid_coords по дистанции
        
        # Выборка, если слишком много, чтобы избежать лагов
        sample_pool = valid_coords
        if len(valid_coords) > 500:
             sample_pool = random.sample(valid_coords, 500)
             
        candidates = []
        min_dist_sq = 100 # 10^2
        max_dist_sq = 625 # 25^2
        
        for c in sample_pool:
            dx = c[0] - player_pos[0]
            dy = c[1] - player_pos[1]
            dist_sq = dx*dx + dy*dy
            
            if min_dist_sq <= dist_sq <= max_dist_sq:
                candidates.append(c)
                
        if candidates:
            target = random.choice(candidates)
                
        if target is None:
            # Если не удалось найти рядом, запасной вариант - случайный коридор
            target = self.find_random_corridor_spawn()
            if target is None:
                 target = self.find_spawn_pos()
            
        self.merchant = MerchantNPC(self.tile_size, target)

    def place_mages(self):
        """
        Спавнит уникального мага один раз за сессию в коридоре.
        """
        if not self.dungeon_map:
            return
        
        # Если маги уже есть (например, загружены), не трогаем их
        if self.mages:
            return
        
        # Проверка, был ли маг уже создан в этой сессии
        if self.mage_spawned:
            return

        self.mages = []

        # Найти случайную позицию в коридоре
        if not self.dungeon_map.corridor_tiles:
            return

        import random
        # Преобразуем set в list для выбора
        corridor_list = list(self.dungeon_map.corridor_tiles)
        if not corridor_list:
            return

        # Пытаемся найти подходящее место рядом с игроком (для немедленного следования)
        target = None
        px, py = self.player.pos if self.player else (0, 0)
        
        # Сортируем коридоры по расстоянию к игроку
        corridor_list.sort(key=lambda p: (p[0]-px)**2 + (p[1]-py)**2)
        
        # Ищем первый подходящий (не вплотную, но близко: 3-6 тайлов)
        min_dist_sq = 3*3
        max_dist_sq = 6*6
        
        for cand in corridor_list:
             d2 = (cand[0]-px)**2 + (cand[1]-py)**2
             if min_dist_sq <= d2 <= max_dist_sq:
                 if self.dungeon_map.is_walkable(cand[0], cand[1]):
                     target = cand
                     break
        
        # Если не нашли в идеальном диапазоне, берем ближайший доступный (> 2 тайлов)
        if not target:
             for cand in corridor_list:
                 d2 = (cand[0]-px)**2 + (cand[1]-py)**2
                 if d2 > 2*2:
                     if self.dungeon_map.is_walkable(cand[0], cand[1]):
                         target = cand
                         break
        
        if not target:
            target = random.choice(corridor_list)

        # Создаем мага с параметрами для следования
        # Можно настроить скорость здесь, если нужно (по умолчанию в классе)
        mage = MageNPC(self.tile_size, target)
        
        # Настройка анимации спавна
        if mage and mage.sprite:
            mage.alpha = 0
            try:
                mage.sprite.alpha = 0
            except Exception:
                pass
            
            tx, ty = target
            mage.start_draw_pos = [tx * self.tile_size + self.tile_size // 2,
                                    ty * self.tile_size + self.tile_size // 2] # Начинаем сразу на месте
            mage.target_draw_pos = mage.start_draw_pos
            mage.spawn_anim_active = True
            
        self.mages.append(mage)
        
        # Отмечаем, что маг был создан
        self.mage_spawned = True
        
        logger = GameLogger()
        logger.log(f"Unique Mage spawned at {target}")
        
    def place_ghosts(self):
        """Размещает призраков в случайных местах с помощью GhostManager"""
        if not self.dungeon_map:
            return
            
        # Использование GhostManager для спавна призраков в коридорах
        self.ghost_manager.ghosts.clear()
        self.ghost_manager.ghost_records.clear()
        
        count = random.randint(3, 5) + (self.level // 2) # Масштабирование с уровнем
        self.ghost_manager.spawn_ghosts(self.dungeon_map, count, self.level)

    def place_player(self):
        if not self.dungeon_map or not self.player:
            return

        spawn_pos = self.find_spawn_pos()

        self.player.set_pos(*spawn_pos)
        self.visible_tiles.add(spawn_pos)
        self.minimap_player_draw_pos = (
            float(spawn_pos[0]), float(spawn_pos[1]))
            
        logger = GameLogger()
        logger.log(f"Player spawned at: {spawn_pos}")
            
        # self.place_sage_in_corridor()
        # self.place_merchant()
        self.place_mages()
        self.place_ghosts()

    def place_bosses(self):
        """Размещает боссов и обычных врагов на карте, боссы далеко от спавна"""
        if not self.dungeon_map or not self.dungeon_map.rooms:
            return

        import random
        self.bosses = []
        self.boss_room_ids = set()

        # Определяем комнату спавна игрока
        spawn_room_id = None
        if self.player and hasattr(self.player, "pos"):
            spawn_room_id = self.dungeon_map.get_room_id(
                self.player.pos[0], self.player.pos[1])

        # Приоритет 1: Использование назначенной комнаты выхода для босса
        far_room_idx = None
        boss_x, boss_y = None, None
        
        if self.dungeon_map.exit_room_idx is not None and self.dungeon_map.exit_room_idx != spawn_room_id:
             far_room_idx = self.dungeon_map.exit_room_idx
             
             # Если есть координаты выхода, ставим босса относительно них
             if self.dungeon_map.exit_pos:
                 ex, ey = self.dungeon_map.exit_pos
                 boss_x = ex + 1
                 boss_y = ey + 1
                 
                 # Скрываем выход (делаем его полом), пока босс жив
                 if 0 <= ex < self.dungeon_map.map_width and 0 <= ey < self.dungeon_map.map_height:
                     self.dungeon_map.map_data[ey][ex] = 2
             else:
                 # Fallback: центр комнаты
                 room = self.dungeon_map.rooms[far_room_idx]
                 if isinstance(room, dict):
                    x1, y1, x2, y2 = room["x1"], room["y1"], room["x2"], room["y2"]
                    boss_x = (x1 + x2) // 2
                    boss_y = (y1 + y2) // 2
                 else:
                    x, y, w, h = room
                    boss_x = x + w // 2
                    boss_y = y + h // 2
        
        if boss_x is None:
            # Fallback: Выбираем комнату у края карты, максимально далекую от спавна для босса Caveman
            far_room_center = None
            max_dist_sq = -1
            margin = 2
            map_w = self.dungeon_map.map_width
            map_h = self.dungeon_map.map_height
            corner_candidates = []
            for i, room in enumerate(self.dungeon_map.rooms):
                if i == spawn_room_id:
                    continue
                if isinstance(room, dict):
                    x1 = room.get("x1", 0)
                    y1 = room.get("y1", 0)
                    x2 = room.get("x2", 0)
                    y2 = room.get("y2", 0)
                    cx = (x1 + x2) // 2
                    cy = (y1 + y2) // 2
                else:
                    x, y, w, h = room
                    cx = x + w // 2
                    cy = y + h // 2
                if self.player and self.player.pos:
                    dx = cx - self.player.pos[0]
                    dy = cy - self.player.pos[1]
                    dist_sq = dx*dx + dy*dy
                else:
                    dist_sq = 0
                near_edge = (cx <= margin or cy <= margin or cx >=
                            map_w - margin or cy >= map_h - margin)
                if near_edge:
                    corner_candidates.append((i, cx, cy, dist_sq))
                if dist_sq > max_dist_sq and self.dungeon_map.is_walkable(cx, cy):
                    max_dist_sq = dist_sq
                    far_room_idx = i
                    far_room_center = (cx, cy)

            # Предпочтительно берём самую дальнюю комнату у края
            if corner_candidates:
                corner_candidates.sort(key=lambda t: t[3], reverse=True)
                candidate_idx, cx, cy, _ = corner_candidates[0]
                boss_x, boss_y = cx, cy
                far_room_idx = candidate_idx
            elif far_room_center:
                boss_x, boss_y = far_room_center
                
        if boss_x is not None:
            boss = Boss(self.tile_size, "Caveman Boss", (boss_x, boss_y))
            boss.scale_stats(self.level)
            boss.visible = True
            if self.player and boss.sprite:
                boss.sprite.scale = self.player.sprite.scale
            self.bosses.append(boss)
            if far_room_idx is not None:
                self.boss_room_ids.add(far_room_idx)

        # Размещаем дополнительных врагов (мобы) в случайных комнатах
        available_room_indices = []
        for i, room in enumerate(self.dungeon_map.rooms):
            if i != far_room_idx and i != spawn_room_id:
                available_room_indices.append(i)

        random.shuffle(available_room_indices)
        goblin_count = 5
        viking_count = 5

        # Выбираем уникальные комнаты для каждого типа, чтобы разбросать по карте
        goblin_rooms = random.sample(available_room_indices, k=min(
            goblin_count, len(available_room_indices)))
        remaining = [
            i for i in available_room_indices if i not in goblin_rooms]
        viking_rooms = random.sample(
            remaining, k=min(viking_count, len(remaining)))

        def spawn_in_room(idx, mob_type):
            room = self.dungeon_map.rooms[idx]
            if isinstance(room, dict):
                x1 = room.get("x1", 0)
                y1 = room.get("y1", 0)
                x2 = room.get("x2", 0)
                y2 = room.get("y2", 0)
                spawn_x = random.randint(x1 + 1, max(x1 + 1, x2 - 2))
                spawn_y = random.randint(y1 + 1, max(y1 + 1, y2 - 2))
            else:
                x, y, w, h = room
                spawn_x = random.randint(x + 1, max(x + 1, x + w - 2))
                spawn_y = random.randint(y + 1, max(y + 1, y + h - 2))

            if (0 <= spawn_x < self.dungeon_map.map_width and
                0 <= spawn_y < self.dungeon_map.map_height and
                    self.dungeon_map.is_walkable(spawn_x, spawn_y)):
                mob = Boss(self.tile_size, mob_type, (spawn_x, spawn_y))
                mob.scale_stats(self.level)
                mob.visible = True
                if self.player and mob.sprite:
                    mob.sprite.scale = self.player.sprite.scale
                self.bosses.append(mob)
        
        # Тест распределения коридорных спавнов мага (диагностика)
        # Диагностика коридорного спавна удалена для предотвращения задержек генерации
        
        # Отключен спавн мобов, чтобы гарантировать наличие только одного босса на уровень
        # for idx in goblin_rooms:
        #     spawn_in_room(idx, "Giant Goblin")
        # for idx in viking_rooms:
        #     spawn_in_room(idx, "Viking Leader")

    def place_ambient(self):
        if not self.dungeon_map:
            return
        path = os.path.join("resources", "map", "tile_0108.png")
        count = random.randint(4, 8)
        for _ in range(count):
            sprite = arcade.Sprite(path)
            tex = sprite.texture
            if tex and tex.width:
                sprite.scale = (self.tile_size / tex.width) * 0.6
            rx = random.randint(0, self.dungeon_map.map_width - 1)
            ry = random.randint(0, self.dungeon_map.map_height - 1)
            sprite.center_x = rx * self.tile_size + self.tile_size // 2
            sprite.center_y = ry * self.tile_size + self.tile_size // 2
            sprite.change_x = random.uniform(-1.5, 1.5)
            sprite.change_y = random.uniform(-1.5, 1.5)
            # Добавление позиции сетки для отсечения
            sprite.grid_x = rx
            sprite.grid_y = ry
            self.ambient_sprites.append(sprite)

    def init_items(self):
        trash = {1, 7, 11, 12, 22, 31, 34, 35, 36, 37, 48}
        icons_dir = os.path.join("resources", "items")
        for i in range(1, 51):
            if i in trash:
                continue
            p = os.path.join(icons_dir, f"Icon{i}.png")
            if os.path.exists(p):
                tex = arcade.load_texture(p)
                self.item_textures[i] = tex
                self.valid_item_ids.add(i)
        self.apply_inventory_effects()

    def place_chests(self):
        if not self.dungeon_map or not self.dungeon_map.rooms:
            return
        self.chest_sprites = arcade.SpriteList()
        closed_path = os.path.join("resources", "map", "tile_0092.png")
        
        rooms = self.dungeon_map.rooms
        chest_count = 0
        
        print(f"--- Chest Placement Statistics ---")
        
        # Получение изначально занятых позиций
        occupied = self._get_occupied_grid_positions()
        
        # Вспомогательная функция для размещения сундука в конкретной комнате
        def place_chest_in_room(room):
            if isinstance(room, dict):
                x1, y1, x2, y2 = room["x1"], room["y1"], room["x2"], room["y2"]
            else:
                x, y, w, h = room
                x1, y1, x2, y2 = x, y, x + w, y + h
            
            # Попытка найти подходящее место
            for _ in range(20):
                cx = random.randint(x1 + 1, x2 - 2)
                cy = random.randint(y1 + 1, y2 - 2)
                
                # Проверка занятости клетки
                if (cx, cy) not in occupied and self.dungeon_map.is_walkable(cx, cy):
                    s = arcade.Sprite(closed_path)
                    if s.texture and s.texture.width:
                        s.scale = (self.tile_size / s.texture.width)
                    s.center_x = cx * self.tile_size + self.tile_size // 2
                    s.center_y = cy * self.tile_size + self.tile_size // 2
                    s.properties = {"opened": False}
                    self.chest_sprites.append(s)
                    occupied.add((cx, cy))
                    return True
            return False

        # 1. Гарантируем наличие хотя бы одного сундука в каждой комнате
        for i, room in enumerate(rooms):
            if place_chest_in_room(room):
                chest_count += 1
        
        # 2. Размещаем дополнительные сундуки (много)
        # Цель: ~5 сундуков на комнату в среднем
        target_total = len(rooms) * 5
        attempts = 0
        while chest_count < target_total and attempts < 100:
            attempts += 1
            room = random.choice(rooms)
            if place_chest_in_room(room):
                chest_count += 1
        
        print(f"Total chests placed: {chest_count}")
        print(f"Average chests per room: {chest_count / len(rooms):.2f}")
        print(f"----------------------------------")

        try:
            with open("generation_stats.txt", "a") as f:
                f.write(f"--- Chest Placement Statistics ---\n")
                f.write(f"Total chests placed: {chest_count}\n")
                f.write(f"Average chests per room: {chest_count / len(rooms):.2f}\n")
                f.write(f"----------------------------------\n")
        except Exception as e:
            print(f"Failed to save stats: {e}")



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
            # Всегда добавляем текущую позицию (даже если это стена)
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

            # Проверяем блокировку ПЕРЕД добавлением в видимые
            if self.is_blocking(x, y):
                # Стена - добавляем её в видимые (чтобы видеть стену), но не проходим дальше
                visible.add((x, y))
                break

            visible.add((x, y))

            if x == end_x and y == end_y:
                break

            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy

        return visible

    def calculate_fov(self, center_x, center_y, radius, facing=None):
        visible = set()
        # Всегда видим свою текущую позицию
        visible.add((center_x, center_y))

        # Круговой обзор для освещения
        # Увеличиваем количество лучей для более плавного освещения
        num_rays = max(36, int(radius * 6))
        for i in range(num_rays):
            # Равномерно распределяем лучи по кругу
            angle = 2 * math.pi * i / num_rays

            # Рассчитываем направление луча
            ray_dir_x = math.cos(angle)
            ray_dir_y = math.sin(angle)

            # Бросаем луч до максимального радиуса
            for dist in range(1, int(radius) + 1):
                target_x = int(round(center_x + ray_dir_x * dist))
                target_y = int(round(center_y + ray_dir_y * dist))

                # Проверяем границы
                if (target_x < 0 or target_x >= self.dungeon_map.map_width or
                        target_y < 0 or target_y >= self.dungeon_map.map_height):
                    break

                # Проверяем расстояние (чтобы не превышать радиус)
                distance_sq = (target_x - center_x)**2 + \
                    (target_y - center_y)**2
                if distance_sq > radius * radius:
                    break

                # Добавляем тайл в видимые
                visible.add((target_x, target_y))

                # Если встретили стену, луч останавливается
                if self.is_blocking(target_x, target_y):
                    break

        return visible

    def _setup_difficulty_visibility(self):
        # Настройки легкой сложности
        self.view_radius = 5
        self.use_fov = True

    def _check_line_of_sight(self, target_grid_pos):
        """Проверяет прямую видимость от игрока до цели (raycasting)."""
        if not self.player or not self.dungeon_map:
            return False
            
        player_grid = self.player.get_grid_position()
        
        # Если в одной клетке - видим
        if player_grid == target_grid_pos:
            return True
            
        return self.dungeon_map.has_line_of_sight(player_grid, target_grid_pos)

    def _update_fading(self, delta_time):
        """Обновляет прозрачность объектов для плавного появления/исчезновения в темноте"""
        transition_speed = 5.0 # Скорость затухания
        
        # 1. Боссы
        for boss in self.bosses:
            if not boss: continue
            
            # Проверка целевой видимости
            is_visible = False
            bx, by = int(boss.pos[0]), int(boss.pos[1])
            if self.visibility_grid and 0 <= by < len(self.visibility_grid) and 0 <= bx < len(self.visibility_grid[0]):
                is_visible = self.visibility_grid[by][bx]
            elif (bx, by) in self.visible_tiles:
                is_visible = True
            
            # Дополнительная проверка raycasting
            if is_visible:
                 is_visible = self._check_line_of_sight((bx, by))
            
            # Целевая альфа
            target_alpha = 255 if is_visible else 0
            
            # Обновляем спрайт
            if hasattr(boss, "sprite"):
                current_alpha = boss.sprite.alpha
                if current_alpha < target_alpha:
                    current_alpha = min(target_alpha, current_alpha + transition_speed * delta_time * 255)
                elif current_alpha > target_alpha:
                    current_alpha = max(target_alpha, current_alpha - transition_speed * delta_time * 255)
                boss.sprite.alpha = int(current_alpha)
                # Обновляем логический флаг видимости
                boss.visible = (current_alpha > 0)

        # 2. Маги
        if getattr(self, "mages", None):
            for mage in self.mages:
                if getattr(mage, "spawn_anim_active", False):
                    continue # Маг сам управляет своей прозрачностью при спавне
                
                is_visible = False
                mx, my = int(mage.pos[0]), int(mage.pos[1])
                if self.visibility_grid and 0 <= my < len(self.visibility_grid) and 0 <= mx < len(self.visibility_grid[0]):
                    is_visible = self.visibility_grid[my][mx]
                elif (mx, my) in self.visible_tiles:
                    is_visible = True
                
                # Дополнительная проверка raycasting
                if is_visible:
                     is_visible = self._check_line_of_sight((mx, my))
                
                target_alpha = 255 if is_visible else 0
                
                if hasattr(mage, "sprite") and mage.sprite:
                    current_alpha = mage.sprite.alpha
                    if current_alpha < target_alpha:
                        current_alpha = min(target_alpha, current_alpha + transition_speed * delta_time * 255)
                    elif current_alpha > target_alpha:
                        current_alpha = max(target_alpha, current_alpha - transition_speed * delta_time * 255)
                    mage.sprite.alpha = int(current_alpha)

        # 3. Выпавшие предметы
        if self.dropped_item_sprites:
            for item in self.dropped_item_sprites:
                gx = int(item.center_x / self.tile_size)
                gy = int(item.center_y / self.tile_size)
                
                is_visible = False
                if self.visibility_grid and 0 <= gy < len(self.visibility_grid) and 0 <= gx < len(self.visibility_grid[0]):
                     is_visible = self.visibility_grid[gy][gx]
                elif (gx, gy) in self.visible_tiles:
                     is_visible = True
                
                # Raycasting для предметов
                if is_visible:
                    is_visible = self._check_line_of_sight((gx, gy))
                
                target_alpha = 255 if is_visible else 0
                
                current_alpha = item.alpha
                if current_alpha < target_alpha:
                    current_alpha = min(target_alpha, current_alpha + transition_speed * delta_time * 255)
                elif current_alpha > target_alpha:
                    current_alpha = max(target_alpha, current_alpha - transition_speed * delta_time * 255)
                item.alpha = int(current_alpha)

        # 4. Эмбиент (Призраки и т.д.)
        if self.ambient_sprites:
             for sprite in self.ambient_sprites:
                gx = int(sprite.center_x / self.tile_size)
                gy = int(sprite.center_y / self.tile_size)
                
                is_visible = (gx, gy) in self.visible_tiles
                
                # Raycasting для эмбиента
                if is_visible:
                    is_visible = self._check_line_of_sight((gx, gy))

                target_alpha = 255 if is_visible else 0
                current_alpha = sprite.alpha
                if current_alpha < target_alpha:
                    current_alpha = min(target_alpha, current_alpha + transition_speed * delta_time * 255)
                elif current_alpha > target_alpha:
                    current_alpha = max(target_alpha, current_alpha - transition_speed * delta_time * 255)
                sprite.alpha = int(current_alpha)

        # 4.1 Призраки (Ghosts)
        if hasattr(self, "ghosts") and self.ghosts:
            for ghost in self.ghosts:
                if not ghost or not hasattr(ghost, "sprite") or not ghost.sprite:
                    continue
                
                # Призраки теперь всегда видимы (по запросу пользователя)
                # Устанавливаем целевую альфу в 255 без проверок видимости
                target_alpha = 255
                
                current_alpha = ghost.sprite.alpha
                if current_alpha < target_alpha:
                    current_alpha = min(target_alpha, current_alpha + transition_speed * delta_time * 255)
                elif current_alpha > target_alpha:
                    current_alpha = max(target_alpha, current_alpha - transition_speed * delta_time * 255)
                
                ghost.sprite.alpha = int(current_alpha)

        # 4.2 Маги (Mages)
        if hasattr(self, "mages") and self.mages:
            for mage in self.mages:
                if not mage:
                     continue
                
                mx, my = int(mage.pos[0]), int(mage.pos[1])
                is_visible = False
                if self.visibility_grid and 0 <= my < len(self.visibility_grid) and 0 <= mx < len(self.visibility_grid[0]):
                     is_visible = self.visibility_grid[my][mx]
                elif (mx, my) in self.visible_tiles:
                     is_visible = True
                
                # Raycasting для магов
                if is_visible:
                     is_visible = self._check_line_of_sight((mx, my))
                
                target_alpha = 255 if is_visible else 0
                
                # Маги могут не иметь спрайта напрямую, или иметь сложную структуру
                # Предполагаем, что у мага есть метод set_alpha или свойство sprite
                if hasattr(mage, "sprite") and mage.sprite:
                    current_alpha = mage.sprite.alpha
                    if current_alpha < target_alpha:
                        current_alpha = min(target_alpha, current_alpha + transition_speed * delta_time * 255)
                    elif current_alpha > target_alpha:
                        current_alpha = max(target_alpha, current_alpha - transition_speed * delta_time * 255)
                    mage.sprite.alpha = int(current_alpha)

        # 5. Sage (Мудрец)
        if getattr(self, "sage", None):
            sage = self.sage
            sx, sy = int(sage.pos[0]), int(sage.pos[1])
            is_visible = False
            if self.visibility_grid and 0 <= sy < len(self.visibility_grid) and 0 <= sx < len(self.visibility_grid[0]):
                 is_visible = self.visibility_grid[sy][sx]
            elif (sx, sy) in self.visible_tiles:
                 is_visible = True
            
            # Дополнительная проверка raycasting
            if is_visible:
                 is_visible = self._check_line_of_sight((sx, sy))
            
            target_alpha = 255 if is_visible else 0
            if hasattr(sage, "sprite") and sage.sprite:
                current_alpha = sage.sprite.alpha
                if current_alpha < target_alpha:
                    current_alpha = min(target_alpha, current_alpha + transition_speed * delta_time * 255)
                elif current_alpha > target_alpha:
                    current_alpha = max(target_alpha, current_alpha - transition_speed * delta_time * 255)
                sage.sprite.alpha = int(current_alpha)

        # 6. Merchant (Торговец)
        if getattr(self, "merchant", None):
            merchant = self.merchant
            mx, my = int(merchant.pos[0]), int(merchant.pos[1])
            is_visible = False
            if self.visibility_grid and 0 <= my < len(self.visibility_grid) and 0 <= mx < len(self.visibility_grid[0]):
                 is_visible = self.visibility_grid[my][mx]
            elif (mx, my) in self.visible_tiles:
                 is_visible = True
            
            # Дополнительная проверка raycasting
            if is_visible:
                 is_visible = self._check_line_of_sight((mx, my))
            
            target_alpha = 255 if is_visible else 0
            if hasattr(merchant, "sprite") and merchant.sprite:
                current_alpha = merchant.sprite.alpha
                if current_alpha < target_alpha:
                    current_alpha = min(target_alpha, current_alpha + transition_speed * delta_time * 255)
                elif current_alpha > target_alpha:
                    current_alpha = max(target_alpha, current_alpha - transition_speed * delta_time * 255)
                merchant.sprite.alpha = int(current_alpha)

        # 7. Explosives (Взрывчатка)
        if hasattr(self, 'explosives_list') and self.explosives_list:
            for explosive in self.explosives_list:
                gx = int(explosive.center_x / self.tile_size)
                gy = int(explosive.center_y / self.tile_size)
                
                is_visible = False
                if self.visibility_grid and 0 <= gy < len(self.visibility_grid) and 0 <= gx < len(self.visibility_grid[0]):
                     is_visible = self.visibility_grid[gy][gx]
                elif (gx, gy) in self.visible_tiles:
                     is_visible = True
                
                # Raycasting
                if is_visible:
                    is_visible = self._check_line_of_sight((gx, gy))

                target_alpha = 255 if is_visible else 0
                current_alpha = explosive.alpha
                if current_alpha < target_alpha:
                    current_alpha = min(target_alpha, current_alpha + transition_speed * delta_time * 255)
                elif current_alpha > target_alpha:
                    current_alpha = max(target_alpha, current_alpha - transition_speed * delta_time * 255)
                explosive.alpha = int(current_alpha)

        # 8. Explosions/Particles (Взрывы и частицы)
        if hasattr(self, 'explosions_list') and self.explosions_list:
            for particle in self.explosions_list:
                gx = int(particle.center_x / self.tile_size)
                gy = int(particle.center_y / self.tile_size)
                
                is_visible = False
                if self.visibility_grid and 0 <= gy < len(self.visibility_grid) and 0 <= gx < len(self.visibility_grid[0]):
                     is_visible = self.visibility_grid[gy][gx]
                elif (gx, gy) in self.visible_tiles:
                     is_visible = True
                
                if is_visible:
                    is_visible = self._check_line_of_sight((gx, gy))

                # Управление видимостью вместо альфы, чтобы не ломать жизненный цикл частиц
                particle.visible = is_visible 


    def update_visibility(self):
        self.visible_tiles.clear()

        if not self.player or not self.dungeon_map:
            return

        # Используем сеточную позицию игрока для стабильности обзора
        # Используем pos вместо draw_pos чтобы избежать дергания
        player_x, player_y = self.player.pos

        # Ограничиваем координаты границами карты
        player_x = max(0, min(self.dungeon_map.map_width - 1, player_x))
        player_y = max(0, min(self.dungeon_map.map_height - 1, player_y))

        # Получаем текущую комнату игрока
        current_room_id = self.dungeon_map.get_room_id(player_x, player_y)

        # Проверяем, находится ли игрок в комнате босса
        in_boss_room = current_room_id in self.boss_room_ids

        fov_tiles = self.calculate_fov(
            player_x, player_y, self.view_radius, self.player.facing)

        # Ограничиваем видимость только текущей комнатой
        current_room_tiles = set()
        for y in range(self.dungeon_map.map_height):
            for x in range(self.dungeon_map.map_width):
                tile_room_id = self.dungeon_map.get_room_id(x, y)
                if tile_room_id == current_room_id:
                    current_room_tiles.add((x, y))

        # Оставляем в видимых только тайлы из текущей комнаты
        for tile in fov_tiles:
            if tile in current_room_tiles:
                self.visible_tiles.add(tile)


        # Проверяем, побежден ли босс, чтобы определить видимость выхода
        boss_defeated = len(
            [boss for boss in self.bosses if boss.is_alive()]) == 0

        # Если выход существует и босс не побежден, скрываем тайлы выхода
        if self.dungeon_map.exit_pos and not boss_defeated:
            exit_x, exit_y = self.dungeon_map.exit_pos
            # Убираем тайлы выхода из видимости, если босс не побежден
            self.visible_tiles.discard((exit_x, exit_y))
            # Также убираем позиции дверей выхода, если они существуют
            for door_pos in self.dungeon_map.exit_door_positions:
                self.visible_tiles.discard(door_pos)

        if self.dungeon_map and self.dungeon_map.map_width > 0 and self.dungeon_map.map_height > 0:
            width = self.dungeon_map.map_width
            height = self.dungeon_map.map_height

            self.visibility_grid = [[False] * width for _ in range(height)]
            if (not self.explored_grid or
                    len(self.explored_grid) != height or
                    len(self.explored_grid[0]) != width):
                self.explored_grid = [[False] * width for _ in range(height)]

            for x, y in self.visible_tiles:
                if 0 <= x < width and 0 <= y < height:
                    self.visibility_grid[y][x] = True
                    self.explored_grid[y][x] = True
                    self.explored_tiles.add((x, y))

            for x, y in self.explored_tiles:
                if 0 <= x < width and 0 <= y < height:
                    self.explored_grid[y][x] = True

            self.visible_boss_ids = set()
            self.visible_chests = arcade.SpriteList()
            self.visible_dropped_items = arcade.SpriteList()

            # Обновление видимости боссов и предметов теперь происходит в _update_fading для плавности
            # self.visible_boss_ids и self.visible_dropped_items больше не используются для рендеринга
            
            if self.chest_sprites:
                for chest in self.chest_sprites:
                    gx = int(chest.center_x / self.tile_size)
                    gy = int(chest.center_y / self.tile_size)
                    if gx < 0 or gy < 0 or gx >= width or gy >= height:
                        continue
                    
                    # Strict Visibility Check for Chests
                    is_visible = (gx, gy) in self.visible_tiles
                    
                    # Raycasting check (optional but recommended for consistency)
                    if is_visible and hasattr(self, '_check_line_of_sight'):
                        is_visible = self._check_line_of_sight((gx, gy))

                    if is_visible:
                        self.visible_chests.append(chest)

            # Dropped items visibility is handled in _update_fading

    def save_game(self):
        save_file = get_savegame_path()

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
                "save_point_pos": self.save_point_pos,
                "save_point_used": self.save_point_used,
                "mages": [tuple(m.pos) for m in self.mages if m],
                "mage_data": {
                    "pos": self.mages[0].pos,
                    "draw_pos": self.mages[0].draw_pos
                } if self.mages and self.mages[0] else None,
                "mage_spawned": self.mage_spawned,
                "last_seed": getattr(self, "last_seed", "N/A"),
            }
            save_data = {
                'game_data': game_data
            }

            with open(save_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)

            return True

        except Exception as e:
            # print(f"Ошибка сохранения игры: {e}")
            return False

    def load_game(self):
        save_file = get_savegame_path()
        if os.path.exists(save_file):
            try:
                with open(save_file, 'r', encoding='utf-8') as f:
                    save_data = json.load(f)

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
                        self.save_point_pos = tuple(
                            game_data.get("save_point_pos")) if game_data.get("save_point_pos") else None
                        self.save_point_used = game_data.get(
                            "save_point_used", False)
                        self.mage_spawned = game_data.get(
                            "mage_spawned", False)
                        self.last_seed = game_data.get("last_seed", "N/A")
                        # Инициализация боссов при загрузке
                        self.bosses = []
                        self.place_bosses()
                        # Размещаем Мудреца относительно позиции игрока из сохранения,
                        # чтобы он гарантированно появлялся у спавна при загрузке
                        self.place_sage(tuple(player_pos))
                        
                        # Загрузка магов
                        self.mages = []
                        mages_data = game_data.get("mages", [])
                        for pos in mages_data:
                            if pos:
                                mage = MageNPC(self.tile_size, tuple(pos))
                                self.mages.append(mage)
                                
                        self.update_visibility()
                    else:
                        return False

                    return True

            except Exception as e:
                # print(f"Ошибка загрузки игры: {e}")
                pass

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
        
        # Данные информационной панели
        if self.dungeon_map:
            info_text = (f"Уровень: {self.level}\n"
                         f"Размер: {self.dungeon_map.map_width}x{self.dungeon_map.map_height}\n"
                         f"Комнат: {len(self.dungeon_map.rooms)}\n"
                         f"Игрок: {self.player.pos if self.player else '?'}\n"
                         f"Боссов: {len(self.bosses)}\n"
                         f"Seed: {getattr(self, 'last_seed', 'N/A')}")
            
            info_label = arcade.gui.UITextArea(
                text=info_text,
                width=settings.SETTINGS_PANEL_WIDTH,
                height=150,
                font_size=12,
                text_color=arcade.color.LIGHT_GRAY
            )
            main_box.add(info_label)
            
            # Сохранение информации в лог
            logger = GameLogger()
            logger.log(f"Info Panel Opened: {info_text.replace(chr(10), ', ')}")

        buttons_box = arcade.gui.UIBoxLayout(vertical=True, space_between=15)

        save_text = "Сохранить игру"
        save_button = arcade.gui.UIFlatButton(
            text=save_text,
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

        # Кнопка читов (Только если включена)
        if ProjectSettings.CHEATS_ENABLED:
            cheats_button = arcade.gui.UIFlatButton(
                text="Читы",
                width=settings.SETTINGS_PANEL_WIDTH - 20,
                height=settings.BUTTON_HEIGHT
            )
            cheats_button.style = {
                "normal": {
                    "bg_color": arcade.color.PURPLE,
                    "border_color": arcade.color.WHITE,
                    "border_width": 2
                },
                "hover": {
                    "bg_color": arcade.color.MEDIUM_PURPLE,
                    "border_color": arcade.color.WHITE,
                    "border_width": 2
                },
                "press": {
                    "bg_color": arcade.color.PURPLE,
                    "border_color": arcade.color.WHITE,
                    "border_width": 2
                }
            }
            cheats_button.on_click = self.on_cheats_click
            buttons_box.add(cheats_button)

        # Кнопка перезапуска с читами
        restart_cheats_button = arcade.gui.UIFlatButton(
            text="Перезапуск с читами",
            width=settings.SETTINGS_PANEL_WIDTH - 20,
            height=settings.BUTTON_HEIGHT
        )
        restart_cheats_button.style = {
            "normal": {
                "bg_color": arcade.color.DARK_BLUE,
                "border_color": arcade.color.WHITE,
                "border_width": 2
            },
            "hover": {
                "bg_color": arcade.color.BLUE,
                "border_color": arcade.color.WHITE,
                "border_width": 2
            },
            "press": {
                "bg_color": arcade.color.DARK_BLUE,
                "border_color": arcade.color.WHITE,
                "border_width": 2
            }
        }
        restart_cheats_button.on_click = self.on_restart_with_cheats_click
        buttons_box.add(restart_cheats_button)

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

    def on_save_game_click(self, event):
        if self.save_game():
            pass # print("Игра сохранена!")
        else:
            pass # print("Ошибка сохранения игры!")

    def on_restart_with_cheats_click(self, event):
        import subprocess
        import sys
        
        # Получение корневой директории (где находится run.py)
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        run_script = os.path.join(root_dir, "run.py")
        
        # Определение, должна ли быть отключена музыка (сохранение флага)
        args = [sys.executable, run_script, "--wc"]
        if not ProjectSettings.MUSIC_ENABLED:
            args.append("--wom")
            
        # Запуск нового процесса
        subprocess.Popen(args)
        
        # Закрытие текущего окна/процесса
        arcade.close_window()

    def on_cheats_click(self, event):
        self.setup_cheats_menu()

    def setup_cheats_menu(self):
        self.pause_manager.clear()
        settings = ProjectSettings.Settings
        
        main_box = arcade.gui.UIBoxLayout(vertical=True, space_between=15)
        
        title_label = arcade.gui.UILabel(
            text="ЧИТЫ",
            font_size=32,
            text_color=arcade.color.WHITE,
            width=settings.SETTINGS_PANEL_WIDTH,
            align="center"
        )
        main_box.add(title_label)
        
        buttons_box = arcade.gui.UIBoxLayout(vertical=True, space_between=15)
        
        # 1. Level 20
        lvl20_btn = arcade.gui.UIFlatButton(
            text="Перейти на 20 уровень",
            width=settings.SETTINGS_PANEL_WIDTH - 20,
            height=settings.BUTTON_HEIGHT
        )
        lvl20_btn.on_click = self.on_cheat_level_20
        buttons_box.add(lvl20_btn)

        # 1.5. Level 40
        lvl40_btn = arcade.gui.UIFlatButton(
            text="Перейти на 40 уровень",
            width=settings.SETTINGS_PANEL_WIDTH - 20,
            height=settings.BUTTON_HEIGHT
        )
        lvl40_btn.on_click = self.on_cheat_level_40
        buttons_box.add(lvl40_btn)
        
        # 2. Next Level
        next_lvl_btn = arcade.gui.UIFlatButton(
            text="Следующий уровень",
            width=settings.SETTINGS_PANEL_WIDTH - 20,
            height=settings.BUTTON_HEIGHT
        )
        next_lvl_btn.on_click = self.on_cheat_next_level
        buttons_box.add(next_lvl_btn)
        
        # 3. Reveal Map
        map_btn = arcade.gui.UIFlatButton(
            text="Открыть карту",
            width=settings.SETTINGS_PANEL_WIDTH - 20,
            height=settings.BUTTON_HEIGHT
        )
        map_btn.on_click = self.on_cheat_reveal_map
        buttons_box.add(map_btn)
        
        # 4. One Hit Kill
        kill_text = "Включить One Hit Kill"
        if getattr(self, 'cheats_one_hit_kill', False):
            kill_text = "Выключить One Hit Kill"
            
        kill_btn = arcade.gui.UIFlatButton(
            text=kill_text,
            width=settings.SETTINGS_PANEL_WIDTH - 20,
            height=settings.BUTTON_HEIGHT
        )
        kill_btn.on_click = self.on_cheat_kill_all
        buttons_box.add(kill_btn)
        
        shield_text = f"КД щита: {self.shield_cooldown:.1f} сек"
        shield_btn = arcade.gui.UIFlatButton(
            text=shield_text,
            width=settings.SETTINGS_PANEL_WIDTH - 20,
            height=settings.BUTTON_HEIGHT
        )
        shield_btn.on_click = self.on_cheat_cycle_shield_cooldown
        buttons_box.add(shield_btn)

        # Назад
        back_btn = arcade.gui.UIFlatButton(
            text="Назад",
            width=settings.SETTINGS_PANEL_WIDTH - 20,
            height=settings.BUTTON_HEIGHT
        )
        back_btn.on_click = lambda e: self.setup_pause_menu()
        buttons_box.add(back_btn)
        
        main_box.add(buttons_box)
        
        anchor_layout = arcade.gui.UIAnchorLayout()
        anchor_layout.add(
            child=main_box,
            anchor_x="center_x",
            anchor_y="center_y"
        )
        self.pause_manager.add(anchor_layout)

    def on_cheat_cycle_shield_cooldown(self, event):
        self.cheat_activation_count += 1
        values = [5.0, 3.0, 1.0]
        current = self.shield_cooldown
        if current not in values:
            self.shield_cooldown = values[0]
        else:
            index = values.index(current)
            self.shield_cooldown = values[(index + 1) % len(values)]
        self.setup_cheats_menu()

    def on_cheat_level_20(self, event):
        self.cheat_activation_count += 1
        self.level = 20
        self.map_payload = None
        self.show_pause_menu = False
        self.pause_manager.disable()
        self.manager.disable()
        self.setup_game()

    def on_cheat_level_40(self, event):
        self.cheat_activation_count += 1
        self.level = 40
        self.map_payload = None
        self.show_pause_menu = False
        self.pause_manager.disable()
        self.manager.disable()
        self.stop_suspense_music()
        self.reset_level_music()
        self.setup_game()
        self.play_game_music()
        
    def on_cheat_next_level(self, event):
        self.cheat_activation_count += 1
        self.level += 1
        self.map_payload = None
        self.show_pause_menu = False
        self.pause_manager.disable()
        self.manager.disable()
        self.setup_game()
        
    def on_cheat_reveal_map(self, event):
        self.cheat_activation_count += 1
        if self.dungeon_map:
            for y in range(self.dungeon_map.map_height):
                for x in range(self.dungeon_map.map_width):
                    self.visible_tiles.add((x, y))
                    self.explored_tiles.add((x, y))
            if self.visibility_grid:
                 for y in range(len(self.visibility_grid)):
                     for x in range(len(self.visibility_grid[0])):
                         self.visibility_grid[y][x] = True
            if self.explored_grid:
                 for y in range(len(self.explored_grid)):
                     for x in range(len(self.explored_grid[0])):
                         self.explored_grid[y][x] = True
        
        # Обновление миникарты/рендера при необходимости, но следующий вызов отрисовки обработает это
        
    def on_cheat_kill_all(self, event):
        self.cheat_activation_count += 1
        self.cheats_one_hit_kill = not getattr(self, 'cheats_one_hit_kill', False)
        self.setup_cheats_menu() # Обновление текста кнопки

    def on_return_to_menu_click(self, event):
        self.stop_game_music()
        if self.window:
            import arcade
            arcade.schedule(lambda dt: self._switch_to_start_window(), 0)

    def _switch_to_start_window(self):
        """Переключает на стартовое окно в основном потоке, чтобы избежать проблем с контекстом OpenGL"""
        if self.window:
            from windows.start_window import StartWindow
            start_view = StartWindow()
            start_view.play_main_music()
            self.window.show_view(start_view)

    def on_resume_click(self, event):
        self.show_pause_menu = False
        self.pause_manager.disable()
        self.manager.disable()

    def apply_frame_limit(self):
        if not hasattr(self, 'window') or not self.window:
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

    def on_show_view(self):
        self.manager.disable()
        arcade.set_background_color(ProjectSettings.BACKGROUND_COLOR)

        if self.window:
            if self.camera is None:
                self.camera = arcade_camera.Camera2D()
            self.screen_width = self.window.width
            self.screen_height = self.window.height
            self.camera_window_width = self.screen_width * 0.3
            self.camera_window_height = self.screen_height * 0.3
            tile_size = self.tile_size
            if self.player and self.player.pos:
                start_cam_x = self.player.pos[0] * tile_size + tile_size // 2
                start_cam_y = self.player.pos[1] * tile_size + tile_size // 2
                self.camera.position = (start_cam_x, start_cam_y)
                self.camera_target_pos = (start_cam_x, start_cam_y)
            self.apply_frame_limit()

        self.show_pause_menu = False
        self.pause_manager.disable()

        # История показывается в LoadingView

        pass

    def on_hide_view(self):
        self.manager.disable()
        self.pause_manager.disable()

    def on_draw(self):
        self.clear()

        if self.camera:
            self.camera.use()
            self.draw_map()  # Здесь рисуются стены, пол, игроки и боссы, Sage, Merchant, Mages
            
            # Отрисовка взрывчатки и взрывов
            if hasattr(self, 'explosives_list') and self.explosives_list:
                visible_explosives = arcade.SpriteList()
                
                # Culling bounds
                cull_margin = self.tile_size * 2
                cam_x, cam_y = self.camera.position
                half_w = (self.window.width // 2) if self.window else 0
                half_h = (self.window.height // 2) if self.window else 0
                cull_left = cam_x - half_w - cull_margin
                cull_right = cam_x + half_w + cull_margin
                cull_bottom = cam_y - half_h - cull_margin
                cull_top = cam_y + half_h + cull_margin

                for explosive in self.explosives_list:
                    # Frustum Culling
                    if not (cull_left < explosive.center_x < cull_right and cull_bottom < explosive.center_y < cull_top):
                        continue

                    gx = int(explosive.center_x / self.tile_size)
                    gy = int(explosive.center_y / self.tile_size)
                    
                    is_visible = False
                    if self.visibility_grid and 0 <= gy < len(self.visibility_grid) and 0 <= gx < len(self.visibility_grid[0]):
                         is_visible = self.visibility_grid[gy][gx]
                    elif (gx, gy) in self.visible_tiles:
                         is_visible = True
                    
                    # Raycasting
                    if is_visible:
                        is_visible = self._check_line_of_sight((gx, gy))

                    if is_visible:
                        visible_explosives.append(explosive)
                
                if len(visible_explosives) > 0:
                    visible_explosives.draw()
            
            if hasattr(self, 'explosions_list') and self.explosions_list:
                # Отрисовка только видимых взрывов и частиц
                visible_explosions = arcade.SpriteList()
                for particle in self.explosions_list:
                    # Frustum Culling
                    if not (cull_left < particle.center_x < cull_right and cull_bottom < particle.center_y < cull_top):
                        continue

                    gx = int(particle.center_x / self.tile_size)
                    gy = int(particle.center_y / self.tile_size)
                    
                    is_visible = (gx, gy) in self.visible_tiles
                    
                    # Raycasting
                    if is_visible:
                        is_visible = self._check_line_of_sight((gx, gy))
                    
                    if is_visible:
                        visible_explosions.append(particle)
                
                if len(visible_explosions) > 0:
                    visible_explosions.draw()

            # Отрисовка портала выхода (Красный квадрат)
            if self.dungeon_map and not self.dungeon_map.exit_door_closed and self.dungeon_map.exit_pos:
                ex, ey = self.dungeon_map.exit_pos
                
                # Visibility Check for Exit Portal
                is_visible = (ex, ey) in self.visible_tiles
                
                # Raycasting
                if is_visible:
                     is_visible = self._check_line_of_sight((ex, ey))
                
                if is_visible:
                    # Используем draw_lrbt_rectangle_filled, так как draw_rectangle_filled может отсутствовать
                    arcade.draw_lrbt_rectangle_filled(
                        ex * self.tile_size,
                        (ex + 1) * self.tile_size,
                        ey * self.tile_size,
                        (ey + 1) * self.tile_size,
                        arcade.color.RED
                    )
            
            # Отрисовка умирающих боссов
            if self.dying_bosses:
                # Calculate culling bounds
                tile_size = self.tile_size
                cam_x, cam_y = self.camera.position
                half_w = (self.window.width // 2) if self.window else 0
                half_h = (self.window.height // 2) if self.window else 0
                cull_margin = tile_size * 2
                cull_left = cam_x - half_w - cull_margin
                cull_right = cam_x + half_w + cull_margin
                cull_bottom = cam_y - half_h - cull_margin
                cull_top = cam_y + half_h + cull_margin

                for boss in self.dying_bosses:
                    # Frustum Culling
                    bx, by = boss.draw_pos if hasattr(boss, 'draw_pos') else boss.pos
                    if not (cull_left < bx < cull_right and cull_bottom < by < cull_top):
                        continue
                    
                    # Visibility Check
                    gx = int(bx / self.tile_size)
                    gy = int(by / self.tile_size)
                    is_visible = False
                    if self.visibility_grid and 0 <= gy < len(self.visibility_grid) and 0 <= gx < len(self.visibility_grid[0]):
                        is_visible = self.visibility_grid[gy][gx]
                    elif (gx, gy) in self.visible_tiles:
                        is_visible = True
                    
                    # Raycasting check if visible
                    if is_visible:
                         is_visible = self._check_line_of_sight((gx, gy))

                    if is_visible:
                        if hasattr(boss, 'sprite_list') and boss.sprite_list:
                             boss.sprite_list.draw()
                        elif hasattr(boss, 'sprite'):
                             boss.sprite.draw()
                        if hasattr(boss, 'death_particles'):
                             boss.death_particles.draw()

        # Возвращаемся к UI камере для отрисовки интерфейса
        self.ui_camera.use()
        if getattr(self, "debug_show_sage_info", False) and self.sage and self.window:
            try:
                sx, sy = int(self.sage.pos[0]), int(self.sage.pos[1])
                vis = False
                if self.visibility_grid and 0 <= sy < len(self.visibility_grid) and 0 <= sx < len(self.visibility_grid[0]):
                    vis = self.visibility_grid[sy][sx]
                elif (sx, sy) in self.visible_tiles:
                    vis = True
                text = f"Sage at {sx},{sy} visible={vis}"
                arcade.draw_text(text, 10, self.window.height - 20, arcade.color.LIGHT_BLUE, 14)
            except Exception:
                pass

        if self.player and hasattr(self.player, "damage_effect_timer") and hasattr(self.player, "damage_effect_duration"):
            if self.player.damage_effect_timer > 0.0 and self.player.damage_effect_duration > 0.0:
                t = self.player.damage_effect_timer / self.player.damage_effect_duration
                t = max(0.0, min(1.0, t))
                alpha = int(120 * t)
                arcade.draw_lrbt_rectangle_filled(
                    0,
                    self.window.width if self.window else 0,
                    0,
                    self.window.height if self.window else 0,
                    (255, 0, 0, alpha)
                )
        
        # Отрисовка интерфейса щита
        if self.shield_active:
             arcade.draw_text(f"ЩИТ АКТИВЕН: {self.shield_timer:.1f}", 
                              self.window.width // 2, 
                              self.window.height - 100, 
                              arcade.color.CYAN, 
                              20, 
                              anchor_x="center")
        elif self.shield_cooldown_timer > 0:
             arcade.draw_text(f"ПЕРЕЗАРЯДКА ЩИТА: {self.shield_cooldown_timer:.1f}", 
                              self.window.width // 2, 
                              self.window.height - 100, 
                              arcade.color.ORANGE, 
                              20, 
                              anchor_x="center")

        if self.show_pause_menu:
            self.pause_manager.draw()
        elif self.current_story_line or (self.story_lines and len(self.story_lines) > 0):
            # Если есть текст истории или еще есть строки для показа, показываем UI истории
            if not self.story_manager._enabled:
                self.story_manager.enable()
            self.story_manager.draw()
            # Также отрисовываем текст истории
            self.draw_story_text()
        else:
            # Скрываем UI истории если текст закончился
            if self.story_manager._enabled:
                self.story_manager.disable()
            
            # HUD активного предмета
            if self.player and hasattr(self.player, 'get_selected_active_item'):
                key, count = self.player.get_selected_active_item()
                # Рисуем фон для HUD
                arcade.draw_lrbt_rectangle_filled(10, 230, 20, 80, (0, 0, 0, 150))
                
                color = arcade.color.YELLOW
                if count == 0:
                    color = arcade.color.GRAY
                
                item_names = {"bomb": "БОМБА", "dynamite": "ДИНАМИТ", "medkit": "МЯСО"}
                name_ru = item_names.get(key, key.upper())
                
                # Явно рисуем ТОЛЬКО текст, чтобы избежать путаницы с иконками
                arcade.draw_text(f"Активный: {name_ru} x{count}", 20, 60, color, 14, bold=True)
                
                arcade.draw_text("[Z]Сменить [F]Исп. [R]Взорвать", 20, 35, arcade.color.WHITE, 10)

            self.draw_player_health()
            self.draw_death_message()
            self.draw_minimap()
            self.draw_mage_hud()

        # Наложение вспышки экрана
        if self.screen_flash_timer > 0 and self.screen_flash_duration > 0:
             alpha = int(255 * (self.screen_flash_timer / self.screen_flash_duration))
             alpha = max(0, min(255, alpha))
             # Убеждаемся, что цвет имеет RGB компоненты
             c = self.screen_flash_color
             if len(c) == 4:
                 c = c[:3]
             arcade.draw_lrbt_rectangle_filled(
                 0, self.window.width, 0, self.window.height,
                 (*c, alpha)
             )

        if self.loading_overlay_active and self.window:
            w = self.window.width
            h = self.window.height
            t = self.loading_overlay_timer
            fin = self.loading_overlay_fade_in
            fout = self.loading_overlay_fade_out
            dur = self.loading_overlay_duration
            alpha_bg = 180
            if t < fin:
                k = max(0.0, min(1.0, t / max(0.0001, fin)))
                a = int(alpha_bg * k)
            elif t > dur - fout:
                k = max(0.0, min(1.0, (dur - t) / max(0.0001, fout)))
                a = int(alpha_bg * k)
            else:
                a = alpha_bg
            arcade.draw_lrbt_rectangle_filled(0, w, 0, h, (0, 0, 0, a))
            cx = w // 2
            cy = h // 2
            text = "Генерация карты..."
            offset = int(min(w, h) * 0.04)
            arcade.draw_text(text, cx, cy + offset, arcade.color.WHITE, 28, anchor_x="center", anchor_y="center", bold=True)
            r = min(w, h) * 0.06
            arcade.draw_arc_outline(cx, cy - int(r * 2.0), int(r * 2.0), int(r * 2.0), arcade.color.DARK_GRAY, 0, 360, 6)
            sa = self.loading_spinner_angle
            arcade.draw_arc_outline(cx, cy - int(r * 2.0), int(r * 2.0), int(r * 2.0), arcade.color.LIGHT_BLUE, sa, sa + 120, 8)

        # Отрисовка диалогового окна мага (поверх всего)
        if self.mage_dialog:
            self.mage_dialog.draw()
        
        # Отрисовка оверлея окончания игры
        if self.game_over:
             arcade.draw_lrbt_rectangle_filled(
                0,
                self.window.width if self.window else 0,
                0,
                self.window.height if self.window else 0,
                (0, 0, 0, min(255, int(self.death_sequence_timer * 100)))
            )
             if self.death_sequence_timer > 1.0:
                arcade.draw_text(
                    "ПОРАЖЕНИЕ",
                    self.window.width // 2,
                    self.window.height // 2,
                    arcade.color.RED,
                    64,
                    anchor_x="center",
                    anchor_y="center",
                    bold=True
                )

    def draw_passage_opening_effect(self):
        """Рисует эффект открытия прохода"""
        if not self.passage_opening_effect or not self.passage_opening_effect['active']:
            return

        effect = self.passage_opening_effect
        elapsed = time.time() - effect['start_time']

        if elapsed > effect['duration']:
            effect['active'] = False
            return

        # Создаем новые частицы
        if len(effect['particles']) < 100:
            positions = []
            if hasattr(self.dungeon_map, 'exit_door_positions') and self.dungeon_map.exit_door_positions:
                positions = self.dungeon_map.exit_door_positions
            elif hasattr(self.dungeon_map, 'exit_pos') and self.dungeon_map.exit_pos:
                positions = [self.dungeon_map.exit_pos]

            if positions:
                for _ in range(5):
                    pos = random.choice(positions)
                    x = (pos[0] + 0.5) * self.tile_size
                    y = (pos[1] + 0.5) * self.tile_size
                    particle = {
                        'x': x,
                        'y': y,
                        'dx': random.uniform(-2, 2),
                        'dy': random.uniform(3, 7),
                        'size': random.uniform(3, 8),
                        'color': random.choice([arcade.color.WHITE, arcade.color.YELLOW, arcade.color.ORANGE]),
                        'alpha': 255
                    }
                    effect['particles'].append(particle)

        # Обновляем и рисуем частицы
        for p in effect['particles']:
            p['x'] += p['dx']
            p['y'] += p['dy']
            p['alpha'] -= 5
            
            # Проверка видимости частицы
            gx = int(p['x'] / self.tile_size)
            gy = int(p['y'] / self.tile_size)
            
            is_visible = (gx, gy) in self.visible_tiles
            
            if is_visible:
                 is_visible = self._check_line_of_sight((gx, gy))

            if p['alpha'] > 0 and is_visible:
                # Убеждаемся, что берем только RGB от объекта цвета (он может быть RGBA)
                arcade.draw_circle_filled(p['x'], p['y'], p['size'], (*p['color'][:3], p['alpha']))

        # Удаляем старые частицы
        effect['particles'] = [p for p in effect['particles'] if p['alpha'] > 0]


    def on_update(self, delta_time):
        if delta_time > 0:
            self.current_fps = int(1.0 / delta_time)

        if self.game_over:
             self.death_sequence_timer += delta_time
             if self.player:
                 self.player.update_animation(delta_time)
             
             if self.death_sequence_timer >= 4.0:
                 view = GameOverView(self)
                 self.window.show_view(view)
             return

        # Проверка смерти
        if self.player and self.player.health <= 0:
            self.game_over = True
            self.death_sequence_timer = 0.0
            # Воспроизведение звука смерти
            try:
                # Пытаемся найти звук смерти, иначе используем звук удара
                path = self.find_music_file("player_death.wav")
                if not path:
                    path = self.find_music_file("player_hp_down.wav")
                if not path:
                    path = self.find_music_file("game_over_voice.mp3")
                
                if path:
                    arcade.play_sound(arcade.load_sound(path), volume=self.sound_volume)
            except:
                pass
            return

        # Обновление взрывчатки
        if hasattr(self, 'explosives_list') and self.explosives_list:
            self.explosives_list.update(delta_time)
            for explosive in self.explosives_list:
                if explosive.exploded:
                    self.create_explosion(explosive.center_x, explosive.center_y, explosive.explosion_radius, explosive.damage)
                    explosive.remove_from_sprite_lists()

        # Обновление взрывов
        if hasattr(self, 'explosions_list') and self.explosions_list:
            self.explosions_list.update(delta_time)
            
        self.update_music(delta_time)

        if self.sage:
            self.sage.update(delta_time)
            
        # Обновление магов
        for mage in self.mages:
            if mage:
                if self.player:
                    mage.update(delta_time, self.player.draw_pos, self.dungeon_map)
                else:
                    mage.update(delta_time)
        
        # Обновление текста диалога мага, если он открыт
        if self.mage_dialog and self.mage_dialog.is_visible and self.active_mage:
             if self.active_mage.current_response:
                 self.mage_dialog.set_text(self.active_mage.current_response)
        
        # Обновление dying_bosses (анимация смерти)
        if hasattr(self, 'dying_bosses') and self.dying_bosses:
            bosses_to_cleanup = []
            for boss in self.dying_bosses:
                boss.death_timer -= delta_time
                if boss.sprite:
                     boss.sprite.alpha = max(0, int(255 * (boss.death_timer / 2.0)))
                     # Частицы или эффекты
                     pass
                
                if boss.death_timer <= 0:
                    bosses_to_cleanup.append(boss)
            
            for boss in bosses_to_cleanup:
                self.dying_bosses.remove(boss)
                # Окончательная очистка ресурсов босса, если нужно

        # Обновление боссов
        if self.bosses:
            for boss in self.bosses:
                if boss and boss.visible:
                    if self.player:
                        boss.update(delta_time, self.player.draw_pos, self.dungeon_map)
                        
                        # Логика урона от атаки босса
                        if boss.is_attacking and not boss.damage_dealt:
                            # Наносим урон в середине анимации (например, > 30% прогресса)
                            if boss.attack_timer > boss.attack_duration * 0.3:
                                # Снова проверяем дистанцию для честности? Класс Boss отменяет, если слишком далеко, но можно проверить дважды
                                dx = boss.sprite.center_x - self.player.draw_pos[0]
                                dy = boss.sprite.center_y - self.player.draw_pos[1]
                                dist_sq = dx*dx + dy*dy
                                hit_range = boss.attack_range * self.tile_size * 1.5 # Щедрый хитбокс
                                
                                if dist_sq < hit_range * hit_range:
                                    self.player.take_damage(boss.attack_damage)
                                    boss.damage_dealt = True
                                    self.shake_camera(5.0, 0.2)
                        
                        # Запуск музыки босса, если рядом с боссом и он атакует/активен
                        # Простая логика: если босс видим и близко, играем тревожную музыку.
                        # Но музыка босса должна начинаться, когда мы входим в комнату или триггерим босса.
                        # "Определите триггер начала и окончания битвы с боссом"
                        # Начало: Когда босс видит игрока (агро)
                        # Конец: Когда босс умирает (обрабатывается в handle_boss_death)
                        
                        # У босса нет явно открытого свойства состояния "агро", но мы можем проверить, движется ли он к игроку или атакует.
                        # На самом деле у класса Boss есть `is_attacking` и `is_moving`.
                        # Добавим свойство в Boss или проверим здесь.
                        # Если босс активен (движется или атакует), играем музыку.
                        
                        if (boss.is_moving or boss.is_attacking) and not getattr(self, "boss_music_active", False):
                            self.play_suspense_music()
                            self.boss_music_active = True
                        elif not (boss.is_moving or boss.is_attacking) and getattr(self, "boss_music_active", False):
                            # Может не останавливать сразу, ждать смерти или дистанции?
                            # Требование говорит "Начало и Конец битвы".
                            # Битва начинается, когда босс вступает в бой.
                            # Битва заканчивается, когда босс умирает.
                            # Поэтому мы не останавливаем музыку, если босс просто делает паузу.
                            pass
                                    
                    else:
                        boss.update(delta_time, None, self.dungeon_map)

        # Обновление призраков
        if self.ghost_manager:
            # Вычисление вьюпорта для отсечения
            # Вьюпорт центрирован на позиции камеры
            if self.camera and self.camera.position:
                cx, cy = self.camera.position
                # Получаем размер окна (предполагаем стандартный или текущий)
                w = self.window.width
                h = self.window.height
                # Масштабируем вьюпорт по зуму камеры, если применимо (camera.scale не стандартно в 2.6 Camera2D, но проверим документацию, если используется Camera2D)
                # Пока предполагаем масштаб 1:1 или обрабатываем широко
                
                # Определяем прямоугольник вьюпорта (left, right, bottom, top)
                # Позиция камеры обычно левый нижний угол в Arcade, если не использовать центр.
                # Предположим, camera.position это левый нижний угол вида.
                
                # Подождите, Camera2D обычно устанавливает позицию как левый нижний угол видимой области?
                # Или центр? В Arcade 2.6+, use_camera() устанавливает проекцию.
                # Если мы устанавливаем camera.position = (x, y), это обычно левый нижний.
                
                viewport_rect = (cx, cx + w, cy, cy + h)
            else:
                viewport_rect = None
                
            self.ghost_manager.update(delta_time, self.player, self.dungeon_map, viewport_rect)

        if self.merchant:
            self.merchant.update(delta_time, self.dungeon_map, self.player)
            
        # Обновление физики выпавших предметов и подбора
        # Обрабатываем только те предметы, которые движутся или находятся рядом с игроком для оптимизации
        items_to_remove = []
        
        # Оптимизация: обновляем предметы только если они движутся или видимы/близко
        # Но для корректного отскока они должны обновляться до остановки.
        # Как только остановились (is_calm), можно пропустить расчет физики, если они далеко.
        
        # Оптимизация: Отсечение предметов
        player_x, player_y = self.player.draw_pos
        culling_dist = 1000.0 # Дистанция в пикселях для обновления предметов
        
        for item in self.dropped_item_sprites:
            # Проверка дистанции
            dx = item.center_x - player_x
            dy = item.center_y - player_y
            
            # Если далеко И не движется, пропускаем
            is_moving = abs(getattr(item, 'change_x', 0)) > 0.1 or abs(getattr(item, 'change_y', 0)) > 0.1
            if not is_moving and (abs(dx) > culling_dist or abs(dy) > culling_dist):
                continue

            if not is_moving:
                # Если не движется, проверяем подбор только если близко к игроку (простая проверка дистанции или коллизии)
                # Можем пропустить расчет физики
                pass
            else:
                # Физика
                new_x = item.center_x + getattr(item, 'change_x', 0)
                new_y = item.center_y + getattr(item, 'change_y', 0)
                
                # Проверка коллизий со стенами
                grid_x = int(new_x / self.tile_size)
                grid_y = int(new_y / self.tile_size)
                
                if self.dungeon_map.is_walkable(grid_x, grid_y):
                    item.center_x = new_x
                    item.center_y = new_y
                else:
                    # Удар о стену - отскок с затуханием (Исправление механики падения предметов)
                    item.change_x = -item.change_x * 0.5
                    item.change_y = -item.change_y * 0.5
                
                # Трение
                item.change_x = getattr(item, 'change_x', 0) * 0.9
                item.change_y = getattr(item, 'change_y', 0) * 0.9
                
                # Остановка, если скорость мала
                if abs(item.change_x) < 0.1:
                    item.change_x = 0
                if abs(item.change_y) < 0.1:
                    item.change_y = 0
            
            # Логика подбора
            ignore_until = item.properties.get("ignore_until", 0)
            is_calm = abs(getattr(item, 'change_x', 0)) < 0.5 and abs(getattr(item, 'change_y', 0)) < 0.5
            
            if time.time() > ignore_until and is_calm:
                 if self.player and arcade.check_for_collision(self.player.sprite, item):
                     # Добавление в инвентарь или активные предметы
                    icon_id = item.properties.get("icon_id")
                    picked_up = False
                    
                    # Перехват расходников/активных предметов
                    # 43, 44: Meat (+20% HP description) -> Treat as Medkit refill
                    # 45: Potion (+45% HP description) -> Treat as Medkit refill
                    if icon_id in [43, 44, 45]: 
                        if self.player:
                            self.player.active_items["medkit"] += 1
                            picked_up = True
                            
                    elif icon_id == 49: # Бомба
                        if self.player:
                            self.player.active_items["bomb"] += 1
                            picked_up = True
                    
                    elif icon_id == 999: # Rubin
                        self.trigger_end_game()
                        picked_up = True
                            
                    elif icon_id == 50: # Динамит
                        if self.player:
                            self.player.active_items["dynamite"] += 1
                            picked_up = True
                    
                    elif icon_id == 999: # Rubin - Final Item
                        from windows.end_game_view import EndGameView
                        stats = {
                            "chests": self.chest_open_count,
                            "cheats": self.cheat_activation_count
                        }
                        view = EndGameView(self, stats=stats)
                        self.window.show_view(view)
                        return
                            
                    if picked_up:
                         items_to_remove.append(item)
                    elif len(self.inventory) < 10: # Ограничение размера инвентаря
                        self.inventory.append({"icon_id": icon_id})
                        items_to_remove.append(item)
                        self.apply_inventory_effects()
                        # Воспроизведение звука подбора (опционально)
        
        for item in items_to_remove:
            item.remove_from_sprite_lists()
            if item in self.dropped_item_sprites:
                self.dropped_item_sprites.remove(item)

        # Проверяем наличие ожидающего аудио из потока
        if self.pending_audio_path:
            try:
                if os.path.exists(self.pending_audio_path):
                    # Останавливаем предыдущее
                    if self.story_audio_player:
                        try:
                            arcade.stop_sound(self.story_audio_player)
                        except Exception:
                            pass

                    sound = arcade.load_sound(self.pending_audio_path)
                    if sound:
                        self.story_audio_player = arcade.play_sound(sound)
                    self.pending_audio_path = None
            except Exception as e:
                pass

        self.update_story(delta_time)
        if self.window:
            current_width = self.window.width
            current_height = self.window.height
            if current_width != self.screen_width or current_height != self.screen_height:
                self.screen_width = current_width
                self.screen_height = current_height
                self.camera_window_width = self.screen_width * 0.3
                self.camera_window_height = self.screen_height * 0.3
                if self.camera is None:
                    self.camera = arcade_camera.Camera2D()
                self.apply_frame_limit()

        if self.show_pause_menu or self.game_over:
            self.pause_manager.on_update(delta_time)
            return

        # Обновление механики щита
        if self.shield_active:
            self.shield_timer -= delta_time
            if self.shield_timer <= 0:
                self.shield_active = False
                self.shield_cooldown_timer = self.shield_cooldown
                if self.player:
                    self.player.shield_active = False
        elif self.shield_cooldown_timer > 0:
            self.shield_cooldown_timer -= delta_time

        self._update_player_state_from_keys()

        if self.camera and self.window and self.player and self.dungeon_map:
            # Перемещение для легкой сложности
            self.player.update_movement(delta_time)

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
                    if not self.player.is_moving:
                        new_x = self.player.pos[0] + dx
                        new_y = self.player.pos[1] + dy
                        if self.can_move_to(new_x, new_y):
                            if self.player.move(dx, dy):
                                self._on_player_moved()
                    self.move_timer = self.move_cooldown

            self.player.update_animation(delta_time)

            # Синхронизация удара с анимацией
            if self.player.should_strike:
                self.perform_attack_hit_check()
                self.player.should_strike = False

            # Логика следования камеры
            if self.player:
                player_pixel_x, player_pixel_y = self.player.get_pixel_position()

                # Плавное следование камеры
                target_cam_x = player_pixel_x
                target_cam_y = player_pixel_y

                # Используем отдельную переменную для "истинной" позиции камеры без тряски
                if not hasattr(self, 'true_camera_pos') or self.true_camera_pos is None:
                    self.true_camera_pos = self.camera.position if self.camera.position else (target_cam_x, target_cam_y)

                curr_x, curr_y = self.true_camera_pos
                new_x = curr_x + (target_cam_x - curr_x) * self.camera_lerp_speed
                new_y = curr_y + (target_cam_y - curr_y) * self.camera_lerp_speed
                self.true_camera_pos = (new_x, new_y)

                # Применяем тряску
                final_x, final_y = new_x, new_y
                
                if self.camera_shake_duration > 0:
                    self.camera_shake_duration -= delta_time
                    offset_x = (random.random() - 0.5) * self.camera_shake_intensity
                    offset_y = (random.random() - 0.5) * self.camera_shake_intensity
                    final_x += offset_x
                    final_y += offset_y
                
                self.camera.position = (final_x, final_y)

            # Обновление эффектов смерти босса
            if self.dying_bosses:
                for boss in self.dying_bosses[:]:
                    boss.death_timer -= delta_time
                    
                    # Затухание
                    if hasattr(boss, 'sprite'):
                        alpha = max(0, int(255 * (boss.death_timer / 2.0)))
                        boss.sprite.alpha = alpha
                    
                    # Создание частиц
                    if False: # random.random() < 0.5:
                        bx, by = boss.draw_pos
                        p = ExplosionParticle(
                            bx, by, 
                            speed=random.uniform(1.0, 3.0), 
                            angle=random.uniform(0, 6.28),
                            color=random.choice([arcade.color.DARK_VIOLET, arcade.color.BLACK, arcade.color.RED]),
                            scale_speed=-0.02
                        )
                        boss.death_particles.append(p)
                    
                    # Обновление частиц
                    if hasattr(boss, 'death_particles'):
                        boss.death_particles.update()

                    if boss.death_timer <= 0:
                        self.dying_bosses.remove(boss)

            # Обновление вспышки экрана
            if self.screen_flash_timer > 0:
                self.screen_flash_timer -= delta_time

        if self.loading_overlay_active:
            self.loading_overlay_timer += delta_time
            self.loading_spinner_angle = (self.loading_spinner_angle + self.loading_spinner_speed * delta_time) % 360.0
            if self.loading_overlay_timer >= self.loading_overlay_duration:
                self.loading_overlay_active = False
                self.loading_overlay_timer = 0.0
            else:
                self.camera_shake_intensity = 0

            # Обновление регенерации здоровья игрока
            if self.player and self.player.is_alive():
                self.player.update_health_regen(delta_time)

            # Проверка смерти игрока
            if self.player and not self.player.is_alive() and self.player.is_dead:
                if self.player_dead_message is None:  # Показываем сообщение только один раз
                    self.handle_player_death()

            # Проверка смерти боссов и их действий
            any_boss_active = False
            # Используем копию списка для безопасного удаления
            for boss in self.bosses[:]:
                if not boss:
                    continue
                if not boss.is_alive():
                    self.handle_boss_death(boss)
                    continue
                if not (self.player and self.player.is_alive()):
                    continue
                player_pixel_pos = self.player.draw_pos
                player_room_id = self.dungeon_map.get_room_id(
                    self.player.pos[0], self.player.pos[1])
                boss_room_id = self.dungeon_map.get_room_id(
                    boss.pos[0], boss.pos[1])
                
                # Проверка дистанции для активации (погоня разрешена, если близко, даже если в другой комнате)
                dist_to_player = math.sqrt(
                    (boss.draw_pos[0] - player_pixel_pos[0])**2 + 
                    (boss.draw_pos[1] - player_pixel_pos[1])**2
                )
                activation_dist = 15 * self.tile_size # 15 тайлов
                
                is_active = False
                if boss_room_id is not None and boss_room_id == player_room_id:
                    is_active = True
                elif dist_to_player < activation_dist:
                    is_active = True

                if is_active:
                    any_boss_active = True


                # Обновляем и двигаем врага
                if is_active:
                    boss.update(delta_time, player_pixel_pos)
                    boss.move_towards_player(
                        player_pixel_pos, 
                        delta_time,
                        lambda x, y: self.dungeon_map.is_walkable(x, y)
                    )
                    # Атака возможна только если враг видим игроку
                    visible = False
                    if self.visibility_grid:
                        bx, by = boss.pos[0], boss.pos[1]
                        if 0 <= by < len(self.visibility_grid) and 0 <= bx < len(self.visibility_grid[0]):
                            visible = self.visibility_grid[by][bx]
                    else:
                        visible = tuple(boss.pos) in self.visible_tiles
                    
                    # Логика атаки
                    if visible and boss.attack_player(player_pixel_pos):
                        if not self.shield_active and random.random() >= self.player_dodge_chance:
                            self.player.take_damage(boss.attack_damage)
                elif boss.boss_type != "Caveman Boss":
                    # Если враг (не босс) в другой комнате, он бродит
                    boss.update(delta_time, None)
                    boss.wander(delta_time, lambda x, y: self.dungeon_map.is_walkable(x, y))

            # Логика музыки босса
            if any_boss_active and not getattr(self, "boss_music_active", False):
                self.play_suspense_music()
                self.boss_music_active = True
            elif not any_boss_active and getattr(self, "boss_music_active", False):
                self.stop_suspense_music()
                self.play_game_music()
                self.boss_music_active = False

            # Проверка смерти игрока (если еще не обработана)
            if self.player and not self.player.is_alive() and not self.player_dead_message:
                self.handle_player_death()

            if self.ambient_sprites and self.dungeon_map:
                map_pixel_w = self.dungeon_map.map_width * self.tile_size
                map_pixel_h = self.dungeon_map.map_height * self.tile_size
                
            # Обновление магов
            if getattr(self, "mages", None):
                for mage in self.mages:
                    mage.update(delta_time)
                for s in self.ambient_sprites:
                    s.center_x += s.change_x
                    s.center_y += s.change_y
                    if s.center_x < 0:
                        s.center_x = map_pixel_w
                    elif s.center_x > map_pixel_w:
                        s.center_x = 0
                    if s.center_y < 0:
                        s.center_y = map_pixel_h
                    elif s.center_y > map_pixel_h:
                        s.center_y = 0

            if self.damage_buff_timer > 0:
                self.damage_buff_timer = max(
                    0.0, self.damage_buff_timer - delta_time)
                if self.damage_buff_timer == 0:
                    self.damage_buff_multiplier = 1.0

            if self.dropped_item_sprites and self.player and self.player.is_alive():
                hits = arcade.check_for_collision_with_list(
                    self.player.sprite, self.dropped_item_sprites)
                for sp in hits:
                    icon_id = getattr(sp, "properties", {}).get("icon_id")
                    effect = ITEM_EFFECTS.get(icon_id)
                    
                    # Если предмет имеет длительность (временный эффект), применяем сразу
                    if effect and "duration" in effect:
                        if "temp_dmg_pct" in effect:
                            self.damage_buff_timer = effect["duration"]
                            self.damage_buff_multiplier = 1.0 + effect["temp_dmg_pct"]
                        sp.remove_from_sprite_lists()
                        continue

                    if len(self.inventory) < 9:
                        self.inventory.append({"icon_id": icon_id})
                        sp.remove_from_sprite_lists()
                        self.apply_inventory_effects()

            # Обновление затухания видимости
            self._update_fading(delta_time)

    def handle_player_death(self):
        """Обрабатывает смерть игрока"""
        try:
            self.stop_suspense_music()
            self.stop_game_music()
        except Exception:
            pass

        # Переключение на экран окончания игры
        # Воспроизведение музыки окончания игры
        from game.logic.music_manager import MusicManager
        MusicManager().play(
            MusicManager.PATH_GAME_OVER,
            MusicManager.PRIORITY_GAME_OVER,
            loop=False,
            volume=getattr(self, 'music_volume', 1.0)
        )
        
        self.game_over = True
        
        stats = {
            "chests": self.chest_open_count,
            "cheats": self.cheat_activation_count
        }
        game_over_view = GameOverView(self, stats=stats)
        self.window.show_view(game_over_view)

    def trigger_end_game(self):
        """Запускает финальную сцену игры"""
        if self.end_game_active:
            return
            
        self.end_game_active = True
        
        # Собираем статистику
        stats = {
            "chests_opened": self.chest_open_count,
            "cheats_activated": self.cheat_activation_count
        }
        
        # Переход к финальному виду
        end_view = EndGameView(self, stats=stats)
        self.window.show_view(end_view)

    def handle_boss_death(self, boss):
        """Обрабатывает смерть босса"""
        if boss in self.bosses:
            self.bosses.remove(boss)
            
            # Логирование смерти босса
            logger = GameLogger()
            logger.log(f"Boss {boss.boss_type} defeated at {boss.pos}")
            
            # Остановка музыки босса (будет затухание)
            self.stop_suspense_music()
            # Возобновление/Воспроизведение обычной музыки уровня
            self.play_game_music()

            # Добавляем босса в список умирающих для анимации
            boss.death_timer = 2.0  # Время анимации смерти
            boss.death_particles = arcade.SpriteList()
            self.dying_bosses.append(boss)

            # Запускаем эффекты
            self.shake_camera(15.0, 1.0)
            self.start_screen_flash(0.5)
            
            # Level 40 Final Boss Drop (Rubin)
            if self.level >= 40: # Boss level check
                rubin_path = os.path.join("resources", "items", "rubin.png")
                # Create drop
                self.spawn_dropped_item(
                    999, # Special ID for Rubin
                    boss.draw_pos[0], boss.draw_pos[1],
                    ignore_player_duration=1.0,
                    velocity=(0, 0),
                    custom_texture_path=rubin_path
                )
            
            # Звуковой эффект
            try:
                # Пытаемся найти звук взрыва или смерти
                sound_path = find_music_file("explosion.wav")
                if not sound_path:
                    sound_path = find_music_file("boss_death.wav")
                
                if sound_path:
                    play_once(sound_path, volume=self.sound_volume)
            except Exception:
                pass
            
            # Если боссов больше нет, открываем выход
            if not self.bosses:
                if self.dungeon_map and self.dungeon_map.exit_pos:
                    ex, ey = self.dungeon_map.exit_pos
                    if 0 <= ex < self.dungeon_map.map_width and 0 <= ey < self.dungeon_map.map_height:
                        self.dungeon_map.map_data[ey][ex] = 3 # Открываем выход
                
                self.trigger_passage_opening_effects()
            
            # Можно добавить эффекты смерти, звуки и т.д.
            cx, cy = self.camera.position

            if self.camera_target_pos is None:
                self.camera_target_pos = (cx, cy)

            player_pixel_x, player_pixel_y = self.player.get_pixel_position()

            # Камера следует за игроком
            target_cx = player_pixel_x
            target_cy = player_pixel_y
            self.camera_target_pos = (target_cx, target_cy)

            target_cam_x, target_cam_y = self.camera_target_pos

            new_x = target_cam_x
            new_y = target_cam_y

            # Камера следует за игроком без ограничений
            new_x = target_cx
            new_y = target_cy

            self.camera.position = (new_x, new_y)

    def _on_player_moved(self):
        if not self.player or not self.dungeon_map:
            return

        # Обновляем видимость при движении на новую клетку
        self.update_visibility()

        pass

        if self.save_point_pos and not self.save_point_used:
            save_x, save_y = self.save_point_pos
            if self.player.is_at_position(save_x, save_y):
                if self.save_game():
                    self.save_point_used = True

        if self.dungeon_map.exit_pos:
            exit_x, exit_y = self.dungeon_map.exit_pos
            # Разрешаем выход только если дверь выхода ОТКРЫТА (т.е. босс побежден)
            # Красный квадрат рисуется только когда exit_door_closed равно False.
            # Также можем проверить тип тайла: он должен быть 3.
            tile_val = self.dungeon_map.get_tile_value(exit_x, exit_y)
            if tile_val == 3 and self.player.is_at_position(exit_x, exit_y) and not self.dungeon_map.exit_door_closed:
                self.advance_level()

        # Музыка в комнате с боссом и появление босса
        player_room_id = self.dungeon_map.get_room_id(
            self.player.pos[0], self.player.pos[1])
        if player_room_id in self.boss_room_ids and not self.exit_music_played:
            # self.play_suspense_music() # Обработано в on_update
            self.exit_music_played = True

            # Показываем босса и делаем тряску экрана
            for boss in self.bosses:
                if boss and not boss.visible:
                    # Делаем видимыми тех боссов, чья комната совпадает
                    boss_room_id = self.dungeon_map.get_room_id(
                        boss.pos[0], boss.pos[1])
                    if boss_room_id == player_room_id:
                        boss.visible = True
                        try:
                            boss.start_powerup(self.sound_volume)
                        except Exception:
                            pass
                        self.shake_camera(10.0, 0.5)  # Тряска экрана

            # Закрываем выход, когда игрок входит в комнату босса
            # self.close_exit_door() # Уже закрыто во время настройки/обновления
            
            # Обновляем видимость, чтобы сразу отобразить изменения
            # Увеличиваем радиус обзора в комнате босса для лучшего освещения
            self.update_visibility()
        elif player_room_id not in self.boss_room_ids and self.exit_music_played:
            # self.stop_suspense_music() # Обработано в on_update
            self.exit_music_played = False
            # self.play_game_music() # Обработано в on_update

    def _check_collisions_and_triggers(self):
        if not self.player or not self.dungeon_map:
            return

        # Получаем позицию персонажа (нижний тайл, где ноги)
        grid_x, grid_y = self.player.get_grid_position()

        # Проверяем коллизию для обоих тайлов персонажа
        # Персонаж занимает 2 тайла по вертикали (y и y+1)
        if not self.can_move_to(grid_x, grid_y):
            # Если текущая позиция непроходима, корректируем позицию
            # Находим ближайшую проходимую позицию
            player_pixel_x, player_pixel_y = self.player.get_pixel_position()
            corrected_x = int(
                (player_pixel_x - self.tile_size // 2) / self.tile_size)
            corrected_y = int(
                (player_pixel_y - self.tile_size // 2) / self.tile_size)

            # Пробуем скорректировать позицию
            if not self.can_move_to(corrected_x, corrected_y):
                # Если не можем двигаться, останавливаем персонажа
                self.player.reset_velocity()
                # Возвращаем на предыдущую валидную позицию
                if self._last_valid_pos:
                    self.player.set_pos(
                        self._last_valid_pos[0], self._last_valid_pos[1])
                return

        # Сохраняем валидную позицию
        self._last_valid_pos = (grid_x, grid_y)

        if self.dungeon_map.exit_pos:
            exit_x, exit_y = self.dungeon_map.exit_pos
            if grid_x == exit_x and grid_y == exit_y:
                self.advance_level()
                return

        if self.save_point_pos and not self.save_point_used:
            save_x, save_y = self.save_point_pos
            if grid_x == save_x and grid_y == save_y:
                if self.save_game():
                    self.save_point_used = True
                    # print("Игра сохранена через точку сохранения!")

        if self.dungeon_map.exit_room_idx is not None:
            # Логика музыки перенесена в on_update (Активное состояние босса)
            pass


        self.update_visibility()

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
                    self.player.facing = 'back' if dy > 0 else 'front'
                else:
                    self.player.facing = 'right' if dx > 0 else 'left'

                if self.is_running:
                    self.player.set_state('running')
                else:
                    self.player.set_state('walking')
            else:
                self.player.set_state('idle')

    def draw_minimap(self):
        if not self.dungeon_map or not self.player:
            return

        if self.ui_camera:
            self.ui_camera.use()

        max_dim = max(self.dungeon_map.map_width, self.dungeon_map.map_height)
        minimap_scale = max(2.0, min(5.0, 420 / max(1, max_dim)))
        minimap_width = int(self.dungeon_map.map_width * minimap_scale)
        minimap_height = int(self.dungeon_map.map_height * minimap_scale)
        minimap_x = self.window.width - minimap_width - 15
        minimap_y = self.window.height - 15

        arcade.draw_lrbt_rectangle_filled(minimap_x, minimap_x + minimap_width,
                                          minimap_y - minimap_height, minimap_y,
                                          (0, 0, 0, 180))

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
                    explored = visible or (x, y) in getattr(
                        self, "explored_tiles", set())

                if not visible and not explored:
                    continue

                mini_x = minimap_x + x * minimap_scale
                mini_y = minimap_y - y * minimap_scale

                if visible:
                    if tile_value == 0:
                        color = arcade.color.LIGHT_GRAY
                    elif tile_value == 1:
                        color = arcade.color.DIM_GRAY
                    elif tile_value == 2:
                        color = arcade.color.LIGHT_BLUE
                    elif tile_value == 3:
                        # Рисуем выход КРАСНЫМ на миникарте только если активен
                        if not self.dungeon_map.exit_door_closed:
                             color = arcade.color.RED
                        else:
                             # Если неактивен/скрыт, рисуем как пол
                             color = arcade.color.LIGHT_BLUE
                    else:
                        color = arcade.color.WHITE
                else:
                    color = (50, 50, 70, 170)

                arcade.draw_lrbt_rectangle_filled(mini_x,
                                                  mini_x + minimap_scale,
                                                  mini_y - minimap_scale,
                                                  mini_y, color)

        player_mini_x = minimap_x + self.player.pos[0] * minimap_scale
        player_mini_y = minimap_y - \
            self.player.pos[1] * minimap_scale
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

    def create_explosion(self, x, y, radius, damage):
        # Создаем визуальный эффект
        # Основная вспышка
        explosion = Explosion(x, y, radius)
        if hasattr(self, 'explosions_list'):
            self.explosions_list.append(explosion)
            
            # Частицы
            for _ in range(30):
                angle = random.uniform(0, 2 * math.pi)
                speed = random.uniform(100, 300) # pixels/sec
                color = random.choice([arcade.color.RED, arcade.color.ORANGE, arcade.color.YELLOW])
                # scale_speed
                scale_speed = random.uniform(-0.02, -0.05)
                p = ExplosionParticle(x, y, speed, angle, color, scale_speed)
                self.explosions_list.append(p)
        
        # Тряска камеры
        self.shake_camera(min(5.0, damage / 10.0), 0.5)

        # Проверка столкновений
        # Игрок
        if self.player:
            px, py = self.player.draw_pos
            dist_sq = (px - x)**2 + (py - y)**2
            if dist_sq <= radius**2:
                # Расчет падения урона
                dist = math.sqrt(dist_sq)
                factor = 1.0 - (dist / radius)
                actual_damage = int(damage * factor * 0.5) # Уменьшенный урон по себе
                if actual_damage > 0:
                    self.player.health = max(0, self.player.health - actual_damage)
                    self.player.damage_effect_timer = self.player.damage_effect_duration
                    
        # Боссы
        if hasattr(self, 'bosses'):
            for boss in self.bosses:
                if boss and boss.is_alive():
                    # Использовать draw_pos для большей точности
                    if hasattr(boss, 'draw_pos'):
                        bx, by = boss.draw_pos
                    else:
                        bx = boss.pos[0] * self.tile_size + self.tile_size / 2
                        by = boss.pos[1] * self.tile_size + self.tile_size / 2
                    
                    dist_sq = (bx - x)**2 + (by - y)**2
                    if dist_sq <= radius**2:
                        dist = math.sqrt(dist_sq)
                        factor = 1.0 - (dist / radius)
                        actual_damage = int(damage * factor)
                        boss.take_damage(actual_damage)
        
        # Маги (Враги)
        if hasattr(self, 'mages'):
            for mage in self.mages:
                if mage: # Маг может быть None, если мертв/удален?
                     # Маг обычно использует draw_pos
                     if hasattr(mage, 'draw_pos'):
                         mx, my = mage.draw_pos
                     else:
                         mx = mage.pos[0] * self.tile_size + self.tile_size / 2
                         my = mage.pos[1] * self.tile_size + self.tile_size / 2
                     
                     dist_sq = (mx - x)**2 + (my - y)**2
                     if dist_sq <= radius**2:
                        # У мага нет take_damage? Это NPC.
                        # Подождите, MageNPC - торговец/квестодатель. Не враг?
                        # Пользователь сказал "The-edges-of-House". Обычно маги дружелюбны?
                        # Перечитываю контекст: "давай сделаем мага маленьким в углу экрана" - Пользователю нравится Маг.
                        # Я не должен вредить дружественным NPC.
                        pass

        # Призраки
        if hasattr(self, 'ghost_manager') and self.ghost_manager and hasattr(self.ghost_manager, 'ghosts'):
             dead_ghosts = []
             for ghost in self.ghost_manager.ghosts:
                 gx, gy = ghost.draw_pos
                 dist_sq = (gx - x)**2 + (gy - y)**2
                 if dist_sq <= radius**2:
                     dist = math.sqrt(dist_sq)
                     factor = 1.0 - (dist / radius)
                     actual_damage = int(damage * factor)
                     ghost.hp -= actual_damage
                     if ghost.hp <= 0:
                         dead_ghosts.append(ghost)
             
             for ghost in dead_ghosts:
                 self.ghost_manager.remove_ghost(ghost)

    def use_current_active_item(self):
        if not self.player:
            return
            
        key, count = self.player.get_selected_active_item()
        if count <= 0:
            return
            
        px, py = self.player.draw_pos
        
        if key == "bomb":
            bomb = Bomb(px, py)
            if hasattr(self, 'explosives_list'):
                self.explosives_list.append(bomb)
            self.player.use_active_item(key)
        elif key == "dynamite":
            dynamite = Dynamite(px, py)
            if hasattr(self, 'explosives_list'):
                self.explosives_list.append(dynamite)
            self.player.use_active_item(key)
        elif key == "medkit":
                # Лечение 25% от максимального здоровья
                if self.player.health < self.player.max_health:
                    heal_amount = self.player.max_health * 0.25
                    self.player.heal(heal_amount)
                    self.player.use_active_item(key)
                    # Визуальный эффект лечения?
            
    def detonate_dynamite(self):
        if not hasattr(self, 'explosives_list'):
            return
        for explosive in self.explosives_list:
            if isinstance(explosive, Dynamite):
                explosive.explode()

    def on_key_press(self, key, modifiers):
        if self.game_over:
            return

        # Отладка: Переход на уровень 20
        if key == arcade.key.F5 and ProjectSettings.CHEATS_ENABLED:
            self.level = 20
            self.setup_game()
            return

        # Чит: Переход на уровень 40 (Запрос пользователя 'P')
        if key == arcade.key.P and ProjectSettings.CHEATS_ENABLED:
            self.level = 40
            self.map_payload = None
            self.stop_suspense_music()
            self.reset_level_music()
            self.setup_game()
            self.play_game_music()
            return

        # Переход к диалогу с магом, если он виден
        if hasattr(self, 'mage_dialog') and self.mage_dialog and self.mage_dialog.is_visible:
            if self.mage_dialog.on_key_press(key, modifiers):
                return

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

        if self.show_pause_menu or self.game_over:
            return

        if key == arcade.key.Z:
            if self.player:
                self.player.cycle_active_item()
        elif key == arcade.key.F:
            if not self.shield_active and self.shield_cooldown_timer <= 0:
                self.shield_active = True
                self.shield_timer = self.shield_duration
                if self.player:
                    self.player.shield_active = True
        elif key == arcade.key.R:
            self.detonate_dynamite()

        if key == arcade.key.E:
            px, py = self.player.draw_pos if self.player else (0, 0)
            
            # Взаимодействие с Мудрецом
            if self.sage:
                sx, sy = self.sage.draw_pos
                dist_sq = (sx - px) ** 2 + (sy - py) ** 2
                # Дистанция взаимодействия - tile_size * 2, квадрат - (tile_size * 2)^2
                if dist_sq < (self.tile_size * 2) ** 2:
                    self.sage.interact()
            
            # Взаимодействие с Торговцем
            if self.merchant:
                mx, my = self.merchant.draw_pos
                dist_sq = (mx - px) ** 2 + (my - py) ** 2
                if dist_sq < (self.tile_size * 2) ** 2:
                    self.merchant.interact()
            
            # Взаимодействие с Магами
            for mage in self.mages:
                if mage:
                    mx, my = mage.draw_pos
                    dist_sq = (mx - px) ** 2 + (my - py) ** 2
                    if dist_sq < (self.tile_size * 2) ** 2:
                        # Запускаем взаимодействие (API call)
                        mage.interact()
                        self.active_mage = mage
                        
                        # Показать диалог
                        if self.mage_dialog:
                            self.mage_dialog.show()
                        break
                        
            # Взаимодействие с сундуками
            if self.chest_sprites:
                # Ищем ближайший сундук
                closest_chest = None
                min_dist_sq = (self.tile_size * 1.5) ** 2
                
                for chest in self.chest_sprites:
                    cx, cy = chest.center_x, chest.center_y
                    dist_sq = (cx - px) ** 2 + (cy - py) ** 2
                    
                    if dist_sq < min_dist_sq:
                        min_dist_sq = dist_sq
                        closest_chest = chest
                
                if closest_chest:
                    is_opened = closest_chest.properties.get("opened", False)
                    if not is_opened:
                        # Открываем сундук
                        closest_chest.properties["opened"] = True
                        self.chest_open_count += 1
                        
                        # Меняем текстуру (если есть открытая)
                        try:
                            open_tex = arcade.load_texture(os.path.join("resources", "map", "tile_0090.png"))
                            closest_chest.texture = open_tex
                        except Exception:
                            pass
                            
                        # Выпадение лута (3-5 предметов)
                        import random
                        num_items = random.randint(3, 5)
                        for _ in range(num_items):
                            # Случайный предмет (кроме мусора)
                            if self.valid_item_ids:
                                item_id = random.choice(list(self.valid_item_ids))
                                # Разброс позиции
                                offset_x = random.randint(-20, 20)
                                offset_y = random.randint(-20, 20)
                                self.spawn_dropped_item(item_id, closest_chest.center_x + offset_x, closest_chest.center_y + offset_y)
            
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
        elif key == arcade.key.SPACE:
            dx = (1 if self.move_hold["right"] else 0) - \
                (1 if self.move_hold["left"] else 0)
            dy = (1 if self.move_hold["up"] else 0) - \
                (1 if self.move_hold["down"] else 0)
            if dx != 0 or dy != 0:
                # Перемещение на легкой сложности
                if not self.player.is_moving:
                    new_x = self.player.pos[0] + dx
                    new_y = self.player.pos[1] + dy
                    if self.can_move_to(new_x, new_y):
                        # Настройка скорости для бега/ходьбы
                        if self.is_running:
                            self.player.move_speed = self.player.base_move_speed * 1.6
                        else:
                            self.player.move_speed = self.player.base_move_speed
                        if self.player.move(dx, dy):
                            self._on_player_moved()
                    self.move_timer = self.move_cooldown
        elif key == arcade.key.F7 and ProjectSettings.CHEATS_ENABLED:
            try:
                if self.player and self.dungeon_map:
                    # print("[Admin] Принудительный спавн мага на позиции игрока")
                    self.place_sage(tuple(self.player.pos))
            except Exception as e:
                pass
                # print(f"[Admin] Ошибка принудительного спавна мага: {e}")
        elif key == arcade.key.F8 and ProjectSettings.CHEATS_ENABLED:
            try:
                # print("[Admin] Случайный спавн мага в коридоре")
                self.place_sage_in_corridor()
            except Exception as e:
                pass
                # print(f"[Admin] Ошибка коридорного спавна мага: {e}")
        elif key == arcade.key.F9 and ProjectSettings.CHEATS_ENABLED:
            self.debug_show_sage_info = not getattr(self, "debug_show_sage_info", False)
            # print(f"[Admin] Показывать инфо о Мудреце: {self.debug_show_sage_info}")
        elif key == arcade.key.F10 and ProjectSettings.CHEATS_ENABLED:
            # Чит: Переход на уровень 40
            self.level = 40
            self.map_payload = None
            self.stop_suspense_music()
            self.reset_level_music()
            self.setup_game()
            self.play_game_music()
        elif key == arcade.key.Q or key == 1081 or key == 1049:  # 1081='й', 1049='Й'
            if 0 <= self.selected_slot < len(self.inventory):
                item = self.inventory[self.selected_slot]
                icon_id = item.get("icon_id")
                px, py = self.player.get_pixel_position()
                
                # Логика выбрасывания предмета с физикой
                # Логика выброса предмета с физикой
                start_dist = 20 # Начальное расстояние (1-2 единицы ~ 20px)
                throw_force = 5.0 # Сила броска
                
                vx, vy = 0.0, 0.0
                
                if self.player.facing == 'left':
                    px -= start_dist
                    vx = -throw_force
                elif self.player.facing == 'right':
                    px += start_dist
                    vx = throw_force
                elif self.player.facing == 'back':
                    py += start_dist
                    vy = throw_force
                else: # front
                    py -= start_dist
                    vy = -throw_force
                    
                self.spawn_dropped_item(icon_id, px, py, ignore_player_duration=1.0, velocity=(vx, vy))
                del self.inventory[self.selected_slot]
                # Сдвигаем инвентарь, если нужно
                if self.selected_slot >= len(self.inventory) and len(self.inventory) > 0:
                    self.selected_slot = len(self.inventory) - 1
                self.apply_inventory_effects()
        else:
            key_1 = getattr(arcade.key, "KEY_1",
                            getattr(arcade.key, "_1", None))
            key_2 = getattr(arcade.key, "KEY_2",
                            getattr(arcade.key, "_2", None))
            key_3 = getattr(arcade.key, "KEY_3",
                            getattr(arcade.key, "_3", None))
            key_4 = getattr(arcade.key, "KEY_4",
                            getattr(arcade.key, "_4", None))
            key_5 = getattr(arcade.key, "KEY_5",
                            getattr(arcade.key, "_5", None))
            key_6 = getattr(arcade.key, "KEY_6",
                            getattr(arcade.key, "_6", None))
            # Ограничение до 6 ячеек (клавиши 1-6)
            if key in (arcade.key.NUM_1, key_1):
                self.selected_slot = 0
            elif key in (arcade.key.NUM_2, key_2):
                self.selected_slot = 1
            elif key in (arcade.key.NUM_3, key_3):
                self.selected_slot = 2
            elif key in (arcade.key.NUM_4, key_4):
                self.selected_slot = 3
            elif key in (arcade.key.NUM_5, key_5):
                self.selected_slot = 4
            elif key in (arcade.key.NUM_6, key_6):
                self.selected_slot = 5
            elif key in (getattr(arcade.key, "NUM_7", None), getattr(arcade.key, "KEY_7", getattr(arcade.key, "_7", None))):
                self.selected_slot = 6
            elif key in (getattr(arcade.key, "NUM_8", None), getattr(arcade.key, "KEY_8", getattr(arcade.key, "_8", None))):
                self.selected_slot = 7
            elif key in (getattr(arcade.key, "NUM_9", None), getattr(arcade.key, "KEY_9", getattr(arcade.key, "_9", None))):
                self.selected_slot = 8
            elif key in (getattr(arcade.key, "NUM_0", None), getattr(arcade.key, "KEY_0", getattr(arcade.key, "_0", None))):
                self.selected_slot = 9
            elif key == arcade.key.ENTER:
                self.loading_overlay_active = True
                self.loading_overlay_timer = 0.0
                self.loading_spinner_angle = 0.0

    def on_key_release(self, key, modifiers):
        if self.game_over:
            return

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

    def get_world_coordinates(self, screen_x, screen_y):
        """Преобразует экранные координаты в мировые"""
        if not self.camera:
            return screen_x, screen_y

        cam_x, cam_y = self.camera.position
        world_x = cam_x + (screen_x - self.window.width / 2)
        world_y = cam_y + (screen_y - self.window.height / 2)
        return world_x, world_y

    def perform_attack_hit_check(self):
        """Проверяет попадания атаки игрока"""
        if not self.player:
            return

        hb = self.player.get_attack_hitbox()
        if not hb:
            return

        damage_mult = 1.0 + self.player.bonus_damage_percent
        if self.damage_buff_timer > 0:
            damage_mult += (self.damage_buff_multiplier - 1.0)
            
        damage = int((self.player.base_damage + self.player.bonus_damage_flat) * damage_mult)
        
        # Логирование расчета урона
        print(f"DEBUG: Damage Calc - Base: {self.player.base_damage}, Flat Bonus: {self.player.bonus_damage_flat}, Pct Bonus: {self.player.bonus_damage_percent}, Buff Mult: {self.damage_buff_multiplier if self.damage_buff_timer > 0 else 1.0}, Final Mult: {damage_mult}, Final Damage: {damage}")
        
        if getattr(self, 'cheats_one_hit_kill', False):
             damage = 999999
        
        # Проверка двойного удара
        hits = 1
        if self.player.has_double_strike:
            hits = 2
            # print("Двойной удар!")

        ax1, ay1, ax2, ay2 = hb
        px, py = self.player.draw_pos

        targets = []
        if self.bosses:
            for boss in self.bosses:
                if boss.is_alive() and boss.visible:
                    bw = getattr(boss.sprite, "width", self.tile_size)
                    bh = getattr(boss.sprite, "height", self.tile_size)
                    bx1 = boss.sprite.center_x - bw * 0.5
                    bx2 = boss.sprite.center_x + bw * 0.5
                    by1 = boss.sprite.center_y - bh * 0.5
                    by2 = boss.sprite.center_y + bh * 0.5
                    if not (ax2 < bx1 or ax1 > bx2 or ay2 < by1 or ay1 > by2):
                        targets.append(boss)

        # Проверка призраков
        if hasattr(self, 'ghosts'):
            for ghost in self.ghosts:
                 if ghost.is_alive():
                     # Призрак использует draw_pos (центр)
                     gx, gy = ghost.draw_pos
                     # Простая проверка радиуса или прямоугольника. Призрак размером с тайл.
                     size = self.tile_size
                     gx1 = gx - size * 0.5
                     gx2 = gx + size * 0.5
                     gy1 = gy - size * 0.5
                     gy2 = gy + size * 0.5
                     
                     if not (ax2 < gx1 or ax1 > gx2 or ay2 < gy1 or ay1 > gy2):
                         targets.append(ghost)

        try:
            swing = arcade.load_sound("resources/sounds/swing.wav")
            arcade.play_sound(swing, volume=self.sound_volume)
        except Exception:
            pass

        for i in range(hits):
            for target in targets:
                 # Нанесение урона цели
                 if hasattr(target, 'take_damage'):
                     target.take_damage(damage)
                     
                     is_dead = False
                     if hasattr(target, 'health'):
                         is_dead = target.health <= 0
                     elif hasattr(target, 'hp'):
                         is_dead = target.hp <= 0
                         
                     if is_dead:
                         if isinstance(target, Boss):
                             self.handle_boss_death(target)
                         elif hasattr(self, 'ghosts') and target in self.ghosts:
                             self.handle_ghost_death(target)

    def handle_ghost_death(self, ghost):
        if ghost in self.ghosts:
            self.ghosts.remove(ghost)
            # Логирование смерти призрака
            # logger = GameLogger()
            # logger.log(f"Ghost defeated at {ghost.pos}")
            
    def on_mouse_press(self, x, y, button, modifiers):
        if self.game_over:
            return

        # Перенаправление в диалог мага, если он видим
        if hasattr(self, 'mage_dialog') and self.mage_dialog and self.mage_dialog.is_visible:
            if self.mage_dialog.on_mouse_press(x, y, button, modifiers):
                return

        if self.show_pause_menu:
            return

        if button == arcade.MOUSE_BUTTON_LEFT:
            if self.player and not self.player.is_attacking and self.player.is_alive():
                self.player.move_hold = self.move_hold
                self.player.is_running = self.is_running
                self.player.attack()
            world_x, world_y = self.get_world_coordinates(x, y)
            for chest in list(self.chest_sprites):
                if not getattr(chest, "properties", None):
                    chest.properties = {}
                if not chest.properties.get("opened") and chest.collides_with_point((world_x, world_y)):
                    chest.properties["opened"] = True
                    self.chest_open_count += 1
                    self.chest_open_count += 1
                    drop_ids = random.sample(
                        list(self.valid_item_ids), k=min(3, len(self.valid_item_ids)))
                    for iid in drop_ids:
                        # Случайная скорость для эффекта взрыва
                        angle = random.uniform(0, 6.28)
                        speed = random.uniform(3.0, 6.0)
                        vx = math.cos(angle) * speed
                        vy = math.sin(angle) * speed
                        
                        self.spawn_dropped_item(
                            iid, chest.center_x, chest.center_y,
                            ignore_player_duration=0.5,
                            velocity=(vx, vy))

        elif button == arcade.MOUSE_BUTTON_RIGHT:
            # Атака босса правой кнопкой мыши
            if self.player and self.player.is_alive():
                # print("Правая кнопка мыши нажата - атака босса")

                # Получаем мировые координаты клика
                world_x, world_y = self.get_world_coordinates(x, y)

                # Поворачиваем игрока к курсору
                player_x, player_y = self.player.draw_pos
                dx = world_x - player_x
                dy = world_y - player_y

                if abs(dx) > abs(dy):
                    self.player.facing = 'right' if dx > 0 else 'left'
                else:
                    self.player.facing = 'back' if dy > 0 else 'front'

                if not self.player.is_attacking:
                    self.player.attack()  # Анимация атаки
                    # Атакуем босса с учетом направления
                    self.attack_boss(target_pos=(world_x, world_y))
            else:
                pass
                # print("Не могу атаковать: игрок мертв или отсутствует")

    def shake_camera(self, intensity, duration):
        """Добавляет тряску камеры"""
        if self.camera:
            self.camera_shake_intensity = intensity
            self.camera_shake_duration = duration
            # Примечание: Фактическое смещение тряски применяется в on_update
            
    def start_screen_flash(self, duration, color=arcade.color.WHITE):
        """Запускает эффект вспышки на экране"""
        self.screen_flash_duration = duration
        self.screen_flash_timer = duration
        self.screen_flash_color = color

    def attack_boss(self, target_pos=None):
        """
        Атакует боссов в направлении курсора или в зависимости от направления игрока.
        target_pos: (world_x, world_y) - точка, куда кликнул игрок.
        """
        if not self.player or not self.bosses:
            return

        player_x, player_y = self.player.draw_pos
        attack_range = self.tile_size * 2.5
        base_damage = 10
        damage = int(base_damage * self.player_damage_multiplier *
                     self.damage_buff_multiplier) + self.player_damage_flat

        # Определяем область атаки
        hit_bosses = []

        if target_pos:
            tx, ty = target_pos
            dx = tx - player_x
            dy = ty - player_y
            attack_dir = math.atan2(dy, dx)  # радианы
        else:
            # Запасной вариант для противостояния
            dirs = {
                'right': 0,
                'left': math.pi,
                'back': math.pi/2,  # Вверх
                'front': -math.pi/2  # Вниз
            }
            attack_dir = dirs.get(self.player.facing, 0)

        # Проверяем всех боссов
        for boss in self.bosses:
            if not boss.is_alive():
                continue

            boss_x, boss_y = boss.draw_pos
            
            # ИСПРАВЛЕНИЕ: Проверяем видимость босса (предотвращаем атаку сквозь стены)
            bx_grid = int(boss_x / self.tile_size)
            by_grid = int(boss_y / self.tile_size)
            
            # Используем сетку видимости, если она доступна, для более точной проверки
            is_visible = False
            if self.visibility_grid and 0 <= by_grid < len(self.visibility_grid) and 0 <= bx_grid < len(self.visibility_grid[0]):
                is_visible = self.visibility_grid[by_grid][bx_grid]
            elif (bx_grid, by_grid) in self.visible_tiles:
                is_visible = True
                
            if not is_visible:
                continue

            # Дистанция
            dist = math.sqrt((boss_x - player_x)**2 + (boss_y - player_y)**2)

            if dist <= attack_range:
                # Угол к боссу
                boss_dx = boss_x - player_x
                boss_dy = boss_y - player_y
                boss_angle = math.atan2(boss_dy, boss_dx)

                # Разница углов
                angle_diff = boss_angle - attack_dir
                # Нормализация угла (от -pi до pi)
                while angle_diff > math.pi:
                    angle_diff -= 2*math.pi
                while angle_diff < -math.pi:
                    angle_diff += 2*math.pi

                # Если босс в секторе 90 градусов (+/- 45)
                if abs(angle_diff) <= math.pi / 4:
                    hit_bosses.append(boss)

        for boss in hit_bosses:
            boss.take_damage(damage)
            if boss.health <= 0:
                self.handle_boss_death(boss)
            else:
                if any(i.get("icon_id") == 17 for i in self.inventory):
                    boss.take_damage(damage)
                    if boss.health <= 0:
                        self.handle_boss_death(boss)

        if not hit_bosses:
            pass
            # print("Промах!")

    def try_move_player(self, dx, dy):
        if not self.player or not self.dungeon_map:
            return

        prev_room_id = self.dungeon_map.get_room_id(
            self.player.pos[0], self.player.pos[1])
        new_x = self.player.pos[0] + dx
        new_y = self.player.pos[1] + dy
        if 0 <= new_x < self.dungeon_map.map_width and 0 <= new_y < self.dungeon_map.map_height:
            if self.can_move_to(new_x, new_y):
                # Перемещение на легкой сложности
                if self.player.move(dx, dy):
                    self._on_player_moved()

                # Проверка входа в комнату с выходом для закрытия двери
                room_id = self.dungeon_map.get_room_id(new_x, new_y)
                if room_id == self.dungeon_map.exit_room_idx and not self.dungeon_map.exit_door_closed:
                    self.close_exit_door()
                    # print("Проход закрыт! Сразитесь с боссом!")

                if self.save_point_pos and not self.save_point_used:
                    save_x, save_y = self.save_point_pos
                    if new_x == save_x and new_y == save_y:
                        if self.save_game():
                            self.save_point_used = True
                            # print("Игра сохранена через точку сохранения!")

                if self.dungeon_map.exit_room_idx is not None:
                    room_id = self.dungeon_map.get_room_id(new_x, new_y)
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
        """Проверяет может ли персонаж переместиться в позицию (x, y)
        Персонаж занимает 1 тайл для более свободного прохода"""
        if not self.dungeon_map:
            return False

        # Проверяем границы карты
        if not (0 <= x < self.dungeon_map.map_width and 0 <= y < self.dungeon_map.map_height):
            return False

        # Персонаж занимает только 1 тайл для более свободного прохода
        if not self.dungeon_map.is_walkable(x, y):
            return False

        return True

    def advance_level(self):
        # Логирование перехода уровня
        logger = GameLogger()
        logger.log(f"Level Transition from {self.level} to {self.level + 1}")
        
        self.level += 1
        self.visible_tiles.clear()
        self.explored_tiles.clear()
        self.stop_suspense_music()
        self.reset_level_music() # Сброс выбора музыки для нового уровня
        self.exit_music_played = False
        # Легкая сложность - нет жесткой системы сохранений
        self.save_point_used = False
        self.map_payload = None
        self.spawn_corner = None
        self.explored_grid = None
        self.visibility_grid = None
        self.setup_game()
        self.play_game_music()

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

        batches = {
            'visible_exit': [],
            'seen_exit': [],
            # Запасной вариант для объектов без текстур
            'visible_wall': [],
            'seen_wall': [],
            'visible_floor': [],
            'seen_floor': []
        }
        
        # Значение -> {'visible': [], 'seen': []}
        texture_batches = {}

        use_grid = self.visibility_grid is not None
        use_explored = self.explored_grid is not None

        view_bottom_clamped = max(0, view_bottom)
        view_top_clamped = min(self.dungeon_map.map_height, view_top)
        view_left_clamped = max(0, view_left)
        view_right_clamped = min(self.dungeon_map.map_width, view_right)

        tile_size_float = float(tile_size)

        for y in range(view_bottom_clamped, view_top_clamped):
            vis_row = self.visibility_grid[y] if use_grid else None
            screen_y = y * tile_size_float
            bottom = screen_y
            top = screen_y + tile_size_float
            cy = screen_y + tile_size_float / 2

            for x in range(view_left_clamped, view_right_clamped):
                if use_grid:
                    visible = vis_row[x]
                else:
                    visible = (x, y) in self.visible_tiles

                explored = False
                if use_explored:
                    explored = self.explored_grid[y][x]
                else:
                    explored = visible or (x, y) in getattr(
                        self, "explored_tiles", set())

                if not visible and not explored:
                    continue

                value = self.dungeon_map.get_tile_value(x, y)
                if value is None:
                    continue

                screen_x = x * tile_size_float
                cx = screen_x + tile_size_float / 2
                
                # Попытка использовать текстуру
                tex = self.dungeon_map.textures.get(value) if hasattr(self.dungeon_map, 'textures') else None
                
                if tex:
                    if value not in texture_batches:
                        texture_batches[value] = {'visible': [], 'seen': []}
                    
                    key = 'visible' if visible else 'seen'
                    texture_batches[value][key].append((cx, cy))
                else:
                    # Логика отката
                    left = screen_x
                    right = screen_x + tile_size_float
                    
                    if value == 3: # Выход
                        key = 'visible_exit' if visible else 'seen_exit'
                        batches[key].append((left, right, bottom, top))
                    elif value == 1: # Стена
                        key = 'visible_wall' if visible else 'seen_wall'
                        batches[key].append((left, right, bottom, top))
                    else: # Пол
                        key = 'visible_floor' if visible else 'seen_floor'
                        batches[key].append((left, right, bottom, top))

        # Отрисовка текстур
        for val, lists in texture_batches.items():
            tex = self.dungeon_map.textures.get(val)
            if not tex:
                continue
            
            # Видимые
            for cx, cy in lists['visible']:
                left = cx - tile_size / 2
                right = cx + tile_size / 2
                bottom = cy - tile_size / 2
                top = cy + tile_size / 2
                rect = arcade.types.Rect(left, right, bottom, top, tile_size, tile_size, cx, cy)
                arcade.draw_texture_rect(tex, rect)
                
            # Виденные (Затемненные)
            color = arcade.types.Color(100, 100, 110)
            for cx, cy in lists['seen']:
                left = cx - tile_size / 2
                right = cx + tile_size / 2
                bottom = cy - tile_size / 2
                top = cy + tile_size / 2
                rect = arcade.types.Rect(left, right, bottom, top, tile_size, tile_size, cx, cy)
                arcade.draw_texture_rect(tex, rect, color=color)

        color_batches = {
            arcade.color.DIM_GRAY: batches['visible_wall'],
            arcade.color.LIGHT_GRAY: batches['visible_floor'],
            (180, 60, 40): batches['visible_exit'],
            (110, 110, 120): batches['seen_wall'],
            (140, 140, 160): batches['seen_exit'],
            (100, 100, 110): batches['seen_floor']
        }

        for color, rects in color_batches.items():
            if rects:
                for left, right, bottom, top in rects:
                    arcade.draw_lrbt_rectangle_filled(
                        left, right, bottom, top, color)

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
                    
                    # Если тайл исследован, не рисуем черный квадрат (оставляем затемненную текстуру)
                    if explored:
                        continue
                        
                    screen_x = x * tile_size
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
            # Отрисовка полоски здоровья игрока над игроком
            self.draw_player_health_above()

        # Проверка появления босса при входе в его комнату
        if self.dungeon_map and self.player and self.bosses:
            player_room_id = self.dungeon_map.get_room_id(
                self.player.pos[0], self.player.pos[1])
            if player_room_id in self.boss_room_ids:
                for boss in self.bosses:
                    if boss and not boss.visible:
                        # Делаем видимыми тех боссов, чья комната совпадает
                        rid = self.dungeon_map.get_room_id(
                            boss.pos[0], boss.pos[1])
                        if rid == player_room_id:
                            boss.visible = True
                            try:
                                boss.start_powerup(self.sound_volume)
                            except Exception:
                                pass
                            self.shake_camera(10.0, 0.5)

        # Frustum Culling Limits (Pixels)
        cull_margin = self.tile_size * 2
        cull_left = cam_x - half_w - cull_margin
        cull_right = cam_x + half_w + cull_margin
        cull_bottom = cam_y - half_h - cull_margin
        cull_top = cam_y + half_h + cull_margin

        for boss in self.bosses:
            if not boss or not boss.is_alive():
                continue
            
            # Frustum Culling
            if not (cull_left < boss.draw_pos[0] < cull_right and cull_bottom < boss.draw_pos[1] < cull_top):
                continue

            # Пропускаем полностью невидимых
            if hasattr(boss, "sprite") and boss.sprite.alpha <= 0:
                continue

            boss.draw()
            
            # Отрисовка обводки (с учетом прозрачности)
            if hasattr(boss, "sprite") and ProjectSettings.DEBUG_MODE:
                cx = boss.sprite.center_x
                cy = boss.sprite.center_y
                r = self.tile_size * 0.7
                alpha = boss.sprite.alpha
                color = (255, 0, 0, alpha)
                arcade.draw_circle_outline(cx, cy, r, color, 3)

        # Отрисовка NPC (Sage, Merchant, Mages)
        if getattr(self, "sage", None):
            # Culling & Alpha Check
            if (cull_left < self.sage.draw_pos[0] < cull_right and cull_bottom < self.sage.draw_pos[1] < cull_top):
                if hasattr(self.sage, "sprite") and self.sage.sprite.alpha > 0:
                    self.sage.draw()
        
        if getattr(self, "merchant", None):
            # Culling & Alpha Check
            if (cull_left < self.merchant.draw_pos[0] < cull_right and cull_bottom < self.merchant.draw_pos[1] < cull_top):
                if hasattr(self.merchant, "sprite") and self.merchant.sprite.alpha > 0:
                    self.merchant.draw()
            
        if getattr(self, "mages", None):
            for mage in self.mages:
                # Frustum Culling
                if not (cull_left < mage.draw_pos[0] < cull_right and cull_bottom < mage.draw_pos[1] < cull_top):
                    continue

                # Alpha Check
                if hasattr(mage, "sprite") and mage.sprite.alpha <= 0:
                     continue

                mage.draw()
                if self.player:
                    # Рисуем UI только если маг видим
                    alpha = 255
                    if hasattr(mage, "sprite"):
                        alpha = mage.sprite.alpha
                    
                    if alpha > 0:
                        mage.draw_ui(self.player.get_pixel_position())

        if self.visible_chests and self.player and self.dungeon_map:
            chests_to_draw = arcade.SpriteList()
            for chest in self.visible_chests:
                # Frustum Culling for chests
                if cull_left < chest.center_x < cull_right and cull_bottom < chest.center_y < cull_top:
                    chests_to_draw.append(chest)
            
            if len(chests_to_draw) > 0:
                chests_to_draw.draw()
                if ProjectSettings.DEBUG_MODE:
                    for chest in chests_to_draw:
                        cx = chest.center_x
                        cy = chest.center_y
                        w = self.tile_size * 0.9
                        h = self.tile_size * 0.9
                        left = cx - w / 2
                        right = cx + w / 2
                        bottom = cy - h / 2
                        top = cy + h / 2
                        arcade.draw_lrbt_rectangle_outline(left, right, bottom, top, arcade.color.GOLD, 2)

        if self.dropped_item_sprites and self.player and self.dungeon_map:
            # Отрисовка предметов с проверкой видимости
            items_to_draw = arcade.SpriteList()
            for item in self.dropped_item_sprites:
                # Frustum Culling
                if not (cull_left < item.center_x < cull_right and cull_bottom < item.center_y < cull_top):
                    continue

                # Visibility Check (Fog of War)
                gx = int(item.center_x / self.tile_size)
                gy = int(item.center_y / self.tile_size)
                
                is_visible = False
                if self.visibility_grid and 0 <= gy < len(self.visibility_grid) and 0 <= gx < len(self.visibility_grid[0]):
                    is_visible = self.visibility_grid[gy][gx]
                elif (gx, gy) in self.visible_tiles:
                    is_visible = True
                
                if is_visible:
                    items_to_draw.append(item)
            
            if len(items_to_draw) > 0:
                items_to_draw.draw()
            
                # Отрисовка обводки для видимых
                if ProjectSettings.DEBUG_MODE:
                    for item in items_to_draw:
                        if item.alpha > 0:
                            cx = item.center_x
                            cy = item.center_y
                            r = self.tile_size * 0.45
                            color = (144, 238, 144, item.alpha)
                            arcade.draw_circle_outline(cx, cy, r, color, 2)

        if self.ambient_sprites:
            # Frustum Culling и проверка видимости для эмбиента
            visible_ambient = arcade.SpriteList()
            for sprite in self.ambient_sprites:
                if cull_left < sprite.center_x < cull_right and cull_bottom < sprite.center_y < cull_top:
                     # Visibility Check
                    gx = int(sprite.center_x / self.tile_size)
                    gy = int(sprite.center_y / self.tile_size)
                    
                    is_visible = False
                    if self.visibility_grid and 0 <= gy < len(self.visibility_grid) and 0 <= gx < len(self.visibility_grid[0]):
                        is_visible = self.visibility_grid[gy][gx]
                    elif (gx, gy) in self.visible_tiles:
                        is_visible = True
                        
                    if is_visible and sprite.alpha > 0:
                        visible_ambient.append(sprite)
            
            if len(visible_ambient) > 0:
                visible_ambient.draw()

        self.draw_minimap()

        # Отрисовка UI здоровья игрока
        self.draw_player_health()

        # Отрисовка сообщения о смерти игрока
        self.draw_death_message()

    def draw_player_health(self):
        """Отрисовка полоски здоровья игрока"""
        if not self.player or not self.window:
            return

        # Используем UI камеру, если она есть
        if hasattr(self, 'ui_camera') and self.ui_camera:
            self.ui_camera.use()

        bar_width = 200
        bar_height = 20
        bar_x = 20
        bar_y = self.window.height - 40

        # Фон полоски
        arcade.draw_lrbt_rectangle_filled(
            bar_x, bar_x + bar_width, bar_y, bar_y + bar_height,
            arcade.color.BLACK
        )

        # Полоска здоровья
        health_value = getattr(self.player, "display_health", self.player.health)
        health_percent = max(0.0, min(1.0, health_value / self.player.max_health))
        health_width = bar_width * health_percent
        health_color = arcade.color.RED if health_percent < 0.3 else (
            arcade.color.YELLOW if health_percent < 0.6 else arcade.color.GREEN
        )
        arcade.draw_lrbt_rectangle_filled(
            bar_x, bar_x + health_width, bar_y, bar_y + bar_height,
            health_color
        )

        # Рамка
        arcade.draw_lrbt_rectangle_outline(
            bar_x, bar_x + bar_width, bar_y, bar_y + bar_height,
            arcade.color.WHITE, 2
        )

        # Текст здоровья
        health_text = f"{int(health_value)}/{self.player.max_health}"
        arcade.draw_text(
            health_text,
            bar_x + bar_width / 2,
            bar_y + bar_height / 2,
            arcade.color.WHITE,
            14,
            anchor_x="center",
            anchor_y="center",
            bold=True
        )
        self.draw_inventory_bar()

    def draw_inventory_bar(self):
        if not self.window:
            return
        self.ui_camera.use()
        slots = 9
        slot_size = 48
        padding = 8
        total_w = slots * slot_size + (slots - 1) * padding
        x0 = (self.window.width - total_w) // 2
        y0 = 20
        inv_list = arcade.SpriteList()
        for i in range(slots):
            left = x0 + i * (slot_size + padding)
            right = left + slot_size
            bottom = y0
            top = y0 + slot_size
            color = arcade.color.DARK_GRAY if i != self.selected_slot else arcade.color.LIGHT_GRAY
            arcade.draw_lrbt_rectangle_filled(left, right, bottom, top, color)
            arcade.draw_lrbt_rectangle_outline(
                left, right, bottom, top, arcade.color.WHITE, 2)
            if i < len(self.inventory):
                icon_id = self.inventory[i].get("icon_id")
                tex = self.item_textures.get(icon_id)
                if tex:
                    cx = (left + right) / 2
                    cy = (bottom + top) / 2
                    sp = arcade.Sprite()
                    sp.texture = tex
                    sp.center_x = cx
                    sp.center_y = cy
                    if getattr(tex, "width", 0):
                        sp.scale = slot_size / tex.width
                    inv_list.append(sp)
        inv_list.draw()
        if 0 <= self.selected_slot < len(self.inventory):
            icon_id = self.inventory[self.selected_slot].get("icon_id")
            desc = self.get_item_description(icon_id)
            if desc:
                tx = self.window.width // 2
                ty = y0 + slot_size + 18
                arcade.draw_text(desc, tx, ty, arcade.color.WHITE,
                                 14, anchor_x="center", anchor_y="bottom")

        # Draw FPS
        arcade.draw_text(
            f"FPS: {self.current_fps}",
            self.window.width - 10,
            self.window.height - 10,
            arcade.color.YELLOW,
            12,
            anchor_x="right",
            anchor_y="top"
        )

    def draw_player_health_above(self):
        """Отрисовка полоски здоровья игрока над игроком"""
        if not self.player or not self.player.is_alive():
            return

        # Сохраняем текущую камеру
        if self.camera:
            self.camera.use()

        bar_width = self.tile_size * 1.5
        bar_height = 8
        bar_x = self.player.draw_pos[0] - bar_width / 2
        bar_y = self.player.draw_pos[1] + self.tile_size / 2 + 10

        # Фон полоски
        arcade.draw_lrbt_rectangle_filled(
            bar_x, bar_x + bar_width, bar_y, bar_y + bar_height,
            arcade.color.BLACK
        )

        # Полоска здоровья
        health_value = getattr(self.player, "display_health", self.player.health)
        health_percent = max(0.0, min(1.0, health_value / self.player.max_health))
        health_width = bar_width * health_percent
        health_color = arcade.color.RED if health_percent < 0.3 else (
            arcade.color.YELLOW if health_percent < 0.6 else arcade.color.GREEN
        )
        arcade.draw_lrbt_rectangle_filled(
            bar_x, bar_x + health_width, bar_y, bar_y + bar_height,
            health_color
        )

        # Рамка
        arcade.draw_lrbt_rectangle_outline(
            bar_x, bar_x + bar_width, bar_y, bar_y + bar_height,
            arcade.color.WHITE, 1
        )

    def draw_death_message(self):
        """Отрисовка сообщения о смерти игрока"""
        if not self.player_dead_message or self.death_message_timer <= 0:
            return

        if not self.window:
            return

        # Используем экранные координаты для UI
        center_x = self.window.width // 2
        center_y = self.window.height // 2

        # Полупрозрачный фон
        alpha = int(200 * min(1.0, self.death_message_timer / 5.0))
        arcade.draw_lrbt_rectangle_filled(
            0, self.window.width, 0, self.window.height,
            (*arcade.color.BLACK[:3], alpha)
        )

        # Большой текст "ИГРОК УМЕР!"
        text_size = 72
        arcade.draw_text(
            self.player_dead_message,
            center_x,
            center_y + 50,
            arcade.color.RED,
            text_size,
            anchor_x="center",
            anchor_y="center",
            bold=True
        )

        # Дополнительный текст
        # sub_text удален как неиспользуемый

    def update_story(self, delta_time):
        """Обновление логики отображения истории"""
        # В оригинальной логике текст исчезает по таймеру,
        # но теперь он будет исчезать только при нажатии кнопки "Далее"
        # Оставляем таймер для отладки, но не используем для скрытия текста
        if self.current_story_line:
            self.story_line_timer -= delta_time
            # Отладочный таймер каждую секунду
            if int(self.story_line_timer + delta_time) != int(self.story_line_timer):
                print(f"Story timer: {int(self.story_line_timer)}")

        # Показываем следующую строку истории только если текущая закончилась
        # или если пользователь нажал "Далее"
        if not self.current_story_line and self.story_lines:
            self.current_story_line = self.story_lines.pop(0)
            # Увеличиваем время до бесконечности, чтобы текст не исчезал по таймеру
            # Текст не исчезает по таймеру
            self.story_line_timer = float('inf')
            pass # print(f"Showing story line: {self.current_story_line[:20]}...")

            # Создаем объект текста один раз для оптимизации
            if self.window:
                text_width = self.window.width * 0.8
                bg_y = self.window.height * 0.2
                self.current_story_text_object = arcade.Text(
                    self.current_story_line,
                    self.window.width // 2,
                    bg_y,
                    arcade.color.WHITE,
                    font_size=18,
                    anchor_x="center",
                    anchor_y="center",
                    width=int(text_width),
                    multiline=True,
                    align="center"
                )
            else:
                print("Warning: Window not ready for story text creation")

            self.play_story_audio(self.current_story_line)

    def draw_story_text(self):
        """Отрисовка текста истории"""
        if not self.current_story_line or not self.window:
            return

        # Рисуем подложку для текста
        bg_height = 100
        bg_y = self.window.height * 0.2
        arcade.draw_lrbt_rectangle_filled(
            0,
            self.window.width,
            bg_y - bg_height // 2,
            bg_y + bg_height // 2,
            (0, 0, 0, 150)
        )

        if self.current_story_text_object:
            self.current_story_text_object.draw()

    def setup_story_ui(self):
        """Настройка UI для отображения истории с кнопкой Далее"""
        self.story_manager.clear()

        # Создаем UI элементы для отображения истории
        # Увеличиваем расстояние между элементами
        main_box = arcade.gui.UIBoxLayout(vertical=True, space_between=30)

        # Добавляем текст истории (временно пустой, будет обновляться в on_draw)
        text_label = arcade.gui.UILabel(
            text="",
            font_size=18,
            text_color=arcade.color.WHITE,
            width=self.window.width * 0.8,
            height=100,  # Увеличиваем высоту для лучшего отображения текста
            multiline=True,
            align="center"
        )
        main_box.add(text_label)

        # Добавляем пустое пространство для увеличения расстояния между текстом и кнопкой
        spacer = arcade.gui.UISpace(
            width=self.window.width * 0.8,
            height=50  # Дополнительное пространство между текстом и кнопкой
        )
        main_box.add(spacer)

        # Кнопка "Далее" - размещаем дальше от текста
        next_button = arcade.gui.UIFlatButton(
            text="Далее",
            width=200,
            height=50
        )
        next_button.style = {
            "normal": {
                "bg_color": arcade.color.DARK_BLUE,
                "border_color": arcade.color.WHITE,
                "border_width": 2
            },
            "hover": {
                "bg_color": arcade.color.BLUE,
                "border_color": arcade.color.WHITE,
                "border_width": 2
            },
            "press": {
                "bg_color": arcade.color.LIGHT_BLUE,
                "border_color": arcade.color.WHITE,
                "border_width": 2
            }
        }
        next_button.on_click = self.on_next_click
        main_box.add(next_button)

        anchor_layout = arcade.gui.UIAnchorLayout()
        anchor_layout.add(
            child=main_box,
            anchor_x="center_x",
            anchor_y="center_y"
        )
        self.story_manager.add(anchor_layout)

    def on_next_click(self, event):
        """Обработка нажатия кнопки 'Далее'"""
        # Пропускаем текущую строку истории
        self.current_story_line = None
        self.current_story_text_object = None
        self.story_line_timer = 0.0

        # Проверяем, есть ли еще строки истории
        if not self.story_lines:
            # Если строк больше нет, скрываем UI истории
            self.story_manager.disable()

    def toggle_story_ui(self, show):
        """Показать или скрыть UI истории"""
        if show:
            self.story_manager.enable()
        else:
            self.story_manager.disable()

    def display_story_text(self):
        """Инициализирует текст истории"""
        # print("Initializing story text...")
        story_text = (
            "Герой — Элиас, скромный картограф и алхимик из приграничного городка Валемар. "
            "Его жена, Лира, талантливая травница, тяжело заболела «Каменной Чумой» — "
            "болезнью, которая постепенно превращает плоть в холодный, инертный камень. "
            "Все известные методы лечения оказались бессильны.\n"
            "В отчаянии Элиас находит старую карту, нарисованную его же рукой много лет назад, "
            "но места на ней он не помнит. Карта ведёт в заброшенное подземелье под Валемаром, "
            "где, по легенде, хранится Сердце Камня — источник энергии, породивший Каменную Чуму.\n"
            "Элиас спускается в подземелье, надеясь уничтожить источник и спасти Лиру."
        )

        self.story_lines = [line.strip()
                            for line in story_text.split('\n') if line.strip()]
        self.current_story_line = None
        self.current_story_text_object = None
        self.story_line_timer = 0.0
        # for i, line in enumerate(self.story_lines):
        #     print(f"Line {i+1}: {line[:30]}...")

    def play_story_audio(self, text):
        """Запускает генерацию и воспроизведение аудио в отдельном потоке"""
        import threading
        # print(f"Starting audio thread for: {text[:20]}...")
        threading.Thread(target=self._generate_and_play_audio_thread, args=(
            text,), daemon=True).start()

    def _generate_and_play_audio_thread(self, text):
        """Фоновый поток для генерации и воспроизведения"""
        try:
            import asyncio
            # print("Running async audio generation...")
            asyncio.run(self._speak_text_async(text))
        except Exception as e:
            # print(f"Ошибка в потоке аудио: {e}")
            pass

    async def _speak_text_async(self, text):
        """Асинхронная генерация и воспроизведение"""
        try:
            # print(f"Generating audio for: {text[:20]}...")
            filename = os.path.join(os.getcwd(), "story_audio_current.mp3")

            # Удаляем старый файл
            if os.path.exists(filename):
                try:
                    os.remove(filename)
                except Exception:
                    pass

            communicate = edge_tts.Communicate(text, 'ru-RU-DmitryNeural')
            await communicate.save(filename)

            if os.path.exists(filename):
                self.pending_audio_path = filename
                # print(f"Audio generated: {filename}")
            else:
                pass
                # print(f"Failed to generate audio file: {filename}")

        except Exception as e:
            pass
            # print(f"Ошибка при озвучивании текста: {e}")
