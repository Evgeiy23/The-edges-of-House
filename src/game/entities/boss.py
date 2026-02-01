import arcade
import os
import glob
import math
import random
from game.logic.music import play_once, find_music_file


class Boss:
    def __init__(self, tile_size, boss_type="Caveman Boss", pos=(0, 0)):
        self.tile_size = tile_size
        self.boss_type = boss_type
        self.pos = list(pos)  # Позиция в клетках
        self.draw_pos = [pos[0] * tile_size + tile_size // 2,
                         pos[1] * tile_size + tile_size // 2]

        self.facing = 'front'
        self.state = 'idle'
        self.sprite = None
        self.sprite_list = None
        self.is_attacking = False
        self.is_moving = False
        self.attack_timer = 0.0
        self.damage_dealt = False
        self.attack_duration = 0.8
        self.animations = {}
        self.current_animation_frames = []
        self.current_frame_index = 0
        self.animation_timer = 0.0
        self.animation_speed = 0.15

        if self.boss_type == "Caveman Boss":
            self.max_health = 500
        else:
            self.max_health = 30
        self.health = self.max_health
        self.is_dead = False
        self.hurt_timer = 0.0
        self.hurt_duration = 0.3
        self.target_max_health = 1000
        self.health_increase_speed = 200.0
        self.powerup_active = False
        self.powerup_timer = 0.0
        self.sound_volume = 1.0

        # Боевая система
        self.attack_range = 1.5  # Дистанция атаки в клетках
        self.attack_damage = 20  # Урон от атаки босса: 20 единиц (по запросу)
        self.defense = 5 # Базовая защита
        self.attack_cooldown = 2.0
        self.last_attack_time = 0.0

        # Движение босса (в клетках в секунду)
        self.move_speed = 2.0
        self.visible = True

        self._initialize_sprites()
        self._load_animations()
        self._update_animation()

    def scale_stats(self, level):
        """Scales boss stats based on level"""
        # Example scaling: +10% health and +5% damage per level
        multiplier = 1.0 + (level - 1) * 0.1
        dmg_multiplier = 1.0 + (level - 1) * 0.05
        
        self.max_health = int(self.max_health * multiplier)
        self.health = self.max_health
        self.attack_damage = int(self.attack_damage * dmg_multiplier)
        self.defense = int(self.defense * multiplier)
        
        print(f"Босс {self.boss_type} масштабирован до уровня {level}: HP={self.health}, Урон={self.attack_damage}, Защита={self.defense}")

    def _initialize_sprites(self):
        """Инициализация спрайтов"""
        self.sprite = arcade.Sprite()
        self.sprite.center_x = self.draw_pos[0]
        self.sprite.center_y = self.draw_pos[1]
        self.sprite.scale = 1.0
        self.sprite_list = arcade.SpriteList()
        self.sprite_list.append(self.sprite)

    def _load_animations(self):
        """Загрузка анимаций босса"""
        base_path = f"resources/character_enemies/{self.boss_type}"
        directions = ['Front', 'Back', 'Left', 'Right']
        actions = {
            'idle': 'Running',  # Используем Running как idle
            'attacking': 'Attacking',
            'dying': 'Dying'
        }

        for direction in directions:
            for action_key, action_name in actions.items():
                if action_key == 'dying':
                    folder_path = os.path.join(base_path, action_name)
                else:
                    folder_path = os.path.join(
                        base_path, f"{direction} - {action_name}")

                if os.path.exists(folder_path):
                    pattern = os.path.join(folder_path, "*.png")
                    files = sorted(glob.glob(pattern))

                    if files:
                        textures = []
                        for file_path in files:
                            texture = arcade.load_texture(file_path)
                            textures.append(texture)

                        key = f"{direction.lower()}_{action_key}"
                        self.animations[key] = textures

                        if textures:
                            texture_width = textures[0].width
                            self.sprite.scale = (
                                self.tile_size / texture_width) * 0.7

    def _get_animation_key(self):
        """Получает ключ анимации"""
        if self.state == 'dying':
            return 'dying'

        direction = self.facing.lower()
        state_key = self.state

        return f"{direction}_{state_key}"

    def _update_animation(self):
        """Обновляет анимацию"""
        animation_key = self._get_animation_key()

        if animation_key in self.animations:
            self.current_animation_frames = self.animations[animation_key]
            self.current_frame_index = 0
            self.animation_timer = 0.0

            if self.current_animation_frames:
                self.sprite.texture = self.current_animation_frames[0]
        else:
            if self.animations:
                first_key = list(self.animations.keys())[0]
                self.current_animation_frames = self.animations[first_key]
                if self.current_animation_frames:
                    self.sprite.texture = self.current_animation_frames[0]

    def wander(self, delta_time, is_walkable_func=None):
        """Случайное блуждание"""
        if self.is_dead or self.is_attacking:
            return

        # Инициализация таймера блуждания, если его нет
        if not hasattr(self, 'wander_timer'):
            self.wander_timer = 0.0
            self.wander_angle = random.uniform(0, 2 * math.pi)
            
        self.wander_timer -= delta_time
        if self.wander_timer <= 0:
            self.wander_timer = random.uniform(1.0, 3.0)
            self.wander_angle = random.uniform(0, 2 * math.pi)
            
        speed = self.move_speed * self.tile_size * 0.5 # Медленнее, чем при погоне
        dx = math.cos(self.wander_angle) * speed * delta_time
        dy = math.sin(self.wander_angle) * speed * delta_time
        
        new_x = self.draw_pos[0] + dx
        new_y = self.draw_pos[1] + dy
        
        can_move = True
        if is_walkable_func:
            # Проверяем проходимость клетки
            grid_x = int(round((new_x - self.tile_size // 2) / self.tile_size))
            grid_y = int(round((new_y - self.tile_size // 2) / self.tile_size))
            if not is_walkable_func(grid_x, grid_y):
                can_move = False
                # Уперлись в стену - меняем направление
                self.wander_angle += math.pi + random.uniform(-0.5, 0.5)
                self.wander_timer = 0.5 # Быстрая смена направления

        if can_move:
            self.draw_pos[0] = new_x
            self.draw_pos[1] = new_y
            self.pos[0] = int(round((self.draw_pos[0] - self.tile_size // 2) / self.tile_size))
            self.pos[1] = int(round((self.draw_pos[1] - self.tile_size // 2) / self.tile_size))
            self.sprite.center_x = self.draw_pos[0]
            self.sprite.center_y = self.draw_pos[1]
            
            # Обновляем направление
            if abs(dx) > abs(dy):
                self.facing = 'right' if dx > 0 else 'left'
            else:
                self.facing = 'back' if dy > 0 else 'front'
            self._update_animation()

    def move_towards_player(self, player_pixel_pos, delta_time, is_walkable_func=None):
        """Движение к игроку (плавное) с учетом препятствий"""
        if self.is_dead or self.is_attacking:
            return

        target_x, target_y = player_pixel_pos
        current_x, current_y = self.draw_pos

        dx = target_x - current_x
        dy = target_y - current_y
        dist = math.sqrt(dx*dx + dy*dy)

        # Минимальная дистанция (чтобы не наезжать на игрока)
        min_dist = self.tile_size * 0.8

        if dist > min_dist:
            self.is_moving = True
            speed_pixels = self.move_speed * self.tile_size
            move_dist = speed_pixels * delta_time

            if move_dist > dist:
                move_dist = dist

            angle = math.atan2(dy, dx)
            
            # Попытка движения по прямой
            move_x = math.cos(angle) * move_dist
            move_y = math.sin(angle) * move_dist
            
            new_x = current_x + move_x
            new_y = current_y + move_y
            
            can_move = True
            if is_walkable_func:
                # Проверяем новую позицию (центр)
                grid_x = int(round((new_x - self.tile_size // 2) / self.tile_size))
                grid_y = int(round((new_y - self.tile_size // 2) / self.tile_size))
                
                # Если целевая клетка недоступна
                if not is_walkable_func(grid_x, grid_y):
                    can_move = False
                    
                    # Попытка скольжения вдоль стен
                    # Пробуем только по X
                    new_x_only = current_x + move_x
                    grid_x_only = int(round((new_x_only - self.tile_size // 2) / self.tile_size))
                    grid_y_curr = int(round((current_y - self.tile_size // 2) / self.tile_size))
                    
                    if is_walkable_func(grid_x_only, grid_y_curr):
                        new_x = new_x_only
                        new_y = current_y
                        can_move = True
                    else:
                        # Пробуем только по Y
                        new_y_only = current_y + move_y
                        grid_y_only = int(round((new_y_only - self.tile_size // 2) / self.tile_size))
                        grid_x_curr = int(round((current_x - self.tile_size // 2) / self.tile_size))
                        
                        if is_walkable_func(grid_x_curr, grid_y_only):
                            new_x = current_x
                            new_y = new_y_only
                            can_move = True

            if can_move:
                self.draw_pos[0] = new_x
                self.draw_pos[1] = new_y
                self.sprite.center_x = self.draw_pos[0]
                self.sprite.center_y = self.draw_pos[1]
                
                # Обновляем grid pos
                self.pos[0] = int(round((self.draw_pos[0] - self.tile_size // 2) / self.tile_size))
                self.pos[1] = int(round((self.draw_pos[1] - self.tile_size // 2) / self.tile_size))

    def draw(self):
        if self.sprite_list:
            self.sprite_list.draw()
            self.sprite.center_y = self.draw_pos[1]

            # Обновляем grid pos
            self.pos[0] = int(
                round((self.draw_pos[0] - self.tile_size // 2) / self.tile_size))
            self.pos[1] = int(
                round((self.draw_pos[1] - self.tile_size // 2) / self.tile_size))
            
            self.draw_health_bar()

    def update(self, delta_time, player_pos=None, dungeon_map=None):
        """Обновление босса"""
        if self.is_dead:
            return

        self.is_moving = False

        # Обновление таймера урона
        if self.hurt_timer > 0:
            self.hurt_timer = max(0, self.hurt_timer - delta_time)

        # Обновление атаки
        if self.is_attacking:
            self.attack_timer += delta_time
            
            # FIX: Check if player moved away during attack
            if player_pos:
                dx = self.sprite.center_x - player_pos[0]
                dy = self.sprite.center_y - player_pos[1]
                dist_sq = dx*dx + dy*dy
                # If player is out of reach (plus a small buffer), cancel attack
                # Using a slightly larger range than attack_range to prevent flickering
                cancel_range = self.attack_range * self.tile_size * 1.5
                if dist_sq > cancel_range * cancel_range:
                        self.is_attacking = False
                        self.attack_timer = 0.0
                        self.state = 'idle'
                        self._update_animation()
                        if self.sprite.color == (255, 100, 100):
                             self.sprite.color = (255, 255, 255)
                        return

            if self.attack_timer >= self.attack_duration:
                self.is_attacking = False
                self.attack_timer = 0.0
                self.state = 'idle'
                self._update_animation()
                if self.sprite.color == (255, 100, 100):
                     self.sprite.color = (255, 255, 255)
        # Ensure we don't get stuck in attacking state if something goes wrong
        elif self.state == 'attacking' and not self.is_attacking:
            # This shouldn't happen, but if it does, reset to idle
            self.state = 'idle'
            self._update_animation()

        # Обновление времени последней атаки
        self.last_attack_time += delta_time
        if self.powerup_active and self.max_health < self.target_max_health:
            inc = self.health_increase_speed * delta_time
            new_max = min(self.target_max_health, self.max_health + inc)
            ratio = self.health / max(1.0, self.max_health)
            self.max_health = new_max
            self.health = min(self.max_health, max(0.0, ratio * self.max_health))
            self.powerup_timer += delta_time
            phase = abs(math.sin(self.powerup_timer * 6.0))
            tint = int(200 + 55 * phase)
            try:
                self.sprite.color = (255, tint, 150)
            except Exception:
                pass
            if self.max_health >= self.target_max_health:
                self.powerup_active = False
                try:
                    self.sprite.color = (255, 255, 255)
                except Exception:
                    pass

        # Движение и поворот к игроку
        if player_pos and not self.is_attacking and self.visible:
            dx = player_pos[0] - self.draw_pos[0]
            dy = player_pos[1] - self.draw_pos[1]
            dist_sq = dx*dx + dy*dy
            dist = math.sqrt(dist_sq)
            
            # Update facing
            if abs(dx) > abs(dy):
                new_facing = 'right' if dx > 0 else 'left'
            else:
                new_facing = 'back' if dy > 0 else 'front'

            if self.facing != new_facing:
                self.facing = new_facing
                self._update_animation()

            # Attack check
            attack_dist_pixels = self.attack_range * self.tile_size
            if dist <= attack_dist_pixels:
                if self.last_attack_time >= self.attack_cooldown:
                    self.is_attacking = True
                    self.damage_dealt = False
                    self.state = 'attacking'
                    self.last_attack_time = 0.0
                    self._update_animation()
                    # Visual indication handled by animation, but we can add color flash
                    self.sprite.color = (255, 100, 100) # Red tint start
            else:
                # Movement
                if dist > 0:
                    self.is_moving = True
                    speed = self.move_speed * self.tile_size # Convert cells/sec to pixels/sec
                    move_x = (dx / dist) * speed * delta_time
                    move_y = (dy / dist) * speed * delta_time
                    
                    new_x = self.draw_pos[0] + move_x
                    new_y = self.draw_pos[1] + move_y
                    
                    # Collision detection
                    if dungeon_map:
                        # Check X
                        gx = int(new_x / self.tile_size)
                        gy = int(self.draw_pos[1] / self.tile_size)
                        if dungeon_map.is_walkable(gx, gy):
                            self.draw_pos[0] = new_x
                        
                        # Check Y
                        gx = int(self.draw_pos[0] / self.tile_size)
                        gy = int(new_y / self.tile_size)
                        if dungeon_map.is_walkable(gx, gy):
                            self.draw_pos[1] = new_y
                    else:
                        self.draw_pos[0] = new_x
                        self.draw_pos[1] = new_y

                    self.sprite.center_x = self.draw_pos[0]
                    self.sprite.center_y = self.draw_pos[1]
                    
                    # Reset color if not attacking
                    if self.sprite.color == (255, 100, 100):
                         # Сохраняем текущую альфу при сбросе цвета
                         current_alpha = self.sprite.alpha
                         self.sprite.color = (255, 255, 255)
                         self.sprite.alpha = current_alpha

            # Update grid pos
            self.pos[0] = int(self.draw_pos[0] / self.tile_size)
            self.pos[1] = int(self.draw_pos[1] / self.tile_size)

        # Обновление анимации
        self.update_animation(delta_time)

    def update_animation(self, delta_time):
        """Обновление кадров анимации"""
        if not self.current_animation_frames:
            return

        self.animation_timer += delta_time

        if self.animation_timer >= self.animation_speed:
            self.animation_timer = 0.0
            self.current_frame_index = (
                self.current_frame_index + 1) % len(self.current_animation_frames)
            self.sprite.texture = self.current_animation_frames[self.current_frame_index]

    def draw_health_bar(self):
        # Отрисовка полоски здоровья
        if not self.is_dead:
            bar_width = self.tile_size * 1.5
            bar_height = 8
            bar_x = self.draw_pos[0] - bar_width / 2
            bar_y = self.draw_pos[1] + self.tile_size / 2 + 10

            # Фон полоски
            arcade.draw_lrbt_rectangle_filled(
                bar_x, bar_x + bar_width, bar_y, bar_y + bar_height,
                arcade.color.BLACK
            )

            # Полоска здоровья
            health_percent = self.health / self.max_health
            health_width = bar_width * health_percent
            if self.powerup_active:
                pulse = abs(math.sin(self.powerup_timer * 6.0))
                health_color = (int(200 + 55 * pulse), 200, 60)
            else:
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
            if self.powerup_active:
                arcade.draw_lrbt_rectangle_outline(
                    bar_x - 2, bar_x + bar_width + 2, bar_y - 2, bar_y + bar_height + 2,
                    arcade.color.GOLD, 1
                )

    def take_damage(self, damage):
        """Наносит урон боссу"""
        if self.is_dead:
            return

        # Apply defense
        effective_damage = max(1, damage - self.defense)
        
        old_health = self.health
        self.health = max(0, self.health - effective_damage)
        self.hurt_timer = self.hurt_duration

        if self.health <= 0:
            self.health = 0
            self.is_dead = True
            self.state = 'dying'
            self._update_animation()

    def attack_player(self, player_pos):
        """Атакует игрока, если он в радиусе. player_pos в пикселях. Возвращает True только при начале новой атаки"""
        if self.is_dead:
            return False

        # Если уже атакуем, не начинаем новую атаку
        if self.is_attacking:
            return False

        # Дистанция в пикселях
        distance = math.sqrt(
            (player_pos[0] - self.draw_pos[0]) ** 2 +
            (player_pos[1] - self.draw_pos[1]) ** 2
        )

        # Радиус атаки переводим в пиксели
        attack_range_pixels = self.attack_range * self.tile_size

        if distance <= attack_range_pixels and self.last_attack_time >= self.attack_cooldown:
            self.is_attacking = True
            self.attack_timer = 0.0
            self.state = 'attacking'
            self._update_animation()
            self.last_attack_time = 0.0
            return True  # Возвращаем True только при начале новой атаки
        return False
    
    def start_powerup(self, volume=1.0):
        if self.is_dead:
            return
        self.sound_volume = volume
        if not self.powerup_active and self.max_health < self.target_max_health:
            self.powerup_active = True
            self.powerup_timer = 0.0
            try:
                path = find_music_file("boss_powerup.wav")
                if path:
                    play_once(path, volume=self.sound_volume)
            except Exception:
                pass

    def get_grid_position(self):
        """Возвращает позицию в клетках"""
        return (self.pos[0], self.pos[1])

    def is_at_position(self, x, y):
        """Проверяет, находится ли босс на позиции"""
        return self.pos[0] == x and self.pos[1] == y

    def is_alive(self):
        """Проверяет, жив ли босс"""
        return not self.is_dead and self.health > 0
