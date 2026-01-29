import heapq
import math

class Follower:
    """
    Базовый класс или миксин для сущностей, которым нужно следовать за целью (например, за игроком),
    избегая препятствий с использованием поиска пути A*.
    """
    def __init__(self):
        self.path = []
        self.path_index = 0
        self.repath_timer = 0.0
        self.repath_interval = 0.5  # Пересчитывать путь каждые 0.5 секунды
        self.last_target_grid_pos = None

    def move_along_path(self, delta_time, current_pixel_pos, target_pixel_pos, move_speed, tile_size, dungeon_map):
        """
        Вычисляет вектор движения для следования по пути.
        Возвращает кортеж (dx, dy) для движения.
        """
        current_grid_pos = (int(current_pixel_pos[0] // tile_size), int(current_pixel_pos[1] // tile_size))
        target_grid_pos = (int(target_pixel_pos[0] // tile_size), int(target_pixel_pos[1] // tile_size))
        
        self.repath_timer -= delta_time
        
        # Пересчитываем путь, если таймер истек или цель значительно переместилась
        if self.repath_timer <= 0 or self.last_target_grid_pos != target_grid_pos:
            # Оптимизация: Сначала проверяем линию видимости
            if hasattr(dungeon_map, 'has_line_of_sight') and dungeon_map.has_line_of_sight(current_grid_pos, target_grid_pos):
                 self.path = [target_grid_pos]
            else:
                 self.path = self._find_path(current_grid_pos, target_grid_pos, dungeon_map)
                 
            self.path_index = 0
            self.repath_timer = self.repath_interval
            self.last_target_grid_pos = target_grid_pos
            
        if not self.path:
            # Запасной вариант: прямое движение, если нет пути (или рядом)
            return self._get_direct_vector(current_pixel_pos, target_pixel_pos, move_speed, delta_time)

        # Получаем следующую путевую точку
        if self.path_index < len(self.path):
            next_node = self.path[self.path_index]
            
            # Проверяем, достигли ли мы следующего узла (центр плитки)
            next_pixel_x = next_node[0] * tile_size + tile_size / 2
            next_pixel_y = next_node[1] * tile_size + tile_size / 2
            
            dist_to_node = math.sqrt((next_pixel_x - current_pixel_pos[0])**2 + (next_pixel_y - current_pixel_pos[1])**2)
            
            if dist_to_node < tile_size * 0.1: # Достаточно близко
                self.path_index += 1
                if self.path_index >= len(self.path):
                    # Конец пути - пытаемся двигаться прямо к цели для точности
                    return self._get_direct_vector(current_pixel_pos, target_pixel_pos, move_speed, delta_time)
                    
                next_node = self.path[self.path_index]
                next_pixel_x = next_node[0] * tile_size + tile_size / 2
                next_pixel_y = next_node[1] * tile_size + tile_size / 2

            # Движемся к следующему узлу
            angle = math.atan2(next_pixel_y - current_pixel_pos[1], next_pixel_x - current_pixel_pos[0])
            dx = math.cos(angle) * move_speed * delta_time
            dy = math.sin(angle) * move_speed * delta_time
            return dx, dy
            
        return (0, 0)

    def _get_direct_vector(self, current, target, speed, dt):
        dx = target[0] - current[0]
        dy = target[1] - current[1]
        dist = math.sqrt(dx*dx + dy*dy)
        if dist < 1.0:
            return (0, 0)
        
        angle = math.atan2(dy, dx)
        return math.cos(angle) * speed * dt, math.sin(angle) * speed * dt

    def _find_path(self, start, end, dungeon_map):
        # Алгоритм A*
        def heuristic(a, b):
            return abs(a[0] - b[0]) + abs(a[1] - b[1])

        open_set = []
        heapq.heappush(open_set, (0, start))
        came_from = {}
        g_score = {start: 0}
        f_score = {start: heuristic(start, end)}
        
        iterations = 0
        max_iterations = 5000 # Увеличенный лимит для больших карт
        
        while open_set and iterations < max_iterations:
            iterations += 1
            current = heapq.heappop(open_set)[1]
            
            if current == end:
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.reverse()
                return path
            
            neighbors = [
                (current[0], current[1] - 1),
                (current[0], current[1] + 1),
                (current[0] - 1, current[1]),
                (current[0] + 1, current[1])
            ]
            
            for neighbor in neighbors:
                if not dungeon_map.is_walkable(neighbor[0], neighbor[1]):
                    continue
                    
                tentative_g_score = g_score[current] + 1
                
                if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f = tentative_g_score + heuristic(neighbor, end)
                    f_score[neighbor] = f
                    heapq.heappush(open_set, (f, neighbor))
                    
        return []
