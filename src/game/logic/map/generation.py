import random
import math


def generate_dungeon(map_width, map_height, cfg, spawn_corner=None):
    room_size = max(6, random.randint(cfg.MIN_ROOM_SIZE, cfg.MAX_ROOM_SIZE))
    corridor_width = max(3, getattr(cfg, 'CORRIDOR_WIDTH', 5))
    passage_thickness = max(2, getattr(cfg, 'PASSAGE_THICKNESS', 2))
    spacing_y = room_size + corridor_width + random.randint(2, 5)
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
            local_w = max(3, corridor_width)
            for w in range(-(local_w // 2), local_w // 2 + 1):
                x = cx + w
                if 0 <= x < map_width:
                    map_data[y][x] = 0
                    corridor_tiles.add((x, y))

    mid_y = map_height // 2
    local_w = max(3, corridor_width)
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

        door_thickness = max(2, passage_thickness)
        for dy in range(-(door_thickness // 2), door_thickness // 2 + 1):
            for dx in range(-(passage_thickness // 2), passage_thickness // 2 + 1):
                px = door_x + dx
                py = door_y + dy
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
        door_thickness = max(2, passage_thickness)
        for dy in range(-(door_thickness // 2), door_thickness // 2 + 1):
            y = door_y + dy
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
        room = rooms[exit_room_idx]

        closest_corridor_x = min(corridor_positions, key=lambda x: abs(
            x - (room["x1"] + room_size // 2)))
        door_x = room["x1"] if (room["x1"] + room_size //
                                2) < closest_corridor_x else room["x2"] - 1

        if door_x == room["x1"]:
            back_wall_x = room["x2"] - 1
            opening_y = room["y1"] + (room["y2"] - room["y1"]) // 2
            map_data[opening_y][back_wall_x] = 0
            map_data[opening_y + 1][back_wall_x] = 0
            corridor_tiles.add((back_wall_x, opening_y))
            corridor_tiles.add((back_wall_x, opening_y + 1))
            exit_pos = (back_wall_x, opening_y)
            ex, ey = exit_pos
            map_data[ey][ex] = 3
        else:
            back_wall_x = room["x1"]
            opening_y = room["y1"] + (room["y2"] - room["y1"]) // 2
            map_data[opening_y][back_wall_x] = 0
            map_data[opening_y + 1][back_wall_x] = 0
            corridor_tiles.add((back_wall_x, opening_y))
            corridor_tiles.add((back_wall_x, opening_y + 1))
            exit_pos = (back_wall_x, opening_y)
            ex, ey = exit_pos
            map_data[ey][ex] = 3

    return map_data, rooms, room_tile_map, corridor_tiles, exit_pos, exit_room_idx
