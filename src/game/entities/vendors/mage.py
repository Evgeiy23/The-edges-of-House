import arcade
import math
import os
from .base import BaseVendor

class MageNPC(BaseVendor):
    def __init__(self, tile_size, pos=(0, 0), speed=120.0, min_follow_dist=2.5, max_follow_dist=12.0):
        BaseVendor.__init__(self, tile_size, pos)
        self.interaction_text = "Нажмите E чтобы поговорить"
        
        # Параметры следования
        self.speed = speed
        self.min_follow_dist = min_follow_dist * tile_size
        self.max_follow_dist = max_follow_dist * tile_size
        
        # Состояние анимации
        self.spawn_anim_active = False
        self.spawn_anim_t = 0.0
        self.spawn_anim_duration = 0.5
        self.start_draw_pos = list(self.draw_pos)
        self.target_draw_pos = list(self.draw_pos)

    def _load_resources(self):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
        
        # Используем спрайт из главного меню (0_Sage_Idle_000.png)
        # Путь: resources/npcs/Sage/PNG/PNG Sequences/Idle/0_Sage_Idle_000.png
        rel_path = os.path.join("resources", "npcs", "Sage", "PNG", "PNG Sequences", "Idle", "0_Sage_Idle_000.png")
        abs_path = os.path.join(base_dir, rel_path)
        
        texture = self._load_texture_from_path(abs_path)
        if not texture:
            # Запасной вариант
            texture = self._load_texture_from_path(rel_path)

        if texture:
            self.sprite = arcade.Sprite()
            self.sprite.texture = texture
            if texture.width:
                self.sprite.scale = (self.tile_size / texture.width) * 0.9
            self.sprite.center_x = self.draw_pos[0]
            self.sprite.center_y = self.draw_pos[1]
            
            # Делаем его фиолетовым/синим, чтобы он был похож на Мага (как в главном меню)
            self.sprite.color = (150, 100, 255)
            self.sprite_list.append(self.sprite)
        else:
            self.sprite = arcade.SpriteSolidColor(self.tile_size, self.tile_size, arcade.color.PURPLE)
            self.sprite.center_x = self.draw_pos[0]
            self.sprite.center_y = self.draw_pos[1]
            self.sprite_list.append(self.sprite)

        # Текстура всплывающего окна для подсказки взаимодействия
        rel_popup_path = os.path.join("resources", "npcs", "Warlord", "popup", "PNG", "popup_1.png")
        abs_popup_path = os.path.join(base_dir, rel_popup_path)
        self.popup_texture = self._load_texture_from_path(abs_popup_path) or self._load_texture_from_path(rel_popup_path)

    def update(self, delta_time, player_pos=None, dungeon_map=None):
        """Обновление состояния мага, включая анимацию и движение."""
        # 1. Анимация появления
        if self.spawn_anim_active:
            self.spawn_anim_t += delta_time
            t = max(0.0, min(1.0, self.spawn_anim_t / max(0.0001, self.spawn_anim_duration)))
            
            # Простое появление
            if self.sprite:
                self.sprite.alpha = int(255 * t)
                
            if t >= 1.0:
                self.spawn_anim_active = False
        
        # 2. Логика движения (следование за игроком)
        if player_pos and dungeon_map and not self.spawn_anim_active:
            self._update_movement(delta_time, player_pos, dungeon_map)
        
        # 3. Анимация пульсации в простое (для визуальной уникальности)
        if self.sprite:
            # пульсация на основе времени
            time_val = getattr(self, "_anim_timer", 0.0) + delta_time
            self._anim_timer = time_val
            
            # Пульсация масштаба немного
            base_scale = getattr(self, "_base_scale", self.sprite.scale)
            
            # Убедимся, что base_scale это float
            if isinstance(base_scale, (list, tuple)):
                base_scale = base_scale[0]
            
            if not hasattr(self, "_base_scale"):
                self._base_scale = base_scale
            
            scale_pulse = 1.0 + 0.05 * math.sin(time_val * 3.0)
            self.sprite.scale = base_scale * scale_pulse

    def _update_movement(self, delta_time, player_pos, dungeon_map):
        """Логика следования за игроком с учетом препятствий."""
        # Текущая позиция (в пикселях)
        curr_x, curr_y = self.draw_pos
        
        # Вектор до игрока
        dx = player_pos[0] - curr_x
        dy = player_pos[1] - curr_y
        dist_sq = dx*dx + dy*dy
        dist = math.sqrt(dist_sq)
        
        # 1. Если слишком далеко - телепортируемся поближе (за экран)
        if dist > self.max_follow_dist:
            # Попытка найти валидную точку ближе к игроку (например, на расстоянии min_follow_dist * 2)
            angle = math.atan2(dy, dx)
            target_dist = self.min_follow_dist * 2
            spawn_x = player_pos[0] - math.cos(angle) * target_dist
            spawn_y = player_pos[1] - math.sin(angle) * target_dist
            
            if self._is_valid_pos(spawn_x, spawn_y, dungeon_map):
                self.draw_pos = [spawn_x, spawn_y]
                # Сброс анимации появления для эффекта
                self.spawn_anim_active = True
                self.spawn_anim_t = 0.0
                if self.sprite:
                    self.sprite.alpha = 0
            else:
                # Если точка занята, просто телепортируемся к игроку (на его позицию), если там можно ходить
                # или оставляем как есть до следующего кадра
                pass
                
        # 2. Если дальше минимальной дистанции - двигаемся к игроку
        elif dist > self.min_follow_dist:
            # Нормализация и скорость
            move_step = self.speed * delta_time
            if move_step > dist:
                move_step = dist
                
            dir_x = dx / dist
            dir_y = dy / dist
            
            # Попытка движения по осям (простая физика скольжения)
            new_x = curr_x + dir_x * move_step
            new_y = curr_y + dir_y * move_step
            
            # Проверяем X
            if self._is_valid_pos(new_x, curr_y, dungeon_map):
                curr_x = new_x
            
            # Проверяем Y
            if self._is_valid_pos(curr_x, new_y, dungeon_map):
                curr_y = new_y
                
            self.draw_pos = [curr_x, curr_y]
            
        # Обновление позиции спрайта
        if self.sprite:
            self.sprite.center_x = self.draw_pos[0]
            self.sprite.center_y = self.draw_pos[1]
            
        # Обновление логической позиции (в тайлах)
        self.pos = [self.draw_pos[0] / self.tile_size, self.draw_pos[1] / self.tile_size]

    def _is_valid_pos(self, x, y, dungeon_map):
        """Проверка проходимости точки (в пикселях)."""
        tx = int(x / self.tile_size)
        ty = int(y / self.tile_size)
        
        if 0 <= tx < dungeon_map.map_width and 0 <= ty < dungeon_map.map_height:
            return dungeon_map.is_walkable(tx, ty)
        return False

    def draw_ui(self, player_pos, camera_pos=(0, 0)):
        """
        Рисует элементы UI для Мага.
        Добавляет визуальную подсветку (круг), когда игрок рядом, чтобы указать на взаимодействие.
        """
        super().draw_ui(player_pos, camera_pos)
        
        # Проверка дистанции для индикатора взаимодействия
        dx = self.draw_pos[0] - player_pos[0]
        dy = self.draw_pos[1] - player_pos[1]
        dist_sq = dx*dx + dy*dy
        interaction_dist_sq = (self.tile_size * 3) ** 2  # Немного больше, чем дальность взаимодействия
        
        if dist_sq < interaction_dist_sq:
            # Рисуем светящийся круг под/вокруг мага
            arcade.draw_circle_outline(
                self.draw_pos[0],
                self.draw_pos[1],
                self.tile_size * 0.8,
                (150, 100, 255, 150), # Фиолетовый с прозрачностью
                3
            )

    def interact(self):
        """
        API взаимодействия для NPC Мага.
        
        Возвращает:
            bool: True, если взаимодействие было успешным/обработано.
            
        Описание:
            Этот метод вызывается, когда игрок нажимает клавишу взаимодействия (E),
            находясь в радиусе действия Мага.
            
            Текущая реализация:
            - Сигнализирует GameWindow открыть MageDialog.
            - Не поддерживает внутреннее состояние диалога; делегирует менеджеру UI.
            
        Планы на будущее API:
            - Может принимать параметр 'action' для указания типа взаимодействия (магазин, квест, разговор).
            - Может возвращать структуру данных, описывающую доступные варианты диалога.
        """
        # Мы не используем здесь стандартную логику всплывающих окон, потому что нам нужно полноценное диалоговое окно.
        # Этот метод будет вызван GameWindow, но GameWindow также управляет UI.
        # Поэтому мы можем просто вернуть True, чтобы сигнализировать об успешном запросе взаимодействия.
        return True
