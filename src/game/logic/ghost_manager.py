import random
import uuid
import math
from game.entities.ghost import Ghost

import arcade

class GhostManager:
    def __init__(self, tile_size):
        self.tile_size = tile_size
        self.ghosts = [] # List of Ghost entity objects
        self.sprite_list = arcade.SpriteList() # Optimization: Batch drawing
        self.ghost_records = [] # List of dictionaries as requested: {id, initial_pos, ...}
        self.logic_timer = 0.0
        self.logic_interval = 1.0 # 1 second interval
        self.active_ghosts = [] # Optimization: Only update these
        
    def spawn_ghosts(self, dungeon_map, count, level=1):
        """
        Spawns ghosts in corridors.
        """
        self.ghosts.clear()
        self.sprite_list = arcade.SpriteList()
        self.ghost_records.clear()
        self.active_ghosts.clear()

        if not hasattr(dungeon_map, 'corridor_tiles') or not dungeon_map.corridor_tiles:
            # Fallback if no corridor tiles found
            return
            
        # Convert set to list for random choice
        corridor_tiles = list(dungeon_map.corridor_tiles)
        
        for _ in range(count):
            if not corridor_tiles:
                break
                
            # Pick a random corridor tile
            idx = random.randint(0, len(corridor_tiles) - 1)
            gx, gy = corridor_tiles[idx]
            
            # Create Ghost Entity
            ghost = Ghost(self.tile_size, (gx, gy), level)
            ghost.id = str(uuid.uuid4())
            
            # Set Ghost Speed (Faster than player's 5.0 tiles/sec)
            # Player speed is 5.0 * tile_size. Ghost will be 6.0 * tile_size.
            ghost.move_speed_tiles = 6.0 
            ghost.move_speed_pixels = ghost.move_speed_tiles * self.tile_size
            
            self.ghosts.append(ghost)
            if ghost.sprite:
                self.sprite_list.append(ghost.sprite)
            
            # Create Record (Dictionary)
            record = {
                "id": ghost.id,
                "initial_pos": (gx, gy),
                "current_pos": (gx, gy), # Grid coordinates
                "target_pos": None,
                "state": "idle", # idle, chase
                "speed": ghost.move_speed_tiles
            }
            self.ghost_records.append(record)
            
    def update(self, delta_time, player, dungeon_map, viewport_rect=None):
        """
        Updates ghost logic and physics.
        viewport_rect: (left, right, bottom, top) in pixels for culling
        """
        # 1. Logic Update (Every 1 second)
        self.logic_timer += delta_time
        if self.logic_timer >= self.logic_interval:
            self.logic_timer = 0.0
            self._update_ai_logic(player)
            # Update active list occasionally
            self._update_active_list(viewport_rect)
            
        # 2. Physics/Animation Update (Every Frame)
        # Optimization: Only update ghosts that are likely visible or active
        targets = self.active_ghosts if self.active_ghosts else self.ghosts
        
        # Calculate camera center for LOD
        cx, cy = 0, 0
        if viewport_rect:
             cx = (viewport_rect[0] + viewport_rect[1]) / 2
             cy = (viewport_rect[2] + viewport_rect[3]) / 2
        elif player:
             cx, cy = player.draw_pos
        
        for ghost in targets:
            # Find corresponding record (Optimization: Cache this relationship if needed, but lookup is fast enough for <100 ghosts)
            record = next((r for r in self.ghost_records if r["id"] == ghost.id), None)
            
            if record:
                # Sync state from record to entity
                ghost.state = record["state"]
                
                # LOD calculation
                lod = 0
                if viewport_rect:
                    dist_sq = (ghost.draw_pos[0] - cx)**2 + (ghost.draw_pos[1] - cy)**2
                    if dist_sq > 1200*1200: # Far (1200 pixels)
                        lod = 2
                    elif dist_sq > 600*600: # Medium (600 pixels)
                        lod = 1
                
                # Update entity (movement, animation)
                ghost.update(delta_time, player, dungeon_map, lod_level=lod)
                
                # Sync position and state back to record
                record["current_pos"] = tuple(ghost.pos)
                record["state"] = ghost.state

    def _update_active_list(self, viewport_rect):
        """
        Updates the list of active ghosts based on viewport + buffer.
        """
        if not viewport_rect:
            self.active_ghosts = list(self.ghosts)
            return

        left, right, bottom, top = viewport_rect
        buffer = 500 # Extra pixels buffer
        
        self.active_ghosts = []
        for ghost in self.ghosts:
            # Check if ghost is within reasonable distance or chasing
            # Always update chasing ghosts regardless of visibility
            if ghost.state == 'chase' or ghost.state == 'attack':
                self.active_ghosts.append(ghost)
                continue
                
            gx, gy = ghost.draw_pos
            if (left - buffer < gx < right + buffer) and (bottom - buffer < gy < top + buffer):
                self.active_ghosts.append(ghost)

    def _update_ai_logic(self, player):
        """
        Performs the periodic AI checks: distance, state transitions.
        """
        if not player:
            return
            
        player_pos = player.pos # Grid coordinates
        
        for record in self.ghost_records:
            ghost_pos = record["current_pos"]
            
            # Calculate distance (Manhattan or Euclidean? "Radius" implies Euclidean)
            dist = math.sqrt((ghost_pos[0] - player_pos[0])**2 + (ghost_pos[1] - player_pos[1])**2)
            
            # Logic:
            # If dist in [4, 7]: Activate Chase
            # If dist < 4: Still Chase (implied, as it must attack at 1)
            # If dist > 10: Stop Chase (Hysteresis)
            
            if 4.0 <= dist <= 7.0:
                record["state"] = "chase"
            elif dist < 4.0:
                 # If already close, ensure we are chasing/attacking
                 if record["state"] == "idle":
                     record["state"] = "chase"
            elif dist > 10.0:
                record["state"] = "idle"
                
    def draw(self):
        # This method might be unused if GameWindowRendering handles drawing manually for Fog of War.
        # But if used, use batch drawing.
        if self.sprite_list:
            self.sprite_list.draw()

    def remove_ghost(self, ghost):
        if ghost in self.ghosts:
            self.ghosts.remove(ghost)
        if ghost in self.active_ghosts:
            self.active_ghosts.remove(ghost)
        if ghost.sprite and ghost.sprite in self.sprite_list:
            self.sprite_list.remove(ghost.sprite)
        # Remove record
        self.ghost_records = [r for r in self.ghost_records if r["id"] != ghost.id]

    def get_ghosts(self):
        return self.ghosts
