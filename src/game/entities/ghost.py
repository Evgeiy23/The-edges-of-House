import arcade
import os
import glob
import math
import time
from game.entities.follower import Follower

from game.logic.resource_manager import ResourceManager

class Ghost(Follower):
    def __init__(self, tile_size, pos=(0, 0), level=1):
        super().__init__()
        self.tile_size = tile_size
        # Позиция в сетке
        self.pos = list(pos)
        self.draw_pos = [pos[0] * tile_size + tile_size // 2,
                         pos[1] * tile_size + tile_size // 2]
        
        self.level = level
        self.damage = 0
        self.hp = 30
        self.max_hp = 30
        self._calculate_stats()
        
        # Машина состояний
        self.state = 'idle' # idle (покой), chase (преследование), attack (атака)
        self.facing = 'front'
        
        self.id = None
        self.move_speed_pixels = 50.0

        # Система агрессии
        self.aggro_radius = 500.0 # Пиксели (Увеличено с 250)
        self.attack_radius = 40.0 # Пиксели
        
        # Система атаки
        self.attack_cooldown = 1.0
        self.attack_timer = 0.0
        self.can_attack = True
        
        self.sprite = None
        self.sprite_list = arcade.SpriteList()
        self.animations = {}
        self.current_animation_frames = []
        self.current_frame_index = 0
        self.animation_timer = 0.0
        self.animation_speed = 0.08
        
        self.resource_manager = ResourceManager.get_instance()
        self._load_resources()
        self._update_animation()

    def _calculate_stats(self):
        # Логика урона:
        # Уровень < 20: 0 урона (Пассивный)
        # Уровень >= 20: Базовый урон 10
        # Уровень 20-30: +5 за каждый уровень
        
        # Логика HP: Базовое 30 + 7 за уровень
        self.max_hp = 30 + (self.level * 7)
        self.hp = self.max_hp
        
        if self.level >= 20:
            self.damage = 10
            # Добавляем +5 за каждый уровень выше 20, до 30
            levels_above_20 = min(self.level, 30) - 20
            if levels_above_20 > 0:
                self.damage += levels_above_20 * 5
        else:
            self.damage = 0
            
    def _load_resources(self):
        # Пытаемся загрузить ассеты Гигантского Гоблина как замену для Призрака
        base_path = "resources/character_enemies/Giant Goblin"
        if os.path.exists(base_path):
            self._load_animations(base_path)
            
        if not self.sprite:
            # Запасной вариант
            self.sprite = arcade.SpriteSolidColor(self.tile_size, self.tile_size, arcade.color.GHOST_WHITE)
            self.sprite_list.append(self.sprite)
        else:
            self.sprite.alpha = 150 # Призрачная прозрачность
            
    def _load_animations(self, base_path):
        directions = ['Front', 'Back', 'Left', 'Right']
        actions = {
            'idle': 'Running', 
            'running': 'Running',
            'attacking': 'Attacking'
        }
        
        self.sprite = arcade.Sprite()
        self.sprite.center_x = self.draw_pos[0]
        self.sprite.center_y = self.draw_pos[1]
        self.sprite_list.append(self.sprite)
        
        for direction in directions:
            for action_key, action_name in actions.items():
                folder_path = os.path.join(base_path, f"{direction} - {action_name}")
                
                if os.path.exists(folder_path):
                    pattern = os.path.join(folder_path, "*.png")
                    files = sorted(glob.glob(pattern))
                    
                    if files:
                        textures = []
                        for file_path in files:
                            texture = self.resource_manager.get_texture(file_path)
                            if texture:
                                textures.append(texture)
                            
                        key = f"{direction.lower()}_{action_key}"
                        self.animations[key] = textures
                        
                        if textures and not self.sprite.texture:
                            self.sprite.texture = textures[0]
                            if textures[0].width:
                                self.sprite.scale = (self.tile_size / textures[0].width) * 0.8

    def _get_animation_key(self):
        direction = self.facing.lower()
        if self.state == 'attack':
            return f"{direction}_attacking"
        # по умолчанию бег, если движется или стоит
        return f"{direction}_running"

    def _update_animation(self):
        key = self._get_animation_key()
        if key in self.animations:
            new_frames = self.animations[key]
            # Сброс анимации, если она изменилась
            if new_frames != self.current_animation_frames:
                self.current_animation_frames = new_frames
                self.current_frame_index = 0
                self.animation_timer = 0
                # Сразу устанавливаем первый кадр
                if self.current_animation_frames:
                    self.sprite.texture = self.current_animation_frames[0]
        elif self.animations:
            self.current_animation_frames = list(self.animations.values())[0]

    def update(self, delta_time, player=None, dungeon_map=None, lod_level=0):
        # Обновление анимации в зависимости от LOD
        if lod_level < 2:
            self.animation_timer += delta_time
            
            # Для LOD 1 мы могли бы замедлить анимацию или пропускать обновления, 
            # но простого "остановить, если далеко" (LOD 2) часто достаточно.
            # Допустим, LOD 1 просто уменьшает частоту, если мы хотим, но здесь оставим просто:
            # LOD 0 & 1: Анимация. LOD 2: Статика.
            
            if self.current_animation_frames and self.animation_timer >= self.animation_speed:
                 self.animation_timer = 0
                 self.current_frame_index = (self.current_frame_index + 1) % len(self.current_animation_frames)
                 self.sprite.texture = self.current_animation_frames[self.current_frame_index]

        # Handle attack cooldown
        if not self.can_attack:
            self.attack_timer += delta_time
            if self.attack_timer >= self.attack_cooldown:
                self.can_attack = True
                self.attack_timer = 0.0

        if not player or not dungeon_map:
            return

        # 1. Проверка дистанции и состояния
        player_pos = player.draw_pos if hasattr(player, 'draw_pos') else player.pos
        # Убедимся, что player_pos в пикселях
        if not hasattr(player, 'draw_pos'):
            # Запасной вариант, если передан простой список координат
             pass 
        
        dx = player_pos[0] - self.draw_pos[0]
        dy = player_pos[1] - self.draw_pos[1]
        dist = math.sqrt(dx*dx + dy*dy)
        
        # Уточнение состояния (Менеджер обрабатывает Idle <-> Chase)
        # Обрабатываем Chase <-> Attack локально для отзывчивости
        if self.state == 'chase':
            # Проверка линии видимости для перехода в атаку
            has_los = True
            if hasattr(dungeon_map, 'has_line_of_sight'):
                # Проверка от центра к центру грубо
                start_node = (int(self.draw_pos[0] // self.tile_size), int(self.draw_pos[1] // self.tile_size))
                end_node = (int(player_pos[0] // self.tile_size), int(player_pos[1] // self.tile_size))
                has_los = dungeon_map.has_line_of_sight(start_node, end_node)
            
            if dist <= self.attack_radius and has_los:
                if self.level >= 20:
                    self.state = 'attack'
        elif self.state == 'attack':
             if dist > self.attack_radius:
                 self.state = 'chase'
            
        # 2. Действие в зависимости от состояния
        if self.state == 'attack':
            # Обеспечиваем поворот к игроку во время атаки
            dx = player_pos[0] - self.draw_pos[0]
            dy = player_pos[1] - self.draw_pos[1]
            if abs(dx) > abs(dy):
                self.facing = 'right' if dx > 0 else 'left'
            else:
                self.facing = 'back' if dy > 0 else 'front'
                
            self._perform_attack(player)
            # Остановка движения при атаке
            pass
            
        elif self.state == 'chase':
            # Использование поиска пути
            # move_along_path возвращает шаг (dx, dy) для этого кадра
            move_dx, move_dy = self.move_along_path(delta_time, self.draw_pos, player_pos, self.move_speed_pixels, self.tile_size, dungeon_map)
            
            # Применение движения с проверкой столкновений
            self._move_with_collisions(move_dx, move_dy, dungeon_map)
            
            # Обновление направления
            if abs(move_dx) > abs(move_dy):
                self.facing = 'right' if move_dx > 0 else 'left'
            else:
                self.facing = 'back' if move_dy > 0 else 'front'
                
        # Визуальный индикатор агрессии
        if self.sprite:
            # Сброс цвета, если не атакует/не получил урон недавно (Простой подход)
            # В идеале использовать таймер для эффектов вспышки
            if self.state == 'attack':
                 self.sprite.color = arcade.color.RED
                 # Эффект пульсации для визуальной обратной связи
                 base_scale = (self.tile_size / self.sprite.texture.width) * 0.8 if (self.sprite.texture and self.sprite.texture.width) else 1.0
                 self.sprite.scale = base_scale * (1.0 + 0.15 * math.sin(time.time() * 15))
                 
                 if not self.can_attack:
                     # Период перезарядки, возможно тускло-красный
                     self.sprite.color = (200, 0, 0)
            elif self.state == 'chase':
                self.sprite.color = (255, 100, 100) # Светло-красный
                # Сброс масштаба
                base_scale = (self.tile_size / self.sprite.texture.width) * 0.8 if (self.sprite.texture and self.sprite.texture.width) else 1.0
                self.sprite.scale = base_scale
            else:
                self.sprite.color = arcade.color.WHITE
                # Сброс масштаба
                base_scale = (self.tile_size / self.sprite.texture.width) * 0.8 if (self.sprite.texture and self.sprite.texture.width) else 1.0
                self.sprite.scale = base_scale

        # Update sprite position
        if self.sprite:
            self.sprite.center_x = self.draw_pos[0]
            self.sprite.center_y = self.draw_pos[1]
            
        self.pos[0] = int(self.draw_pos[0] / self.tile_size)
        self.pos[1] = int(self.draw_pos[1] / self.tile_size)
        
        self._update_animation()

    def _move_with_collisions(self, dx, dy, dungeon_map):
        """Перемещает призрака, проверяя столкновения со стенами."""
        
        # Попытка движения по X
        new_x = self.draw_pos[0] + dx
        if not self._check_wall_collision(new_x, self.draw_pos[1], dungeon_map):
            self.draw_pos[0] = new_x
            
        # Попытка движения по Y
        new_y = self.draw_pos[1] + dy
        if not self._check_wall_collision(self.draw_pos[0], new_y, dungeon_map):
            self.draw_pos[1] = new_y
            
    def _check_wall_collision(self, x, y, dungeon_map):
        """Проверяет, сталкивается ли данная пиксельная позиция со стеной."""
        # Простая проверка точки может быть достаточной, или проверка углов bounding box
        # Используем центральную точку для простоты, но можно улучшить
        grid_x = int(x / self.tile_size)
        grid_y = int(y / self.tile_size)
        
        # Проверка границ
        if grid_x < 0 or grid_x >= dungeon_map.map_width or grid_y < 0 or grid_y >= dungeon_map.map_height:
            return True
            
        # Проверка стен (0 - пол, 1 - стена)
        # Используем map_data вместо grid
        if hasattr(dungeon_map, 'map_data'):
            if dungeon_map.map_data[grid_y][grid_x] == 1:
                return True
        elif hasattr(dungeon_map, 'grid'):
             if dungeon_map.grid[grid_y][grid_x] == 1:
                return True
            
        return False

    def _perform_attack(self, player):
        if self.can_attack:
            if hasattr(player, 'take_damage'):
                # Визуальная обратная связь для атаки
                if self.sprite:
                     self.sprite.color = arcade.color.RED
                     # Принудительное обновление текстуры, чтобы она не "застряла"
                     # Использование анимации атаки, если доступна
                     attack_key = self._get_animation_key()
                     if attack_key in self.animations:
                         frames = self.animations[attack_key]
                         if frames:
                             self.current_animation_frames = frames
                             self.current_frame_index = 0
                             self.sprite.texture = frames[0]
                     
                # print(f"Ghost attacks player for {self.damage} damage!")
                player.take_damage(self.damage)
                self.can_attack = False
            else:
                # Запасной вариант, если у игрока нет take_damage (не должно происходить, судя по player.py)
                pass

    def take_damage(self, amount):
        self.hp -= amount
        
        # Визуальная обратная связь для урона
        if self.sprite:
            self.sprite.color = arcade.color.ORANGE
            
        if self.sprite and self.hp <= 0:
            self.sprite.color = arcade.color.GRAY
            # Больше логики обрабатывается менеджером/окном
            # self.sprite.color = (255, 0, 0) # Логика красной вспышки перенесена или удалена
        # print(f"Ghost took {amount} damage. HP: {self.hp}/{self.max_hp}")

    def is_alive(self):
        return self.hp > 0

    def draw(self):
        if self.sprite_list:
            self.sprite_list.draw()
