import arcade
import os
import glob
import math
import random


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
        self.attack_timer = 0.0
        self.attack_duration = 0.8
        self.animations = {}
        self.current_animation_frames = []
        self.current_frame_index = 0
        self.animation_timer = 0.0
        self.animation_speed = 0.15

        # Система здоровья
        if self.boss_type == "Caveman Boss":
            self.max_health = 200  # TODO: Увеличить хп, чтоб было сложнее убить босса
        else:
            self.max_health = 30
        self.health = self.max_health
        self.is_dead = False
        self.hurt_timer = 0.0
        self.hurt_duration = 0.3

        # Боевая система
        self.attack_range = 1.5  # Дистанция атаки в клетках
        self.attack_damage = 10  # TODO:Уменьшен урон босса, но в релизе увеличить
        self.attack_cooldown = 2.0
        self.last_attack_time = 0.0

        # Движение босса (в клетках в секунду)
        self.move_speed = 2.0

        self._initialize_sprites()
        self._load_animations()
        self._update_animation()

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

    def move_towards_player(self, player_pixel_pos, delta_time):
        """Движение к игроку (плавное)"""
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
            speed_pixels = self.move_speed * self.tile_size
            move_dist = speed_pixels * delta_time

            if move_dist > dist:
                move_dist = dist

            angle = math.atan2(dy, dx)
            self.draw_pos[0] += math.cos(angle) * move_dist
            self.draw_pos[1] += math.sin(angle) * move_dist

            # Обновляем спрайт
            self.sprite.center_x = self.draw_pos[0]
            self.sprite.center_y = self.draw_pos[1]

            # Обновляем grid pos
            self.pos[0] = int(
                round((self.draw_pos[0] - self.tile_size // 2) / self.tile_size))
            self.pos[1] = int(
                round((self.draw_pos[1] - self.tile_size // 2) / self.tile_size))

    def update(self, delta_time, player_pos=None):
        """Обновление босса"""
        if self.is_dead:
            return

        # Обновление таймера урона
        if self.hurt_timer > 0:
            self.hurt_timer = max(0, self.hurt_timer - delta_time)

        # Обновление атаки
        if self.is_attacking:
            self.attack_timer += delta_time
            
            # FIX: Check if player moved away during attack
            if player_pos:
                dx = self.center_x - player_pos[0]
                dy = self.center_y - player_pos[1]
                dist_sq = dx*dx + dy*dy
                # If player is out of reach (plus a small buffer), cancel attack
                # Using a slightly larger range than attack_range to prevent flickering
                cancel_range = self.attack_range * 1.5
                if dist_sq > cancel_range * cancel_range:
                        self.is_attacking = False
                        self.attack_timer = 0.0
                        self.state = 'idle'
                        self._update_animation()
                        return

            if self.attack_timer >= self.attack_duration:
                self.is_attacking = False
                self.attack_timer = 0.0
                self.state = 'idle'
                self._update_animation()
        # Ensure we don't get stuck in attacking state if something goes wrong
        elif self.state == 'attacking' and not self.is_attacking:
            # This shouldn't happen, but if it does, reset to idle
            self.state = 'idle'
            self._update_animation()

        # Обновление времени последней атаки
        self.last_attack_time += delta_time

        # Поворот к игроку (координаты игрока ожидаются в пикселях)
        if player_pos and not self.is_attacking:
            dx = player_pos[0] - self.draw_pos[0]
            dy = player_pos[1] - self.draw_pos[1]
            if abs(dx) > abs(dy):
                new_facing = 'right' if dx > 0 else 'left'
            else:
                new_facing = 'back' if dy > 0 else 'front'

            # Only update facing if it changed to avoid unnecessary animation updates
            if self.facing != new_facing:
                self.facing = new_facing
                # Only update animation if we're not in attacking state
                if self.state != 'attacking':
                    self._update_animation()

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

    def draw(self):
        """Отрисовка босса"""
        if self.sprite_list:
            self.sprite_list.draw()

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

    def take_damage(self, damage):
        """Наносит урон боссу"""
        if self.is_dead:
            print(f"Попытка нанести урон мертвому боссу {self.boss_type}")
            return

        old_health = self.health
        self.health = max(0, self.health - damage)
        self.hurt_timer = self.hurt_duration

        print(
            f"Босс {self.boss_type} получил {damage} урона! HP: {old_health} -> {self.health}/{self.max_health}")

        if self.health <= 0:
            self.health = 0
            self.is_dead = True
            self.state = 'dying'
            self._update_animation()
            print(f"Босс {self.boss_type} убит!")

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
            print(
                f"Босс {self.boss_type} начинает атаку на игрока! Расстояние: {distance:.2f}, радиус: {attack_range_pixels}")
            return True  # Возвращаем True только при начале новой атаки
        return False

    def get_grid_position(self):
        """Возвращает позицию в клетках"""
        return (self.pos[0], self.pos[1])

    def is_at_position(self, x, y):
        """Проверяет, находится ли босс на позиции"""
        return self.pos[0] == x and self.pos[1] == y

    def is_alive(self):
        """Проверяет, жив ли босс"""
        return not self.is_dead and self.health > 0
