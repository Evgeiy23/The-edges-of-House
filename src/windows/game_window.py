import arcade
import arcade.gui
import arcade.camera as arcade_camera
import pyglet
import os
import json
import math
import asyncio
import edge_tts
import random
import time
from project import ProjectSettings
from utils import get_config_path, get_savegame_path
from game.logic.music import find_music_file, play_loop, stop_player, play_once
from game.logic.map.storage import generate_and_store_map
from game.entities.player import Player
from game.entities.boss import Boss
from game.map.dungeon_map import DungeonMap
from game.items.effects import ITEM_EFFECTS



class GameWindow(arcade.View):
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
        
        # Always use easy difficulty
        self.DIFFICULTY_EASY = ProjectSettings.Game.DIFFICULTY_EASY
        self.difficulty = difficulty or ProjectSettings.Game.DIFFICULTY_EASY

        self.screen_width = 0
        self.screen_height = 0
        self.map_width = 0
        self.map_height = 0
        self.tile_size = ProjectSettings.Game.TILE_SIZE

        self.dungeon_map = None
        self.player = None
        self.bosses = []  # Список боссов
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
        self.move_cooldown = 0.1
        self.move_timer = 0.0
        self.exit_music_played = False
        self.frame_limit = ProjectSettings.Game.DEFAULT_FRAME_LIMIT
        self.spawn_corner = spawn_corner
        self.map_payload = map_payload
        self.map_name = map_name
        self.minimap_player_draw_pos = None
        self.boss_room_ids = set()
        self.ambient_sprites = arcade.SpriteList()
        self.chest_sprites = arcade.SpriteList()
        self.dropped_item_sprites = arcade.SpriteList()
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

        self.game_music_sound = None
        self.game_music_player = None

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

        # Настройка видимости (всегда полная для легкого уровня)
        self.use_fov = False
        self.view_radius = 20  # Большой радиус для комфортной игры

        self.load_settings()
        if load_save:
            if not self.load_game():
                self.setup_game()
            else:
                self.update_visibility()
        else:
            self.setup_game()
        self.play_game_music()

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
        path = self.find_music_file("dark_grim_horror_ambience.mp3")
        self.stop_game_music()
        self.game_music_player, self.game_music_sound = play_loop(
            path, self.music_volume)

    def play_suspense_music(self):
        """Воспроизводит музыку в комнате с боссом"""
        path = "/Users/evgen/Downloads/The-edges-of-House 4/music/suspense-horror-music-loop-382813.mp3"
        self.stop_suspense_music()
        if path:
            self.suspense_player, _ = play_loop(path, self.music_volume)

    def stop_suspense_music(self):
        """Останавливает музыку комнаты с выходом"""
        if self.suspense_player:
            stop_player(self.suspense_player)
            self.suspense_player = None

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
                # Не трогаем сам выход (тайл 3)
                if self.dungeon_map.get_tile_value(x, y) != 3:
                    self.dungeon_map.map_data[y][x] = 0  # Делаем полом
                    # Добавляем в коридоры
                    self.dungeon_map.corridor_tiles.add((x, y))

        self.dungeon_map.exit_door_closed = False
        self.update_visibility()
        
        # Визуальные и звуковые эффекты открытия прохода
        self.trigger_passage_opening_effects()
        print("Проход открыт! Босс повержен!")

    def trigger_passage_opening_effects(self):
        """Запускает визуальные и звуковые эффекты открытия прохода"""
        # Визуальный эффект - создаем частицы или вспышку
        self.passage_opening_effect = {
            'active': True,
            'start_time': time.time(),
            'duration': 2.0,  # Длительность эффекта в секундах
            'particles': []
        }
        
        # Звуковой эффект
        try:
            # Загружаем звук открытия прохода
            passage_sound = arcade.load_sound("resources/sounds/passage_open.wav")
            arcade.play_sound(passage_sound, volume=0.7)
        except:
            # Если звук не найден, используем стандартный звук
            try:
                success_sound = arcade.load_sound("resources/sounds/success.wav")
                arcade.play_sound(success_sound, volume=0.5)
            except:
                pass  # Если звуки не загружены, просто продолжаем

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
        # Easy difficulty - no save points
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

    def place_player(self):
        if not self.dungeon_map or not self.player:
            return

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

        self.player.set_pos(*spawn_pos)
        self.visible_tiles.add(spawn_pos)
        self.minimap_player_draw_pos = (
            float(spawn_pos[0]), float(spawn_pos[1]))

    def place_bosses(self):
        """Размещает боссов и обычных врагов на карте, боссы далеко от спавна"""
        if not self.dungeon_map or not self.dungeon_map.rooms:
            return

        import random
        self.bosses = []
        boss_types = ["Caveman Boss", "Giant Goblin", "Viking Leader"]
        self.boss_room_ids = set()

        # Определяем комнату спавна игрока
        spawn_room_id = None
        if self.player and hasattr(self.player, "pos"):
            spawn_room_id = self.dungeon_map.get_room_id(
                self.player.pos[0], self.player.pos[1])

        # Выбираем комнату у края карты, максимально далекую от спавна для босса Caveman
        far_room_idx = None
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
        boss = Boss(self.tile_size, "Caveman Boss", (boss_x, boss_y))
        boss.visible = False
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
                mob.visible = True
                if self.player and mob.sprite:
                    mob.sprite.scale = self.player.sprite.scale
                self.bosses.append(mob)

        for idx in goblin_rooms:
            spawn_in_room(idx, "Giant Goblin")
        for idx in viking_rooms:
            spawn_in_room(idx, "Viking Leader")

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
        count = min(8, max(4, len(self.dungeon_map.rooms) // 3))
        exclude = set()
        spawn_room_id = self.dungeon_map.get_room_id(
            self.player.pos[0], self.player.pos[1]) if self.player else None
        if spawn_room_id is not None:
            exclude.add(spawn_room_id)
        if self.dungeon_map.exit_room_idx is not None:
            exclude.add(self.dungeon_map.exit_room_idx)
        room_indices = [i for i in range(
            len(self.dungeon_map.rooms)) if i not in exclude]
        random.shuffle(room_indices)
        room_indices = room_indices[:count]
        for idx in room_indices:
            room = self.dungeon_map.rooms[idx]
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
            s = arcade.Sprite(closed_path)
            if s.texture and s.texture.width:
                s.scale = (self.tile_size / s.texture.width)
            s.center_x = cx * self.tile_size + self.tile_size // 2
            s.center_y = cy * self.tile_size + self.tile_size // 2
            s.properties = {"opened": False}
            self.chest_sprites.append(s)

    def spawn_dropped_item(self, icon_id, px, py):
        tex = self.item_textures.get(icon_id)
        if not tex:
            return
        sp = arcade.Sprite()
        sp.texture = tex
        if tex.width:
            sp.scale = (self.tile_size / tex.width) * 0.7
        sp.center_x = px
        sp.center_y = py
        sp.properties = {"icon_id": icon_id}
        self.dropped_item_sprites.append(sp)

    def apply_inventory_effects(self):
        if not self.player:
            return

        # Reset to base stats
        self.player.move_speed = self.player.base_move_speed
        self.player.attack_duration = self.player.base_attack_duration
        self.player.health_regen_amount = self.player.base_health_regen_amount
        self.player.has_double_strike = False
        self.player.bonus_damage_percent = 0.0
        self.player.bonus_damage_flat = 0
        self.player.dodge_chance = 0.0
        
        # Accumulators
        move_mult = 1.0
        atk_speed_mult = 1.0
        max_hp_mult = 1.0
        regen_mult = 1.0
        
        for item in self.inventory:
            iid = item.get("icon_id")
            effect = ITEM_EFFECTS.get(iid)
            if not effect:
                continue
            
            self.player.bonus_damage_percent += effect.get("dmg_pct", 0)
            self.player.bonus_damage_flat += effect.get("dmg_flat", 0)
            move_mult += effect.get("move_pct", 0)
            atk_speed_mult += effect.get("atk_speed_pct", 0)
            max_hp_mult += effect.get("max_hp_pct", 0)
            regen_mult += effect.get("regen_pct", 0)
            self.player.dodge_chance += effect.get("dodge", 0)
            
            if effect.get("special") == "double_strike":
                self.player.has_double_strike = True
                

        # Finalize
        self.player.move_speed *= max(0.1, move_mult)
        # Attack speed increases means duration decreases.
        self.player.attack_duration = self.player.base_attack_duration / max(0.1, 1.0 + atk_speed_mult)
        
        old_max = self.player.max_health
        new_max = int(self.player.base_max_health * max(1.0, 1.0 + max_hp_mult))
        
        if new_max != self.player.max_health:
            self.player.max_health = new_max
            # Heal the difference if max hp increased
            if new_max > old_max:
                self.player.health += (new_max - old_max)
             
        self.player.health_regen_amount = int(self.player.base_health_regen_amount * max(1.0, 1.0 + regen_mult))

    def get_item_description(self, icon_id):
        # Check if it has an effect description first
        if icon_id in ITEM_EFFECTS and "desc" in ITEM_EFFECTS[icon_id]:
            return ITEM_EFFECTS[icon_id]["desc"]

        m = {
            1: None,
            2: "Талисман урон +5%",
            3: "Магический листок +2% восстановления здоровья",
            4: "Талисман скорость перезарядки удара +5%",
            5: "Оторванная конечность",
            6: "Оторванная конечность",
            7: None,
            8: "Часть скелета",
            9: "Челюсть",
            10: "Оторванные глаза",
            11: None,
            12: None,
            13: "Перчатка погибшего воина +10% урона +2% скорости",
            14: "Волшебный браслет скорость перезарядки удара +2%",
            15: "Волшебные сапоги +10% скорости передвижения",
            16: "Ботинки нищего крестьянина",
            17: "Талисман позволяющий нанести двойной удар",
            18: "Одежда нищего крестьянина",
            19: "Броня из шкуры дракона +7% промах от ударов",
            20: "Броня мумии +5% промах от ударов",
            21: "Шлем викинга +5% промах от ударов",
            22: None,
            23: "Щит +17% промах от ударов",
            24: "Топор урон +5",
            25: "Секира урон +6% -2% скорости передвижения",
            26: "Молот урон +7% -5% скорости передвижения",
            27: "Сломанный лук",
            28: "Кочан стрел",
            29: "Стрела",
            30: "Сабля пирата +5 урона",
            31: None,
            32: "Клинок как у ассасина +5% урона +5% скорости",
            33: "Факел",
            34: None,
            35: None,
            36: None,
            37: None,
            38: "Зубы",
            39: "Кости",
            40: "Странные вкусности",
            41: "Деньги",
            42: "Гирлянда",
            43: "Кусок мяса +20% здоровья",
            44: "Кусок мяса +20% здоровья",
            45: "Зелье елексира +45% здоровья",
            46: "Зелья урона на 30 секунд +25% урона",
            47: "Опасное зелье",
            48: None,
            49: "Бомба",
            50: "Тратил с фетилем",
        }
        return m.get(icon_id)

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
        # Easy difficulty settings
        self.view_radius = 8
        self.use_fov = True

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

        # Используем лучевую систему для освещения комнаты
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

        # Если игрок в комнате босса, расширяем освещение, чтобы видеть всю комнату
        if in_boss_room:
            # Добавляем все тайлы из комнаты босса в видимые
            self.visible_tiles.update(current_room_tiles)

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
            }
            save_data = {
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
                        # Инициализация боссов при загрузке
                        self.bosses = []
                        self.place_bosses()
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
            print("Игра сохранена!")
        else:
            print("Ошибка сохранения игры!")

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

            if hasattr(self, 'game_music_player') and self.game_music_player:
                try:
                    self.game_music_player.volume = self.music_volume
                except Exception:
                    pass

        self.show_pause_menu = False
        self.pause_manager.disable()

        # История показывается в LoadingView

        # Если это сетевая игра, настраиваем обработку сообщений
        if hasattr(self, 'client') and self.client:
            from dedicated_server.protocol import MessageType
            self.client.register_message_handler(
                MessageType.PLAYER_MOVE,
                self._handle_player_move
            )

    def _handle_player_move(self, message):
        """Обрабатывает сообщение о движении другого игрока"""
        # Получаем информацию о движении игрока
        player_id = message.data.get("player_id")
        position = message.data.get("position", (0, 0))
        facing = message.data.get("facing", "front")

        # В реальной реализации здесь будет обновление позиции других игроков
        # Пока что просто выводим информацию
        print(
            f"Player {player_id} moved to position {position} facing {facing}")

    def _send_player_move(self, x, y):
        """Отправляет сообщение о движении игрока на сервер"""
        if hasattr(self, 'client') and self.client and self.client.connected:
            # Отправляем сообщение о движении на сервер
            import asyncio
            import threading

            def send_move():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(
                        self.client.send_player_move(x, y, self.player.facing if hasattr(
                            self, 'player') and self.player else "front")
                    )
                    loop.close()
                except Exception as e:
                    print(f"Error sending player move: {e}")

            threading.Thread(target=send_move, daemon=True).start()

    def on_hide_view(self):
        self.manager.disable()
        self.pause_manager.disable()

    def on_draw(self):
        self.clear()

        if self.camera:
            self.camera.use()
            self.draw_map()  # Здесь рисуются стены, пол, игроки и боссы
            self.draw_passage_opening_effect()

        # Возвращаемся к UI камере для отрисовки интерфейса
        self.ui_camera.use()
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
            self.draw_player_health()
            self.draw_death_message()

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
            for _ in range(5):
                pos = random.choice(self.dungeon_map.exit_door_positions)
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
            if p['alpha'] > 0:
                arcade.draw_circle_filled(p['x'], p['y'], p['size'], (*p['color'], p['alpha']))

        # Удаляем старые частицы
        effect['particles'] = [p for p in effect['particles'] if p['alpha'] > 0]


    def on_update(self, delta_time):
        # Проверяем наличие ожидающего аудио из потока
        if self.pending_audio_path:
            try:
                if os.path.exists(self.pending_audio_path):
                    # Останавливаем предыдущее
                    if self.story_audio_player:
                        try:
                            arcade.stop_sound(self.story_audio_player)
                        except:
                            pass

                    sound = arcade.load_sound(self.pending_audio_path)
                    if sound:
                        self.story_audio_player = arcade.play_sound(sound)
                    self.pending_audio_path = None
            except Exception as e:
                print(f"Error playing pending audio: {e}")

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

        if hasattr(self, 'game_music_player') and self.game_music_player:
            try:
                if hasattr(self.game_music_player, 'volume'):
                    self.game_music_player.volume = self.music_volume
            except Exception:
                pass

        if self.show_pause_menu:
            self.pause_manager.on_update(delta_time)

        self._update_player_state_from_keys()

        if self.camera and self.window and self.player and self.dungeon_map:
            tile_size = self.tile_size

            # Easy difficulty movement
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

                if self.camera.position:
                    curr_x, curr_y = self.camera.position
                    new_x = curr_x + (target_cam_x - curr_x) * \
                        self.camera_lerp_speed
                    new_y = curr_y + (target_cam_y - curr_y) * \
                        self.camera_lerp_speed
                    self.camera.position = (new_x, new_y)
                else:
                    self.camera.position = (target_cam_x, target_cam_y)

            # Обновление тряски камеры
            if self.camera_shake_duration > 0:
                self.camera_shake_duration -= delta_time
                if self.camera_shake_duration <= 0:
                    self.camera_shake_duration = 0
                    # Сброс к исходной позиции
                    if self.camera_original_pos:
                        self.camera.position = self.camera_original_pos
                        self.camera_original_pos = None
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
                # Обновляем и двигаем врага только если он в той же комнате, что и игрок
                if boss_room_id is not None and boss_room_id == player_room_id:
                    boss.update(delta_time, player_pixel_pos)
                    boss.move_towards_player(player_pixel_pos, delta_time)
                    # Атака возможна только если враг видим игроку
                    visible = False
                    if self.visibility_grid:
                        bx, by = boss.pos[0], boss.pos[1]
                        if 0 <= by < len(self.visibility_grid) and 0 <= bx < len(self.visibility_grid[0]):
                            visible = self.visibility_grid[by][bx]
                    else:
                        visible = tuple(boss.pos) in self.visible_tiles
                    if visible and boss.attack_player(player_pixel_pos):
                        if random.random() >= self.player_dodge_chance:
                            self.player.take_damage(boss.attack_damage)
                elif boss.boss_type != "Caveman Boss":
                    # Если враг (не босс) в другой комнате, он бродит
                    boss.update(delta_time, None)
                    boss.wander(delta_time, lambda x, y: self.dungeon_map.is_walkable(x, y))

            # Проверка смерти игрока (если еще не обработана)
            if self.player and not self.player.is_alive() and not self.player_dead_message:
                self.handle_player_death()

            if self.ambient_sprites and self.dungeon_map:
                map_pixel_w = self.dungeon_map.map_width * self.tile_size
                map_pixel_h = self.dungeon_map.map_height * self.tile_size
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
                            print(f"Применен временный эффект: +{int(effect['temp_dmg_pct']*100)}% урона на {effect['duration']} сек")
                        sp.remove_from_sprite_lists()
                        continue

                    if len(self.inventory) < 9:
                        self.inventory.append({"icon_id": icon_id})
                        sp.remove_from_sprite_lists()
                        self.apply_inventory_effects()

    def handle_player_death(self):
        """Обрабатывает смерть игрока"""
        self.player_dead_message = "ИГРОК УМЕР!"
        self.death_message_timer = 5.0  # Показываем сообщение 5 секунд
        print("Игрок умер! Отображаем сообщение о смерти.")
        # Проигрываем музыку Game Over
        try:
            self.stop_suspense_music()
            self.stop_game_music()
        except Exception:
            pass
        
        # Звук game_over_voice.mp3 удален по требованию

    def handle_boss_death(self, boss):
        """Обрабатывает смерть босса"""
        if boss in self.bosses:
            self.bosses.remove(boss)
            print(f"Босс {boss.boss_type} убит и удалён из списка.")
            # Открываем проход после смерти босса
            self.open_exit_passage()
            # Можно добавить эффекты смерти, звуки и т.д.
            cx, cy = self.camera.position

            if self.camera_target_pos is None:
                self.camera_target_pos = (cx, cy)

            player_pixel_x, player_pixel_y = self.player.get_pixel_position()

            map_pixel_w = self.dungeon_map.map_width * self.tile_size
            map_pixel_h = self.dungeon_map.map_height * self.tile_size

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

        # Если это сетевая игра, отправляем информацию о движении на сервер
        if hasattr(self, 'client') and self.client and self.client.connected:
            self._send_player_move(self.player.pos[0], self.player.pos[1])

        if self.save_point_pos and not self.save_point_used:
            save_x, save_y = self.save_point_pos
            if self.player.is_at_position(save_x, save_y):
                if self.save_game():
                    self.save_point_used = True
                    print("Игра сохранена через точку сохранения!")

        if self.dungeon_map.exit_pos:
            exit_x, exit_y = self.dungeon_map.exit_pos
            if self.player.is_at_position(exit_x, exit_y):
                self.advance_level()

        # Музыка в комнате с боссом и появление босса
        player_room_id = self.dungeon_map.get_room_id(
            self.player.pos[0], self.player.pos[1])
        if player_room_id in self.boss_room_ids and not self.exit_music_played:
            self.play_suspense_music()
            self.exit_music_played = True

            # Показываем босса и делаем тряску экрана
            for boss in self.bosses:
                if boss and not boss.visible:
                    # Делаем видимыми тех боссов, чья комната совпадает
                    boss_room_id = self.dungeon_map.get_room_id(
                        boss.pos[0], boss.pos[1])
                    if boss_room_id == player_room_id:
                        boss.visible = True
                        self.shake_camera(10.0, 0.5)  # Тряска экрана

            # Закрываем выход, когда игрок входит в комнату босса
            self.close_exit_door()

            # Обновляем видимость, чтобы сразу отобразить изменения
            # Увеличиваем радиус обзора в комнате босса для лучшего освещения
            self.update_visibility()
        elif player_room_id not in self.boss_room_ids and self.exit_music_played:
            self.stop_suspense_music()
            self.exit_music_played = False
            self.play_game_music()

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
                    print("Игра сохранена через точку сохранения!")

        if self.dungeon_map.exit_room_idx is not None:
            room_id = self.dungeon_map.get_room_id(grid_x, grid_y)
            if room_id == self.dungeon_map.exit_room_idx and not self.exit_music_played:
                self.play_suspense_music()
                self.exit_music_played = True
            elif room_id != self.dungeon_map.exit_room_idx and self.exit_music_played:
                self.stop_suspense_music()
                self.exit_music_played = False
                self.play_game_music()

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
                        color = (220, 90, 60)
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
        elif key == arcade.key.SPACE:
            dx = (1 if self.move_hold["right"] else 0) - \
                (1 if self.move_hold["left"] else 0)
            dy = (1 if self.move_hold["up"] else 0) - \
                (1 if self.move_hold["down"] else 0)
            if dx != 0 or dy != 0:
                # Easy difficulty movement
                if not self.player.is_moving:
                    new_x = self.player.pos[0] + dx
                    new_y = self.player.pos[1] + dy
                    if self.can_move_to(new_x, new_y):
                        if self.player.move(dx, dy):
                            self._on_player_moved()
                    self.move_timer = self.move_cooldown
        elif key == arcade.key.Q or key == 1081 or key == 1049:  # 1081='й', 1049='Й'
            if 0 <= self.selected_slot < len(self.inventory):
                item = self.inventory[self.selected_slot]
                icon_id = item.get("icon_id")
                px, py = self.player.get_pixel_position()
                
                # Drop item slightly in front of player to avoid immediate pickup
                drop_dist = 40
                if self.player.facing == 'left':
                    px -= drop_dist
                elif self.player.facing == 'right':
                    px += drop_dist
                elif self.player.facing == 'back':
                    py += drop_dist
                else: # front
                    py -= drop_dist
                    
                self.spawn_dropped_item(icon_id, px, py)
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
        
        # Double strike check
        hits = 1
        if self.player.has_double_strike:
            hits = 2
            print("Двойной удар!")

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

        try:
            swing = arcade.load_sound("resources/sounds/swing.wav")
            arcade.play_sound(swing, volume=self.sound_volume)
        except Exception:
            pass

        for i in range(hits):
            for target in targets:
                 # Deal damage to target
                 if hasattr(target, 'take_damage'):
                     target.take_damage(damage)
                     if target.health <= 0:
                         self.handle_boss_death(target)

    def on_mouse_press(self, x, y, button, modifiers):
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
                    drop_ids = random.sample(
                        list(self.valid_item_ids), k=min(3, len(self.valid_item_ids)))
                    for iid in drop_ids:
                        ox = random.uniform(-self.tile_size *
                                            0.5, self.tile_size * 0.5)
                        oy = random.uniform(-self.tile_size *
                                            0.5, self.tile_size * 0.5)
                        self.spawn_dropped_item(
                            iid, chest.center_x + ox, chest.center_y + oy)

        elif button == arcade.MOUSE_BUTTON_RIGHT:
            # Атака босса правой кнопкой мыши
            if self.player and self.player.is_alive():
                print("Правая кнопка мыши нажата - атака босса")

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
                print("Не могу атаковать: игрок мертв или отсутствует")

    def shake_camera(self, intensity, duration):
        """Добавляет тряску камеры"""
        if self.camera:
            self.camera_shake_intensity = intensity
            self.camera_shake_duration = duration
            self.camera_original_pos = self.camera.position

            # Применяем тряску сразу
            shake_x = (random.random() - 0.5) * self.camera_shake_intensity
            shake_y = (random.random() - 0.5) * self.camera_shake_intensity
            self.camera.position = (
                self.camera.position[0] + shake_x,
                self.camera.position[1] + shake_y
            )

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
                'back': math.pi/2,  # Up
                'front': -math.pi/2  # Down
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
            print("Промах!")

    def try_move_player(self, dx, dy):
        if not self.player or not self.dungeon_map:
            return

        prev_room_id = self.dungeon_map.get_room_id(
            self.player.pos[0], self.player.pos[1])
        new_x = self.player.pos[0] + dx
        new_y = self.player.pos[1] + dy
        if 0 <= new_x < self.dungeon_map.map_width and 0 <= new_y < self.dungeon_map.map_height:
            if self.can_move_to(new_x, new_y):
                # Easy difficulty movement
                if self.player.move(dx, dy):
                    self._on_player_moved()

                # Проверка входа в комнату с выходом для закрытия двери
                room_id = self.dungeon_map.get_room_id(new_x, new_y)
                if room_id == self.dungeon_map.exit_room_idx and not self.dungeon_map.exit_door_closed:
                    self.close_exit_door()
                    print("Проход закрыт! Сразитесь с боссом!")

                if self.save_point_pos and not self.save_point_used:
                    save_x, save_y = self.save_point_pos
                    if new_x == save_x and new_y == save_y:
                        if self.save_game():
                            self.save_point_used = True
                            print("Игра сохранена через точку сохранения!")

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
        self.level += 1
        self.visible_tiles.clear()
        self.explored_tiles.clear()
        self.stop_suspense_music()
        self.exit_music_played = False
        # Easy difficulty - no hard save system
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
                
                # Try to use texture
                tex = self.dungeon_map.textures.get(value) if hasattr(self.dungeon_map, 'textures') else None
                
                if tex:
                    if value not in texture_batches:
                        texture_batches[value] = {'visible': [], 'seen': []}
                    
                    key = 'visible' if visible else 'seen'
                    texture_batches[value][key].append((cx, cy))
                else:
                    # Fallback logic
                    left = screen_x
                    right = screen_x + tile_size_float
                    
                    if value == 3: # Exit
                        key = 'visible_exit' if visible else 'seen_exit'
                        batches[key].append((left, right, bottom, top))
                    elif value == 1: # Wall
                        key = 'visible_wall' if visible else 'seen_wall'
                        batches[key].append((left, right, bottom, top))
                    else: # Floor
                        key = 'visible_floor' if visible else 'seen_floor'
                        batches[key].append((left, right, bottom, top))

        # Draw textures
        for val, lists in texture_batches.items():
            tex = self.dungeon_map.textures.get(val)
            if not tex: continue
            
            # Visible
            for cx, cy in lists['visible']:
                left = cx - tile_size / 2
                right = cx + tile_size / 2
                bottom = cy - tile_size / 2
                top = cy + tile_size / 2
                rect = arcade.types.Rect(left, right, bottom, top, tile_size, tile_size, cx, cy)
                arcade.draw_texture_rect(tex, rect)
                
            # Seen (Tinted)
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
                            self.shake_camera(10.0, 0.5)

        # Отрисовка боссов
        for boss in self.bosses:
            if boss and boss.is_alive() and hasattr(boss, 'visible') and boss.visible:
                # Проверяем, находится ли босс в видимой зоне
                boss_grid_x = int(boss.pos[0])
                boss_grid_y = int(boss.pos[1])
                
                # Check visibility using visibility grid if available, otherwise visible_tiles
                is_visible = False
                if self.visibility_grid and 0 <= boss_grid_y < len(self.visibility_grid) and 0 <= boss_grid_x < len(self.visibility_grid[0]):
                    is_visible = self.visibility_grid[boss_grid_y][boss_grid_x]
                elif (boss_grid_x, boss_grid_y) in self.visible_tiles:
                    is_visible = True
                    
                if is_visible:
                    boss.draw()
        # Only draw chests that are in the same room as the player
        if self.chest_sprites and self.player and self.dungeon_map:
            player_room_id = self.dungeon_map.get_room_id(
                self.player.pos[0], self.player.pos[1])
            chests_to_draw = arcade.SpriteList()
            for chest in self.chest_sprites:
                # Convert chest position back to grid coordinates to check room
                chest_grid_x = int(chest.center_x / self.tile_size)
                chest_grid_y = int(chest.center_y / self.tile_size)
                chest_room_id = self.dungeon_map.get_room_id(
                    chest_grid_x, chest_grid_y)

                # Only add to draw list if chest is in the same room as player
                if chest_room_id == player_room_id:
                    chests_to_draw.append(chest)

            # Draw only the chests that are in the same room
            if len(chests_to_draw) > 0:
                chests_to_draw.draw()

        # Only draw dropped items that are in the same room as the player
        if self.dropped_item_sprites and self.player and self.dungeon_map:
            player_room_id = self.dungeon_map.get_room_id(
                self.player.pos[0], self.player.pos[1])
            items_to_draw = arcade.SpriteList()
            for item in self.dropped_item_sprites:
                # Convert item position back to grid coordinates to check room
                item_grid_x = int(item.center_x / self.tile_size)
                item_grid_y = int(item.center_y / self.tile_size)
                item_room_id = self.dungeon_map.get_room_id(
                    item_grid_x, item_grid_y)

                # Only add to draw list if item is in the same room as player
                if item_room_id == player_room_id:
                    items_to_draw.append(item)

            # Draw only the items that are in the same room
            if len(items_to_draw) > 0:
                items_to_draw.draw()

        if self.ambient_sprites:
            self.ambient_sprites.draw()

        self.draw_minimap()

        # Отрисовка UI здоровья игрока
        self.draw_player_health()

        # Отрисовка сообщения о смерти игрока
        self.draw_death_message()

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
        health_percent = self.player.health / self.player.max_health
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
        health_text = f"{int(self.player.health)}/{self.player.max_health}"
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
        health_percent = self.player.health / self.player.max_health
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
        save_exists = os.path.exists(get_savegame_path())
        if save_exists:
            sub_text = "Можно загрузить сохранение"
        else:
            sub_text = "Игра окончена"

    def update_story(self, delta_time):
        """Обновление логики отображения истории"""
        # В оригинальной логике текст исчезает по таймеру,
        # но теперь он будет исчезать только при нажатии кнопки "Далее"
        # Оставляем таймер для отладки, но не используем для скрытия текста
        if self.current_story_line:
            self.story_line_timer -= delta_time
            # Debug timer every second
            if int(self.story_line_timer + delta_time) != int(self.story_line_timer):
                print(f"Story timer: {int(self.story_line_timer)}")

        # Показываем следующую строку истории только если текущая закончилась
        # или если пользователь нажал "Далее"
        if not self.current_story_line and self.story_lines:
            self.current_story_line = self.story_lines.pop(0)
            # Увеличиваем время до бесконечности, чтобы текст не исчезал по таймеру
            # Текст не исчезает по таймеру
            self.story_line_timer = float('inf')
            print(f"Showing story line: {self.current_story_line[:20]}...")

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
        print("Initializing story text...")
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
        print(f"Story lines loaded: {len(self.story_lines)}")
        for i, line in enumerate(self.story_lines):
            print(f"Line {i+1}: {line[:30]}...")

    def play_story_audio(self, text):
        """Запускает генерацию и воспроизведение аудио в отдельном потоке"""
        import threading
        print(f"Starting audio thread for: {text[:20]}...")
        threading.Thread(target=self._generate_and_play_audio_thread, args=(
            text,), daemon=True).start()

    def _generate_and_play_audio_thread(self, text):
        """Фоновый поток для генерации и воспроизведения"""
        try:
            import asyncio
            print("Running async audio generation...")
            asyncio.run(self._speak_text_async(text))
        except Exception as e:
            print(f"Ошибка в потоке аудио: {e}")

    async def _speak_text_async(self, text):
        """Асинхронная генерация и воспроизведение"""
        try:
            print(f"Generating audio for: {text[:20]}...")
            filename = os.path.join(os.getcwd(), "story_audio_current.mp3")

            # Удаляем старый файл
            if os.path.exists(filename):
                try:
                    os.remove(filename)
                except:
                    pass

            communicate = edge_tts.Communicate(text, 'ru-RU-DmitryNeural')
            await communicate.save(filename)

            if os.path.exists(filename):
                self.pending_audio_path = filename
                print(f"Audio generated: {filename}")
            else:
                print(f"Failed to generate audio file: {filename}")

        except Exception as e:
            print(f"Ошибка при озвучивании текста: {e}")

            communicate = edge_tts.Communicate(text, 'ru-RU-DmitryNeural')
            await communicate.save(filename)

            if os.path.exists(filename):
                self.pending_audio_path = filename
                print(f"Audio generated: {filename}")
            else:
                print(f"Failed to generate audio file: {filename}")

        except Exception as e:
            print(f"Ошибка при озвучивании текста: {e}")
