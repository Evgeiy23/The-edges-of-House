import random


def generate_dungeon(map_width, map_height, cfg):
    room_size = max(6, cfg.MIN_ROOM_SIZE, min(cfg.MAX_ROOM_SIZE, 10))
    corridor_width = 5
    spacing_y = room_size + corridor_width + 3
    center_x = map_width // 2

    offset = room_size + corridor_width + 4
    candidate_offsets = [0, offset, -offset]
    corridor_positions = []
    for off in candidate_offsets:
        cx = center_x + off
        if 2 < cx < map_width - 3:
            corridor_positions.append(cx)
    corridor_positions = sorted(set(corridor_positions))
    if len(corridor_positions) < 2:
        corridor_positions = [center_x, max(3, center_x + offset)]

    map_data = [[1 for _ in range(map_width)] for _ in range(map_height)]
    rooms = []
    room_tile_map = {}
    corridor_tiles = set()

    for cx in corridor_positions:
        for y in range(1, map_height - 1):
            for w in range(-(corridor_width // 2), corridor_width // 2 + 1):
                x = cx + w
                if 0 <= x < map_width:
                    map_data[y][x] = 0
                    corridor_tiles.add((x, y))

    target_rooms = max(20, cfg.NUM_ROOMS)

    def overlaps(r):
        # Оптимизация: ранний выход при обнаружении перекрытия
        for other in rooms:
            if not (r["x2"] <= other["x1"] or r["x1"] >= other["x2"] or
                    r["y2"] <= other["y1"] or r["y1"] >= other["y2"]):
                return True
        return False

    # Оптимизация: ограничиваем количество попыток для предотвращения зависания
    max_attempts = target_rooms * 3
    attempts = 0

    for cx_idx, cx in enumerate(corridor_positions):
        if len(rooms) >= target_rooms:
            break
        y_range = list(
            range(room_size + 2, map_height - room_size - 2, spacing_y))
        for y in y_range:
            if len(rooms) >= target_rooms or attempts >= max_attempts:
                break
            attempts += 1
            dir_here = -1 if ((y // spacing_y + cx_idx) % 2 == 0) else 1
            branch_len = room_size + corridor_width + 3
            room_x1 = cx + dir_here * branch_len
            room_y1 = y
            room_x1 = max(1, min(map_width - room_size - 2, room_x1))
            room_y1 = max(1, min(map_height - room_size - 2, room_y1))
            room = {
                "x1": room_x1,
                "y1": room_y1,
                "x2": room_x1 + room_size + 2,
                "y2": room_y1 + room_size + 2,
            }
            margin = corridor_width // 2 + 1
            if dir_here < 0 and room["x2"] >= cx - margin:
                continue
            if dir_here > 0 and room["x1"] <= cx + margin:
                continue
            if overlaps(room):
                continue
            rooms.append(room)

            door_x = room["x1"] if dir_here < 0 else room["x2"] - 1
            door_y = (room["y1"] + room["y2"]) // 2
            for x in range(min(cx, door_x), max(cx, door_x) + 1):
                if 0 <= x < map_width and 0 <= door_y < map_height:
                    map_data[door_y][x] = 0
                    corridor_tiles.add((x, door_y))

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
            for yy in range(room["y1"], room["y2"]):
                map_data[yy][room["x1"]] = 1
                map_data[yy][room["x2"] - 1] = 1

            if 0 <= door_y < map_height:
                inner_x = door_x + 1 if dir_here < 0 else door_x - 1
                map_data[door_y][door_x] = 0
                corridor_tiles.add((door_x, door_y))
                if 0 <= inner_x < map_width:
                    map_data[door_y][inner_x] = 2
                    room_tile_map[(inner_x, door_y)] = len(rooms) - 1
                for x in range(room["x1"], room["x2"]):
                    map_data[door_y][x] = 0
                    corridor_tiles.add((x, door_y))

    exit_pos = None
    exit_room_idx = None
    if rooms:
        exit_room_idx = max(
            range(len(rooms)),
            key=lambda i: (rooms[i]["y2"], abs(rooms[i]["x1"] - center_x))
        )
        room = rooms[exit_room_idx]
        ex = random.randint(room["x1"] + 1, room["x2"] - 2)
        ey = random.randint(room["y1"] + 1, room["y2"] - 2)
        map_data[ey][ex] = 3
        exit_pos = (ex, ey)

    return map_data, rooms, room_tile_map, corridor_tiles, exit_pos, exit_room_idx
