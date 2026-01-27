import random
import time

def generate_dungeon(map_width, map_height, cfg, spawn_corner=None, seed=None):
    if seed is None:
        seed = int(time.time())
    random.seed(seed)
    
    print(f"Generating map with seed: {seed}")
    
    # Use the requested 3-room generation logic
    return _generate_three_room_layout(map_width, map_height, cfg, spawn_corner, seed)

def _generate_three_room_layout(map_width, map_height, cfg, spawn_corner=None, seed=None):
    room_size_min = getattr(cfg, 'MIN_ROOM_SIZE', 8)
    room_size_max = getattr(cfg, 'MAX_ROOM_SIZE', 16)
    
    map_data = [[1 for _ in range(map_width)] for _ in range(map_height)]
    rooms = []
    room_tile_map = {}
    corridor_tiles = set()
    
    # 1. Spawn Room (Left side)
    if spawn_corner == "bottom_left":
        x1 = random.randint(2, 5)
        y1 = random.randint(2, 5)
    else:
        x1 = random.randint(2, map_width // 4)
        y1 = random.randint(2, map_height // 4)
        
    w1 = random.randint(room_size_min, room_size_max)
    h1 = random.randint(room_size_min, room_size_max)
    
    room1 = {"x1": x1, "y1": y1, "x2": x1 + w1, "y2": y1 + h1}
    rooms.append(room1)
    
    # 2. Boss Room (Right side, Far away)
    # Boss room should be enclosed with a specific entry point
    w2 = random.randint(room_size_min + 4, room_size_max + 4) # Slightly larger
    h2 = random.randint(room_size_min + 4, room_size_max + 4)
    
    x2 = random.randint(map_width - w2 - 10, map_width - w2 - 2)
    y2 = random.randint(map_height - h2 - 10, map_height - h2 - 2)
    
    room2 = {"x1": x2, "y1": y2, "x2": x2 + w2, "y2": y2 + h2}
    rooms.append(room2)
    
    # 3. Intermediate Room (Middle)
    w3 = random.randint(room_size_min, room_size_max)
    h3 = random.randint(room_size_min, room_size_max)
    
    x3 = random.randint(map_width // 3, 2 * map_width // 3)
    y3 = random.randint(map_height // 3, 2 * map_height // 3)
    
    room3 = {"x1": x3, "y1": y3, "x2": x3 + w3, "y2": y3 + h3}
    rooms.append(room3)
    
    # Carve Rooms
    for i, room in enumerate(rooms):
        for y in range(room["y1"], room["y2"]):
            for x in range(room["x1"], room["x2"]):
                map_data[y][x] = 1 # Wall border
        
        for y in range(room["y1"] + 1, room["y2"] - 1):
            for x in range(room["x1"] + 1, room["x2"] - 1):
                map_data[y][x] = 2 # Floor
                room_tile_map[(x, y)] = i

    # Connect Rooms: Room 1 -> Room 3 -> Room 2
    corridors_count = 0
    
    def create_tunnel(r_start, r_end):
        nonlocal corridors_count
        c1 = ((r_start["x1"] + r_start["x2"]) // 2, (r_start["y1"] + r_start["y2"]) // 2)
        c2 = ((r_end["x1"] + r_end["x2"]) // 2, (r_end["y1"] + r_end["y2"]) // 2)
        
        # Horizontal then Vertical
        if random.random() < 0.5:
            # H
            for x in range(min(c1[0], c2[0]), max(c1[0], c2[0]) + 1):
                if map_data[c1[1]][x] == 1:
                    map_data[c1[1]][x] = 0
                    corridor_tiles.add((x, c1[1]))
                    corridors_count += 1
                # Widen
                if map_data[c1[1]+1][x] == 1:
                     map_data[c1[1]+1][x] = 0
                     corridor_tiles.add((x, c1[1]+1))
            
            # V
            for y in range(min(c1[1], c2[1]), max(c1[1], c2[1]) + 1):
                if map_data[y][c2[0]] == 1:
                    map_data[y][c2[0]] = 0
                    corridor_tiles.add((c2[0], y))
                    corridors_count += 1
                # Widen
                if map_data[y][c2[0]+1] == 1:
                    map_data[y][c2[0]+1] = 0
                    corridor_tiles.add((c2[0]+1, y))
        else:
            # V
            for y in range(min(c1[1], c2[1]), max(c1[1], c2[1]) + 1):
                if map_data[y][c1[0]] == 1:
                    map_data[y][c1[0]] = 0
                    corridor_tiles.add((c1[0], y))
                    corridors_count += 1
                if map_data[y][c1[0]+1] == 1:
                    map_data[y][c1[0]+1] = 0
                    corridor_tiles.add((c1[0]+1, y))
            
            # H
            for x in range(min(c1[0], c2[0]), max(c1[0], c2[0]) + 1):
                if map_data[c2[1]][x] == 1:
                    map_data[c2[1]][x] = 0
                    corridor_tiles.add((x, c2[1]))
                    corridors_count += 1
                if map_data[c2[1]+1][x] == 1:
                     map_data[c2[1]+1][x] = 0
                     corridor_tiles.add((x, c2[1]+1))

    create_tunnel(rooms[0], rooms[2])
    create_tunnel(rooms[2], rooms[1]) # Connect to Boss Room

    # Boss Room Logic (Room 2)
    # The exit should be INSIDE the boss room, not at the edge.
    # We will place it at the center of the boss room.
    # And we need to define the "door" to the boss room to close it.
    
    # Find the entrance to the boss room (approximate)
    # Since we connected Room 3 -> Room 2, the entrance is where the corridor meets Room 2.
    # We can just iterate the perimeter of Room 2 and find floor tiles that are corridors.
    
    boss_room = rooms[1]
    exit_door_positions = []
    
    # Scan perimeter
    for x in range(boss_room["x1"], boss_room["x2"]):
        # Top
        if (x, boss_room["y1"]) in corridor_tiles or map_data[boss_room["y1"]][x] == 0:
            exit_door_positions.append((x, boss_room["y1"]))
        # Bottom
        if (x, boss_room["y2"]-1) in corridor_tiles or map_data[boss_room["y2"]-1][x] == 0:
            exit_door_positions.append((x, boss_room["y2"]-1))
            
    for y in range(boss_room["y1"], boss_room["y2"]):
        # Left
        if (boss_room["x1"], y) in corridor_tiles or map_data[y][boss_room["x1"]] == 0:
            exit_door_positions.append((boss_room["x1"], y))
        # Right
        if (boss_room["x2"]-1, y) in corridor_tiles or map_data[y][boss_room["x2"]-1] == 0:
             exit_door_positions.append((boss_room["x2"]-1, y))
             
    # Place Exit in Center of Boss Room
    ex = (boss_room["x1"] + boss_room["x2"]) // 2
    ey = (boss_room["y1"] + boss_room["y2"]) // 2
    
    # Ensure exit is on floor
    map_data[ey][ex] = 2 # Initially just floor. Will be drawn as Red Square when active.
    # We don't set it to 3 (Exit) yet because it's inactive. 
    # Logic in GameWindow will handle activation and drawing.
    # Actually, let's mark it as 3 but handle "inactive" state in game logic
    # OR better: keep it 2, and store coordinates. GameWindow will check "if boss dead -> draw portal & check collision"
    
    # Let's set it to 3 so logic works, but we can override drawing/behavior
    map_data[ey][ex] = 3 
    
    exit_pos = (ex, ey)
    exit_room_idx = 1 # Boss Room is index 1

    print(f"--- Map Generation Statistics ---")
    print(f"Rooms count: {len(rooms)}")
    print(f"Corridors segments created: {corridors_count}")

    return map_data, rooms, room_tile_map, list(corridor_tiles), exit_pos, exit_room_idx, exit_door_positions

def _original_generate_dungeon(map_width, map_height, cfg, spawn_corner=None):
    room_size = max(6, random.randint(cfg.MIN_ROOM_SIZE, cfg.MAX_ROOM_SIZE))
    # Увеличиваем ширину коридоров для комфортного прохода
    corridor_width = max(8, getattr(cfg, 'CORRIDOR_WIDTH', 14))
    # Увеличиваем толщину проходов
    passage_thickness = max(3, getattr(cfg, 'PASSAGE_THICKNESS', 3))
    exit_room_multiplier = getattr(cfg, 'EXIT_ROOM_SIZE_MULTIPLIER', 1.5)
    center_x = map_width // 2

    base_offset = room_size + corridor_width + random.randint(3, 6)
    possible_offsets = [0, base_offset, -base_offset,
                        2 * base_offset, -2 * base_offset]
    possible_positions = []
    for off in possible_offsets:
        cx = center_x + off
        if 2 < cx < map_width - 3:
            possible_positions.append(cx)
    if not possible_positions:
        possible_positions = [center_x]
    k = min(len(possible_positions), random.randint(2, 4))
    import random as _r
    corridor_positions = sorted(_r.sample(possible_positions, k))

    map_data = [[1 for _ in range(map_width)] for _ in range(map_height)]
    rooms = []
    room_tile_map = {}
    corridor_tiles = set()

    for cx in corridor_positions:
        for y in range(1, map_height - 1):
            local_w = max(2, corridor_width)  # Ширина коридора 2 тайла
            for w in range(-(local_w // 2), local_w // 2 + 1):
                x = cx + w
                if 0 <= x < map_width:
                    map_data[y][x] = 0
                    corridor_tiles.add((x, y))

    mid_y = map_height // 2
    local_w = max(2, corridor_width)  # Ширина коридора 2 тайла
    for x in range(1, map_width - 1):
        for w in range(-(local_w // 2), local_w // 2 + 1):
            y = mid_y + w
            if 0 <= y < map_height:
                map_data[y][x] = 0
                corridor_tiles.add((x, y))

    def attach_room_at(corridor_x, corridor_y, dir_x, dir_y):
        room_x1 = corridor_x + dir_x * (room_size + corridor_width + 2)
        room_y1 = corridor_y + dir_y * (room_size + corridor_width + 2)
        room_x1 = max(1, min(map_width - room_size - 2, room_x1))
        room_y1 = max(1, min(map_height - room_size - 2, room_y1))
        room = {
            "x1": room_x1,
            "y1": room_y1,
            "x2": room_x1 + room_size + 2,
            "y2": room_y1 + room_size + 2,
        }
        if overlaps(room):
            return
        rooms.append(room)

        door_x = corridor_x
        door_y = corridor_y
        if dir_x != 0:
            door_x = room["x1"] if dir_x < 0 else room["x2"] - 1
            door_y = corridor_y
        else:
            door_x = corridor_x
            door_y = room["y1"] if dir_y < 0 else room["y2"] - 1

        # Создаем проход 2x2 тайла
        passage_size = 2  # 2 блока
        if dir_x != 0:
            # Горизонтальный проход (комната слева/справа) - 2 тайла по вертикали и 2 по горизонтали
            for dy in range(passage_size):  # 2 тайла по вертикали
                # 2 тайла по горизонтали (в сторону комнаты)
                for dx in range(passage_size):
                    px = door_x + (dx if dir_x > 0 else -dx)
                    py = door_y + dy
                    if 0 <= px < map_width and 0 <= py < map_height:
                        map_data[py][px] = 0
                        corridor_tiles.add((px, py))
        else:
            # Вертикальный проход (комната сверху/снизу) - 2 тайла по горизонтали и 2 по вертикали
            for dx in range(passage_size):  # 2 тайла по горизонтали
                for dy in range(passage_size):  # 2 тайла по вертикали (в сторону комнаты)
                    px = door_x + dx
                    py = door_y + (dy if dir_y > 0 else -dy)
                    if 0 <= px < map_width and 0 <= py < map_height:
                        map_data[py][px] = 0
                        corridor_tiles.add((px, py))
        interior_x1 = room["x1"] + 1
        interior_x2 = room["x2"] - 1
        interior_y1 = room["y1"] + 1
        interior_y2 = room["y2"] - 1
        for ry in range(interior_y1, interior_y2):
            for rx in range(interior_x1, interior_x2):
                map_data[ry][rx] = 2
                room_tile_map[(rx, ry)] = len(rooms) - 1
        for xx in range(room["x1"], room["x2"]):
            map_data[room["y1"]][xx] = 1
            map_data[room["y2"] - 1][xx] = 1
        for yy in range(room["y1"] + 1, room["y2"] - 1):
            map_data[yy][room["x1"]] = 1
            map_data[yy][room["x2"] - 1] = 1

    def overlaps(r):
        for other in rooms:
            if not (r["x2"] <= other["x1"] or r["x1"] >= other["x2"] or
                    r["y2"] <= other["y1"] or r["y1"] >= other["y2"]):
                return True
        return False

    def place_room_along_corridor(cx, center_y, dir_side):
        outer_w = room_size + 2
        outer_h = room_size + 2
        near_wall_offset = (corridor_width // 2) + \
            max(1, passage_thickness) + 1
        near_wall_x = cx + dir_side * near_wall_offset
        if dir_side > 0:
            room_x1 = near_wall_x
        else:
            room_x1 = near_wall_x - outer_w + 1
        room_y1 = center_y - outer_h // 2
        room_x1 = max(1, min(map_width - outer_w - 1, room_x1))
        room_y1 = max(1, min(map_height - outer_h - 1, room_y1))
        room = {"x1": room_x1, "y1": room_y1,
                "x2": room_x1 + outer_w, "y2": room_y1 + outer_h}
        if overlaps(room):
            return

        rooms.append(room)
        door_y = min(max(room_y1 + outer_h // 2, 1), map_height - 2)
        door_x = cx
        target_x = room["x1"] if dir_side > 0 else room["x2"] - 1
        # Создаем проход 2x2 тайла
        passage_size = 2  # 2 блока
        for dy in range(passage_size):  # 2 тайла по вертикали
            y = door_y + dy
            # Создаем проход между коридором и комнатой - 2 тайла по горизонтали
            for dx in range(passage_size):
                x = target_x + (dx if dir_side > 0 else -dx)
                if 0 <= x < map_width and 0 <= y < map_height:
                    map_data[y][x] = 0
                    corridor_tiles.add((x, y))
            # Также проход в коридоре
            for x in range(min(door_x, target_x), max(door_x, target_x) + 1):
                if 0 <= x < map_width and 0 <= y < map_height:
                    map_data[y][x] = 0
                    corridor_tiles.add((x, y))
        interior_x1 = room["x1"] + 1
        interior_x2 = room["x2"] - 1
        interior_y1 = room["y1"] + 1
        interior_y2 = room["y2"] - 1
        for ry in range(interior_y1, interior_y2):
            for rx in range(interior_x1, interior_x2):
                map_data[ry][rx] = 2
                room_tile_map[(rx, ry)] = len(rooms) - 1
        for xx in range(room["x1"], room["x2"]):
            map_data[room["y1"]][xx] = 1
            map_data[room["y2"] - 1][xx] = 1
        for yy in range(room["y1"] + 1, room["y2"] - 1):
            map_data[yy][room["x1"]] = 1
            map_data[yy][room["x2"] - 1] = 1

        inner_x = target_x + (-1 if dir_side > 0 else 1)
        if 0 <= inner_x < map_width:
            map_data[door_y][target_x] = 0
            corridor_tiles.add((target_x, door_y))
            map_data[door_y][inner_x] = 2
            room_tile_map[(inner_x, door_y)] = len(rooms) - 1

    room_spacing = room_size + corridor_width + 6
    for cx in corridor_positions:
        side = -1
        for y in range(room_size + 2, map_height - room_size - 2, room_spacing):
            place_room_along_corridor(cx, y, side)
            side *= -1

    exit_pos = None
    exit_room_idx = None
    if rooms:
        if spawn_corner == "bottom_left":
            target_corner = (map_width - 1, 0)
        elif spawn_corner == "bottom_right":
            target_corner = (0, 0)
        else:
            target_corner = (0 if random.random() < 0.5 else map_width - 1, 0)

        corner_distances = []
        for i, room in enumerate(rooms):
            room_center_x = (room["x1"] + room["x2"]) // 2
            room_center_y = (room["y1"] + room["y2"]) // 2
            dx = room_center_x - target_corner[0]
            dy = room_center_y - target_corner[1]
            dist_sq = dx * dx + dy * dy
            corner_distances.append((dist_sq, i))

        corner_distances.sort(key=lambda t: t[0])
        exit_room_idx = corner_distances[0][1]
        original_room = rooms[exit_room_idx]

        # Увеличиваем комнату с выходом
        exit_room_size = int(room_size * exit_room_multiplier)
        exit_room_w = exit_room_size + 2
        exit_room_h = exit_room_size + 2

        # Пересоздаем комнату с выходом большего размера
        room_center_x = (original_room["x1"] + original_room["x2"]) // 2
        room_center_y = (original_room["y1"] + original_room["y2"]) // 2

        new_x1 = max(1, room_center_x - exit_room_w // 2)
        new_y1 = max(1, room_center_y - exit_room_h // 2)
        new_x1 = min(new_x1, map_width - exit_room_w - 1)
        new_y1 = min(new_y1, map_height - exit_room_h - 1)

        # Удаляем старую комнату
        for y in range(original_room["y1"], original_room["y2"]):
            for x in range(original_room["x1"], original_room["x2"]):
                if 0 <= x < map_width and 0 <= y < map_height:
                    if map_data[y][x] == 2:
                        room_tile_map.pop((x, y), None)
                    map_data[y][x] = 1

        # Создаем новую большую комнату
        room = {
            "x1": new_x1,
            "y1": new_y1,
            "x2": new_x1 + exit_room_w,
            "y2": new_y1 + exit_room_h
        }
        rooms[exit_room_idx] = room

        # Заполняем новую комнату
        interior_x1 = room["x1"] + 1
        interior_x2 = room["x2"] - 1
        interior_y1 = room["y1"] + 1
        interior_y2 = room["y2"] - 1
        for ry in range(interior_y1, interior_y2):
            for rx in range(interior_x1, interior_x2):
                map_data[ry][rx] = 2
                room_tile_map[(rx, ry)] = exit_room_idx
        # Стены комнаты
        for xx in range(room["x1"], room["x2"]):
            map_data[room["y1"]][xx] = 1
            map_data[room["y2"] - 1][xx] = 1
        for yy in range(room["y1"] + 1, room["y2"] - 1):
            map_data[yy][room["x1"]] = 1
            map_data[yy][room["x2"] - 1] = 1

        closest_corridor_x = min(corridor_positions, key=lambda x: abs(
            x - (room["x1"] + exit_room_size // 2)))
        door_x = room["x1"] if (room["x1"] + exit_room_size //
                                2) < closest_corridor_x else room["x2"] - 1

        # Сохраняем позицию прохода для возможного закрытия
        exit_door_positions = []

        if door_x == room["x1"]:
            back_wall_x = room["x2"] - 1
            opening_y = room["y1"] + (room["y2"] - room["y1"]) // 2
            # Проход 2x2 тайла
            passage_size = 2
            for dy in range(passage_size):
                for dx in range(passage_size):
                    x = back_wall_x - dx
                    y = opening_y + dy
                    if 0 <= x < map_width and 0 <= y < map_height:
                        map_data[y][x] = 0
                        corridor_tiles.add((x, y))
                        exit_door_positions.append((x, y))
            exit_pos = (back_wall_x, opening_y)
            ex, ey = exit_pos
            map_data[ey][ex] = 3
        else:
            back_wall_x = room["x1"]
            opening_y = room["y1"] + (room["y2"] - room["y1"]) // 2
            # Проход 2x2 тайла
            passage_size = 2
            for dy in range(passage_size):
                for dx in range(passage_size):
                    x = back_wall_x + dx
                    y = opening_y + dy
                    if 0 <= x < map_width and 0 <= y < map_height:
                        map_data[y][x] = 0
                        corridor_tiles.add((x, y))
                        exit_door_positions.append((x, y))
            exit_pos = (back_wall_x, opening_y)
            ex, ey = exit_pos
            map_data[ey][ex] = 3

    # Ensure there's an exit at the end of the exit room - place exit on the far side of the room from the entrance
    if rooms and exit_pos and exit_room_idx is not None:
        # Find the exit room
        exit_room = rooms[exit_room_idx]
        if isinstance(exit_room, dict):
            # Calculate the side of the room that's farthest from the corridor connection
            x1, y1, x2, y2 = exit_room["x1"], exit_room["y1"], exit_room["x2"], exit_room["y2"]

            # Determine which side of the room connects to the corridor
            closest_corridor_x = min(corridor_positions, key=lambda x: abs(
                x - ((x1 + x2) // 2)))

            # Determine where the entrance is (left or right side of room)
            # Based on the original logic, door_x is calculated as follows:
            door_x = x1 if ((x1 + x2) // 2) < closest_corridor_x else x2 - 1

            if abs(door_x - x1) < abs(door_x - x2):
                # Entrance is on the left side (x1), so exit should be on the right side (x2)
                exit_x = x2 - 1
                exit_y = y1 + (y2 - y1) // 2
            else:
                # Entrance is on the right side (x2), so exit should be on the left side (x1)
                exit_x = x1 + 1
                exit_y = y1 + (y2 - y1) // 2

            # Update the exit position to be at the far end of the room
            # Only if it's different from the current exit position
            if exit_pos != (exit_x, exit_y):
                # Clear the old exit position
                old_x, old_y = exit_pos
                if 0 <= old_x < map_width and 0 <= old_y < map_height:
                    # Restore the old exit position to a regular floor tile if it was an exit
                    if map_data[old_y][old_x] == 3:
                        map_data[old_y][old_x] = 2  # Floor tile

                # Set the new exit position
                if 0 <= exit_x < map_width and 0 <= exit_y < map_height:
                    map_data[exit_y][exit_x] = 3  # Set as exit tile
                    exit_pos = (exit_x, exit_y)

    # Post-process map to add variety and decorations
    for y in range(map_height):
        for x in range(map_width):
            if map_data[y][x] == 2:  # Room floor
                # Randomly change some floor tiles to variants
                r = random.random()
                if r < 0.1:
                    map_data[y][x] = 10  # Floor variant 1
                elif r < 0.2:
                    map_data[y][x] = 11  # Floor variant 2
                
                # Add decorations (non-walkable)
                # Only place if not near a door or in a narrow path
                # Ideally, check neighbors to ensure we don't block
                # Simple heuristic: don't place if adjacent to a corridor (0) or door
                # Also don't place if it would block the only path (hard to check cheaply)
                # Let's place them sparsely
                elif r > 0.95:
                    # Check neighbors
                    neighbors = [
                        map_data[y-1][x] if y > 0 else 1,
                        map_data[y+1][x] if y < map_height-1 else 1,
                        map_data[y][x-1] if x > 0 else 1,
                        map_data[y][x+1] if x < map_width-1 else 1
                    ]
                    # If any neighbor is a corridor (0) or door/exit (3), avoid
                    if 0 not in neighbors and 3 not in neighbors:
                         # Pick a decoration
                         dec_r = random.random()
                         if dec_r < 0.33:
                             map_data[y][x] = 20
                         elif dec_r < 0.66:
                             map_data[y][x] = 21
                         else:
                             map_data[y][x] = 22

    return map_data, rooms, room_tile_map, corridor_tiles, exit_pos, exit_room_idx, exit_door_positions
