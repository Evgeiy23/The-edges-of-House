import arcade
import math
import random

class Explosive(arcade.Sprite):
    def __init__(self, x, y, radius, damage, timer=None):
        super().__init__()
        self.center_x = x
        self.center_y = y
        self.explosion_radius = radius
        self.damage = damage
        self.timer = timer
        self.current_time = 0.0
        self.exploded = False
        self.blink_timer = 0.0
        self.blink_interval = 0.5
        self.color_state = 0 # 0: нормальный, 1: красный

    def update(self, delta_time: float = 1/60):
        if self.exploded:
            return

        if self.timer is not None:
            self.current_time += delta_time
            
            # Эффект мигания
            self.blink_timer += delta_time
            # Мигать быстрее, когда время истекает
            remaining = self.timer - self.current_time
            if remaining < 1.0:
                self.blink_interval = 0.1
            elif remaining < 2.0:
                self.blink_interval = 0.25
            
            if self.blink_timer >= self.blink_interval:
                self.blink_timer = 0.0
                self.color_state = 1 - self.color_state
                if self.color_state == 1:
                    self.color = arcade.color.RED
                else:
                    self.color = arcade.color.WHITE

            if self.current_time >= self.timer:
                self.explode()

    def explode(self):
        self.exploded = True

class Bomb(Explosive):
    def __init__(self, x, y):
        super().__init__(x, y, radius=100, damage=50, timer=3.0)
        # Визуальная заглушка: Текстура круга
        self.texture = arcade.make_circle_texture(15, arcade.color.BLACK)
        self.color = arcade.color.WHITE

class Dynamite(Explosive):
    def __init__(self, x, y):
        # Динамит имеет больший радиус (150) и урон (50, как запрошено)
        super().__init__(x, y, radius=150, damage=50, timer=None)
        # Визуальная заглушка: Прямоугольная текстура
        self.texture = arcade.make_soft_square_texture(15, arcade.color.RED_ORANGE, outer_alpha=255)
        
    def activate_timer(self):
        self.timer = 5.0 # Резервный таймер при необходимости

class ExplosionParticle(arcade.Sprite):
    def __init__(self, x, y, speed, angle, color, scale_speed):
        super().__init__()
        self.center_x = x
        self.center_y = y
        self.change_x = math.cos(angle) * speed
        self.change_y = math.sin(angle) * speed
        self.scale = random.uniform(0.5, 1.5)
        self.scale_speed = scale_speed
        self.color = color
        self.texture = arcade.make_circle_texture(8, arcade.color.WHITE)
        self.life = random.uniform(0.3, 0.6)
        self.age = 0

    def update(self, delta_time: float = 1/60):
        self.center_x += self.change_x * delta_time
        self.center_y += self.change_y * delta_time
        self.age += delta_time
        self.alpha = max(0, int(255 * (1 - self.age / self.life)))
        
        # Исправление обновления масштаба для Arcade 3.0 (scale - это кортеж)
        current_scale = self.scale[0] if isinstance(self.scale, (tuple, list)) else self.scale
        new_scale = current_scale + self.scale_speed
        
        if new_scale <= 0.1:
            new_scale = 0.1
        self.scale = new_scale
            
        if self.age >= self.life:
            self.kill()

class Explosion(arcade.Sprite):
    def __init__(self, x, y, max_radius):
        super().__init__()
        self.center_x = x
        self.center_y = y
        self.max_radius = max_radius
        self.growth_speed = 300 # пикселей в секунду
        self.life_time = 0.5
        self.current_time = 0.0
        
        # Визуализация
        self.texture = arcade.make_circle_texture(int(max_radius), arcade.color.ORANGE)
        self.scale = 0.1
        self.alpha = 255
        
    def update(self, delta_time: float = 1/60):
        self.current_time += delta_time
        
        # Рост
        if self.scale < 1.0:
            self.scale += (self.growth_speed / self.max_radius) * delta_time * 2.0
            if self.scale > 1.0:
                self.scale = 1.0

        # Затухание
        if self.current_time > self.life_time * 0.5:
            self.alpha = max(0, int(255 * (1 - (self.current_time / self.life_time))))
        
        if self.current_time >= self.life_time:
            self.remove_from_sprite_lists()
