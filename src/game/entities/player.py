import arcade
import os
import glob
import math


class Player:
    def __init__(self, tile_size):
        self.tile_size = tile_size
        self.pos = [0, 0]  # Текущая позиция в клетках
        self.target_pos = [0, 0]  # Целевая позиция для плавного движения
        self.draw_pos = [0.0, 0.0]  # Текущая позиция отрисовки в пикселях
        self.is_moving = False  # Флаг движения
        self.move_progress = 0.0  # Прогресс движения (0-1)
        self.move_speed = 5.0  # Скорость движения в клетках в секунду

        self.facing = 'front'
        self.state = 'idle'
        self.last_move_direction = None
        self.sprite = None
        self.sprite_list = None
        self.is_attacking = False
        self.attack_timer = 0.0
        self.attack_duration = 0.5
        self.animations = {}
        self.current_animation_frames = []
        self.current_frame_index = 0
        self.animation_timer = 0.0
        self.animation_speed = 0.1

        # Переменные для инерционного движения (сложные режимы)
        self.velocity = [0.0, 0.0]  # Текущая скорость
        self.max_speed = 3.0  # Максимальная скорость в клетках в секунду
        self.acceleration = 8.0  # Ускорение
        self.friction = 0.85  # Трение

        # Система здоровья
        self.max_health = 100
        self.health = self.max_health
        self.is_dead = False
        self.hurt_timer = 0.0
        self.hurt_duration = 0.3

        # Система регенерации здоровья
        self.health_regen_timer = 0.0
        self.health_regen_interval = 5.0  # Интервал регенерации в секундах
        self.health_regen_amount = 10  # Количество HP для восстановления

        self._initialize_sprites()
        self._load_animations()
        self._update_animation()

    def _initialize_sprites(self):
        """Initialize sprites safely with proper OpenGL context"""
        self.sprite = arcade.Sprite()
        self.sprite.center_x = 0
        self.sprite.center_y = 0
        self.sprite.scale = 0.7  # Уменьшаем размер персонажа
        self.sprite_list = arcade.SpriteList()
        self.sprite_list.append(self.sprite)

    def _load_animations(self):
        base_path = "resources/character"
        directions = ['Front', 'Back', 'Left', 'Right']
        actions = {
            'idle': 'Idle',
            'idle_blinking': 'Idle Blinking',
            'walking': 'Walking',
            'running': 'Running',
            'attacking': 'Attacking',
            'hurt': 'Hurt',
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

                        if self.sprite.scale == 0.7 and textures:  # Обновляем для нового начального масштаба
                            texture_width = textures[0].width
                            # Сохраняем уменьшенный размер
                            self.sprite.scale = (
                                self.tile_size / texture_width) * 0.7

    def _get_animation_key(self):
        if self.state == 'dying':
            return 'dying'

        direction = self.facing.lower()
        state_key = self.state

        return f"{direction}_{state_key}"

    def _update_animation(self):
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

    def update_animation(self, delta_time):
        if self.is_attacking:
            self.attack_timer += delta_time
            if self.attack_timer >= self.attack_duration:
                self.is_attacking = False
                self.attack_timer = 0.0
                self.state = 'idle'
                self._update_animation()

        if not self.current_animation_frames:
            return

        self.animation_timer += delta_time

        if self.animation_timer >= self.animation_speed:
            self.animation_timer = 0.0
            self.current_frame_index = (
                self.current_frame_index + 1) % len(self.current_animation_frames)
            self.sprite.texture = self.current_animation_frames[self.current_frame_index]

    def update_movement(self, delta_time):
        """Обновляет плавное движение игрока"""
        if self.is_moving:
            # Увеличиваем прогресс движения
            self.move_progress += delta_time * self.move_speed

            # Ограничиваем прогресс от 0 до 1
            if self.move_progress >= 1.0:
                self.move_progress = 1.0
                self.is_moving = False

                # Устанавливаем окончательную позицию
                self.pos[0] = self.target_pos[0]
                self.pos[1] = self.target_pos[1]
                self.draw_pos[0] = self.pos[0] * \
                    self.tile_size + self.tile_size // 2
                self.draw_pos[1] = self.pos[1] * \
                    self.tile_size + self.tile_size // 2
            else:
                # Интерполяция позиции (smoothstep для более плавного движения)
                t = self.move_progress
                t = t * t * (3 - 2 * t)  # smoothstep

                # Вычисляем промежуточную позицию
                start_x = self.pos[0] * self.tile_size + self.tile_size // 2
                start_y = self.pos[1] * self.tile_size + self.tile_size // 2
                target_x = self.target_pos[0] * \
                    self.tile_size + self.tile_size // 2
                target_y = self.target_pos[1] * \
                    self.tile_size + self.tile_size // 2

                # Плавное движение с уменьшенной чувствительностью
                self.draw_pos[0] = start_x + (target_x - start_x) * t
                self.draw_pos[1] = start_y + (target_y - start_y) * t

            # Обновляем позицию спрайта
            self.sprite.center_x = self.draw_pos[0]
            self.sprite.center_y = self.draw_pos[1]
        else:
            # Плавное замедление до центра клетки, если мы не в движении
            current_x = self.draw_pos[0]
            current_y = self.draw_pos[1]
            target_x = self.pos[0] * self.tile_size + self.tile_size // 2
            target_y = self.pos[1] * self.tile_size + self.tile_size // 2

            # Если мы не точно по центру клетки, плавно двигаемся к центру
            if abs(current_x - target_x) > 0.1 or abs(current_y - target_y) > 0.1:
                # Более плавная коррекция
                lerp_factor = min(1.0, delta_time * 7.0)
                self.draw_pos[0] = current_x + \
                    (target_x - current_x) * lerp_factor
                self.draw_pos[1] = current_y + \
                    (target_y - current_y) * lerp_factor
                self.sprite.center_x = self.draw_pos[0]
                self.sprite.center_y = self.draw_pos[1]

    def update_inertial_movement(self, delta_time, move_input):
        dx, dy = move_input

        if dx != 0:
            self.velocity[0] += dx * self.acceleration * delta_time
        if dy != 0:
            self.velocity[1] += dy * self.acceleration * delta_time

        self.velocity[0] *= self.friction
        self.velocity[1] *= self.friction

        speed = math.sqrt(self.velocity[0]**2 + self.velocity[1]**2)
        if speed > self.max_speed:
            scale = self.max_speed / speed
            self.velocity[0] *= scale
            self.velocity[1] *= scale

        if abs(self.velocity[0]) < 0.01:
            self.velocity[0] = 0
        if abs(self.velocity[1]) < 0.01:
            self.velocity[1] = 0

        if self.velocity[0] != 0 or self.velocity[1] != 0:
            new_x = self.draw_pos[0] + self.velocity[0] * \
                self.tile_size * delta_time
            new_y = self.draw_pos[1] + self.velocity[1] * \
                self.tile_size * delta_time

            self.draw_pos[0] = new_x
            self.draw_pos[1] = new_y

            self.sprite.center_x = self.draw_pos[0]
            self.sprite.center_y = self.draw_pos[1]

            self.pos[0] = int(
                round((self.draw_pos[0] - self.tile_size // 2) / self.tile_size))
            self.pos[1] = int(
                round((self.draw_pos[1] - self.tile_size // 2) / self.tile_size))

    def draw(self):
        if self.sprite_list:
            self.sprite_list.draw()

    def move(self, dx, dy):
        if self.is_moving:
            return False

        self.target_pos[0] = self.pos[0] + dx
        self.target_pos[1] = self.pos[1] + dy

        self.is_moving = True
        self.move_progress = 0.0

        if dx != 0 or dy != 0:
            if dy != 0:
                self.facing = 'back' if dy > 0 else 'front'
            else:
                self.facing = 'right' if dx > 0 else 'left'
            self.last_move_direction = (dx, dy)

        return True

    def move_to(self, x, y):
        self.pos[0] = x
        self.pos[1] = y
        self.target_pos[0] = x
        self.target_pos[1] = y
        self.draw_pos[0] = x * self.tile_size + self.tile_size // 2
        self.draw_pos[1] = y * self.tile_size + self.tile_size // 2
        self.sprite.center_x = self.draw_pos[0]
        self.sprite.center_y = self.draw_pos[1]
        self.is_moving = False
        self.move_progress = 0.0

    def set_pos(self, x, y):
        self.move_to(x, y)

    def set_state(self, state):
        if self.state != state:
            self.state = state
            self._update_animation()

    def attack(self):
        if not self.is_attacking:
            self.is_attacking = True
            self.attack_timer = 0.0
            self.state = 'attacking'
            self._update_animation()

    def get_pixel_position(self):
        return (self.draw_pos[0], self.draw_pos[1])

    def get_grid_position(self):
        return (self.pos[0], self.pos[1])

    def is_at_position(self, x, y):
        return self.pos[0] == x and self.pos[1] == y

    def reset_velocity(self):
        self.velocity[0] = 0.0
        self.velocity[1] = 0.0

    def take_damage(self, damage):
        """Наносит урон игроку"""
        if self.is_dead:
            return

        old_health = self.health
        self.health = max(0, self.health - damage)
        self.hurt_timer = self.hurt_duration

        print(
            f"Игрок получил {damage} урона! HP: {old_health} -> {self.health}/{self.max_health}")

        if self.health <= 0:
            self.health = 0
            self.is_dead = True
            self.state = 'dying'
            self._update_animation()
            print("Игрок умер!")

    def heal(self, amount):
        """Восстанавливает здоровье"""
        if not self.is_dead:
            self.health = min(self.max_health, self.health + amount)

    def is_alive(self):
        """Проверяет, жив ли игрок"""
        return not self.is_dead and self.health > 0

    def update_health_regen(self, delta_time):
        """Обновляет регенерацию здоровья"""
        if self.is_dead or self.health >= self.max_health:
            return

        self.health_regen_timer += delta_time

        if self.health_regen_timer >= self.health_regen_interval:
            self.health_regen_timer = 0.0
            self.heal(self.health_regen_amount)
