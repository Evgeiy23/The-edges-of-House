import csv
import json
import os
from typing import Dict, List, Optional, Set, Tuple

from utils import get_app_data_dir

try:
    from game.logic.map.generation import generate_dungeon
except Exception:
    generate_dungeon = None


MapPayload = Dict[str, object]


def get_maps_dir() -> str:
    base_dir = os.path.join(get_app_data_dir(), "maps")
    os.makedirs(base_dir, exist_ok=True)
    return base_dir


def get_map_paths(map_name: str = "current") -> Tuple[str, str]:
    maps_dir = get_maps_dir()
    csv_path = os.path.join(maps_dir, f"{map_name}.csv")
    meta_path = os.path.join(maps_dir, f"{map_name}.json")
    return csv_path, meta_path


def _write_csv(map_data: List[List[int]], csv_path: str) -> None:
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for row in map_data:
            writer.writerow([int(cell) for cell in row])


def _write_meta(payload: MapPayload, meta_path: str) -> None:
    meta = {
        "rooms": payload.get("rooms", []),
        "room_tile_map": {f"{k[0]},{k[1]}": v for k, v in (payload.get("room_tile_map") or {}).items()},
        "corridor_tiles": [list(t) for t in (payload.get("corridor_tiles") or [])],
        "exit_pos": list(payload.get("exit_pos")) if payload.get("exit_pos") else None,
        "exit_room_idx": payload.get("exit_room_idx"),
        "spawn_corner": payload.get("spawn_corner"),
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def save_map_payload(payload: MapPayload, map_name: str = "current") -> Tuple[str, str]:
    csv_path, meta_path = get_map_paths(map_name)
    map_data = payload.get("map_data") or []
    if not isinstance(map_data, list):
        raise ValueError("map_data must be a 2D list")
    _write_csv(map_data, csv_path)
    _write_meta(payload, meta_path)
    return csv_path, meta_path


def _parse_room_tile_map(raw: Dict[str, int]) -> Dict[Tuple[int, int], int]:
    parsed: Dict[Tuple[int, int], int] = {}
    for key, value in (raw or {}).items():
        try:
            x_str, y_str = key.split(",")
            parsed[(int(x_str), int(y_str))] = int(value)
        except Exception:
            continue
    return parsed


def _parse_corridor_tiles(raw) -> Set[Tuple[int, int]]:
    tiles: Set[Tuple[int, int]] = set()
    for item in raw or []:
        try:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                tiles.add((int(item[0]), int(item[1])))
        except Exception:
            continue
    return tiles


def rebuild_metadata(map_data: List[List[int]], exit_pos: Optional[Tuple[int, int]] = None,
                     spawn_corner: Optional[str] = None) -> MapPayload:
    height = len(map_data)
    width = len(map_data[0]) if height > 0 else 0

    corridor_tiles: Set[Tuple[int, int]] = set()
    room_tile_map: Dict[Tuple[int, int], int] = {}
    rooms: List[Dict[str, int]] = []
    visited: Set[Tuple[int, int]] = set()

    found_exit = exit_pos

    for y in range(height):
        for x in range(width):
            value = int(map_data[y][x])
            if value in (0, 3):
                corridor_tiles.add((x, y))
            if value == 3 and found_exit is None:
                found_exit = (x, y)

    def flood_room(start_x: int, start_y: int, room_id: int) -> None:
        stack = [(start_x, start_y)]
        tiles = []
        while stack:
            cx, cy = stack.pop()
            if (cx, cy) in visited:
                continue
            if not (0 <= cx < width and 0 <= cy < height):
                continue
            if int(map_data[cy][cx]) != 2:
                continue
            visited.add((cx, cy))
            tiles.append((cx, cy))
            stack.extend([
                (cx + 1, cy),
                (cx - 1, cy),
                (cx, cy + 1),
                (cx, cy - 1),
            ])

        if not tiles:
            return

        min_x = min(t[0] for t in tiles)
        max_x = max(t[0] for t in tiles)
        min_y = min(t[1] for t in tiles)
        max_y = max(t[1] for t in tiles)

        room = {
            "x1": max(0, min_x - 1),
            "y1": max(0, min_y - 1),
            "x2": min(width, max_x + 2),
            "y2": min(height, max_y + 2),
        }
        rooms.append(room)
        for tx, ty in tiles:
            room_tile_map[(tx, ty)] = room_id

    room_id = 0
    for y in range(height):
        for x in range(width):
            if (x, y) in visited:
                continue
            if int(map_data[y][x]) == 2:
                flood_room(x, y, room_id)
                room_id += 1

    exit_room_idx = None
    if found_exit is not None and rooms:
        ex, ey = found_exit
        for idx, room in enumerate(rooms):
            if room["x1"] <= ex < room["x2"] and room["y1"] <= ey < room["y2"]:
                exit_room_idx = idx
                break

    return {
        "map_data": map_data,
        "rooms": rooms,
        "room_tile_map": room_tile_map,
        "corridor_tiles": corridor_tiles,
        "exit_pos": found_exit,
        "exit_room_idx": exit_room_idx,
        "spawn_corner": spawn_corner,
    }


def load_map_payload(map_name: str = "current") -> Optional[MapPayload]:
    csv_path, meta_path = get_map_paths(map_name)
    if not os.path.exists(csv_path):
        return None

    with open(csv_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        map_data = [[int(cell) for cell in row] for row in reader]

    meta = {}
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            meta = {}

    payload: MapPayload = {"map_data": map_data}

    if meta:
        payload["rooms"] = meta.get("rooms", [])
        payload["room_tile_map"] = _parse_room_tile_map(
            meta.get("room_tile_map", {}))
        payload["corridor_tiles"] = _parse_corridor_tiles(
            meta.get("corridor_tiles", []))
        exit_pos = meta.get("exit_pos")
        payload["exit_pos"] = tuple(
            exit_pos) if isinstance(exit_pos, (list, tuple)) else None
        payload["exit_room_idx"] = meta.get("exit_room_idx")
        payload["spawn_corner"] = meta.get("spawn_corner")

    if not payload.get("rooms") or not payload.get("room_tile_map") or not payload.get("corridor_tiles"):
        rebuilt = rebuild_metadata(
            map_data, payload.get("exit_pos"), payload.get("spawn_corner"))
        payload.update(rebuilt)

    return payload


def generate_and_store_map(map_width: int, map_height: int, game_cfg,
                           spawn_corner: Optional[str] = None,
                           map_name: str = "current", seed=None) -> MapPayload:
    if generate_dungeon is None:
        raise RuntimeError("Map generator is not available")

    map_data, rooms, room_tile_map, corridor_tiles, exit_pos, exit_room_idx, exit_door_positions = generate_dungeon(
        map_width, map_height, game_cfg, spawn_corner, seed)

    payload: MapPayload = {
        "map_data": map_data,
        "rooms": rooms,
        "room_tile_map": room_tile_map,
        "corridor_tiles": set(corridor_tiles),
        "exit_pos": exit_pos,
        "exit_room_idx": exit_room_idx,
        "exit_door_positions": exit_door_positions,
        "spawn_corner": spawn_corner,
    }

    save_map_payload(payload, map_name=map_name)
    return payload
