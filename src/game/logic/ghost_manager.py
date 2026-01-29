import random
import uuid
import math
from game.entities.ghost import Ghost

import arcade

class GhostManager:
    def __init__(self, tile_size):
        self.tile_size = tile_size
        self.ghosts = [] # Список объектов сущностей призраков
        self.sprite_list = arcade.SpriteList() # Оптимизация: Пакетная отрисовка
        self.ghost_records = [] # Список словарей, как запрошено: {id, initial_pos, ...}
        self.logic_timer = 0.0
        self.logic_interval = 1.0 # Интервал 1 секунда
        self.active_ghosts = [] # Оптимизация: Обновлять только эти
        
    def spawn_ghosts(self, dungeon_map, count, level=1):
        """
        Создает призраков в коридорах.
        """
        self.ghosts.clear()
        self.sprite_list = arcade.SpriteList()
        self.ghost_records.clear()
        self.active_ghosts.clear()

        if not hasattr(dungeon_map, 'corridor_tiles') or not dungeon_map.corridor_tiles:
            # Резервный вариант, если плитки коридора не найдены
            return
            
        # Преобразование множества в список для случайного выбора
        corridor_tiles = list(dungeon_map.corridor_tiles)
        
        for _ in range(count):
            if not corridor_tiles:
                break
                
            # Выбрать случайную плитку коридора
            idx = random.randint(0, len(corridor_tiles) - 1)
            gx, gy = corridor_tiles[idx]
            
            # Создать сущность призрака
            ghost = Ghost(self.tile_size, (gx, gy), level)
            ghost.id = str(uuid.uuid4())
            
            # Установить скорость призрака (быстрее, чем у игрока 5.0 тайлов/сек)
            # Скорость игрока 5.0 * tile_size. Призрак будет 6.0 * tile_size.
            ghost.move_speed_tiles = 6.0 
            ghost.move_speed_pixels = ghost.move_speed_tiles * self.tile_size
            
            self.ghosts.append(ghost)
            if ghost.sprite:
                self.sprite_list.append(ghost.sprite)
            
            # Создать запись (Словарь)
            record = {
                "id": ghost.id,
                "initial_pos": (gx, gy),
                "current_pos": (gx, gy), # Координаты сетки
                "target_pos": None,
                "state": "idle", # idle, chase (ожидание, преследование)
                "speed": ghost.move_speed_tiles
            }
            self.ghost_records.append(record)
            
    def update(self, delta_time, player, dungeon_map, viewport_rect=None):
        """
        Обновляет логику и физику призраков.
        viewport_rect: (left, right, bottom, top) в пикселях для отсечения
        """
        # 1. Обновление логики (Каждую 1 секунду)
        self.logic_timer += delta_time
        if self.logic_timer >= self.logic_interval:
            self.logic_timer = 0.0
            self._update_ai_logic(player)
            # Обновлять активный список периодически
            self._update_active_list(viewport_rect)
            
        # 2. Обновление физики/анимации (Каждый кадр)
        # Оптимизация: Обновлять только призраков, которые вероятно видимы или активны
        targets = self.active_ghosts if self.active_ghosts else self.ghosts
        
        # Вычислить центр камеры для LOD
        cx, cy = 0, 0
        if viewport_rect:
             cx = (viewport_rect[0] + viewport_rect[1]) / 2
             cy = (viewport_rect[2] + viewport_rect[3]) / 2
        elif player:
             cx, cy = player.draw_pos
        
        for ghost in targets:
            # Найти соответствующую запись (Оптимизация: Кэшировать эту связь при необходимости, но поиск достаточно быстрый для <100 призраков)
            record = next((r for r in self.ghost_records if r["id"] == ghost.id), None)
            
            if record:
                # Синхронизировать состояние из записи в сущность
                ghost.state = record["state"]
                
                # Вычисление LOD
                lod = 0
                if viewport_rect:
                    dist_sq = (ghost.draw_pos[0] - cx)**2 + (ghost.draw_pos[1] - cy)**2
                    if dist_sq > 1200*1200: # Далеко (1200 пикселей)
                        lod = 2
                    elif dist_sq > 600*600: # Средне (600 пикселей)
                        lod = 1
                
                # Обновить сущность (движение, анимация)
                ghost.update(delta_time, player, dungeon_map, lod_level=lod)
                
                # Синхронизировать позицию и состояние обратно в запись
                record["current_pos"] = tuple(ghost.pos)
                record["state"] = ghost.state

    def _update_active_list(self, viewport_rect):
        """
        Обновляет список активных призраков на основе вьюпорта + буфера.
        """
        if not viewport_rect:
            self.active_ghosts = list(self.ghosts)
            return

        left, right, bottom, top = viewport_rect
        buffer = 500 # Дополнительный буфер в пикселях
        
        self.active_ghosts = []
        for ghost in self.ghosts:
            # Проверить, находится ли призрак на разумном расстоянии или преследует
            # Всегда обновлять преследующих призраков независимо от видимости
            if ghost.state == 'chase' or ghost.state == 'attack':
                self.active_ghosts.append(ghost)
                continue
                
            gx, gy = ghost.draw_pos
            if (left - buffer < gx < right + buffer) and (bottom - buffer < gy < top + buffer):
                self.active_ghosts.append(ghost)

    def _update_ai_logic(self, player):
        """
        Выполняет периодические проверки ИИ: расстояние, переходы состояний.
        """
        if not player:
            return
            
        player_pos = player.pos # Координаты сетки
        
        for record in self.ghost_records:
            ghost_pos = record["current_pos"]
            
            # Вычислить расстояние (Манхэттенское или Евклидово? "Радиус" подразумевает Евклидово)
            dist = math.sqrt((ghost_pos[0] - player_pos[0])**2 + (ghost_pos[1] - player_pos[1])**2)
            
            # Логика:
            # Если расст в [4, 7]: Активировать преследование
            # Если расст < 4: Все еще преследовать (подразумевается, так как должен атаковать на 1)
            # Если расст > 10: Остановить преследование (Гистерезис)
            
            if 4.0 <= dist <= 7.0:
                record["state"] = "chase"
            elif dist < 4.0:
                 # Если уже близко, убедиться, что мы преследуем/атакуем
                 if record["state"] == "idle":
                     record["state"] = "chase"
            elif dist > 10.0:
                record["state"] = "idle"
                
    def draw(self):
        # Этот метод может не использоваться, если GameWindowRendering обрабатывает отрисовку вручную для Тумана Войны.
        # Но если используется, использовать пакетную отрисовку.
        if self.sprite_list:
            self.sprite_list.draw()

    def remove_ghost(self, ghost):
        if ghost in self.ghosts:
            self.ghosts.remove(ghost)
        if ghost in self.active_ghosts:
            self.active_ghosts.remove(ghost)
        if ghost.sprite and ghost.sprite in self.sprite_list:
            self.sprite_list.remove(ghost.sprite)
        # Удалить запись
        self.ghost_records = [r for r in self.ghost_records if r["id"] != ghost.id]

    def get_ghosts(self):
        return self.ghosts
