
import arcade
import os
import glob
from .base import BaseVendor
from game.entities.follower import Follower

class MerchantNPC(BaseVendor, Follower):
    def __init__(self, tile_size, pos=(0, 0)):
        self.animations = {}
        BaseVendor.__init__(self, tile_size, pos)
        Follower.__init__(self)
        self.interaction_text = "Нажмите E чтобы торговать"
        self.items_for_sale = [] # Placeholder
        self.move_speed = 3.0
        self.current_frame_index = 0
        self.time_since_last_frame = 0
        self.frame_rate = 0.1
        self.state = 'idle' # idle, moving
        self.facing_right = True
        self.target_pos = None # (pixel_x, pixel_y)

    def _load_resources(self):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
        
        # Load Idle Animations
        idle_path = os.path.join(base_dir, "resources", "npcs", "Blacksmith", "PNG", "PNG Sequences", "Idle")
        self.animations['idle'] = self._load_animation_frames(idle_path)
        
        # Load Walking/Moving Animations (Using Greeting as placeholder if Walking doesn't exist, or just Idle)
        # Since no explicit walking animation, we reuse Idle
        self.animations['move'] = self.animations['idle']

        # Initial Sprite
        if self.animations['idle']:
            texture = self.animations['idle'][0]
            self.sprite = arcade.Sprite()
            self.sprite.texture = texture
            if texture.width:
                self.sprite.scale = (self.tile_size / texture.width) * 0.9
            self.sprite.center_x = self.draw_pos[0]
            self.sprite.center_y = self.draw_pos[1]
            self.sprite_list.append(self.sprite)
        else:
            self.sprite = arcade.SpriteSolidColor(self.tile_size, self.tile_size, arcade.color.GREEN)
            self.sprite.center_x = self.draw_pos[0]
            self.sprite.center_y = self.draw_pos[1]
            self.sprite_list.append(self.sprite)

        # Popup
        rel_popup_path = os.path.join("resources", "npcs", "Warlord", "popup", "PNG", "popup_1.png")
        abs_popup_path = os.path.join(base_dir, rel_popup_path)
        self.popup_texture = self._load_texture_from_path(abs_popup_path) or self._load_texture_from_path(rel_popup_path)

    def _load_animation_frames(self, folder_path):
        frames = []
        if os.path.exists(folder_path):
            files = sorted(glob.glob(os.path.join(folder_path, "*.png")))
            for f in files:
                tex = self._load_texture_from_path(f)
                if tex:
                    frames.append(tex)
        return frames

    def update(self, delta_time, dungeon_map=None, player=None):
        # Pursuit Logic
        if player and dungeon_map:
             dist_sq = (self.draw_pos[0] - player.draw_pos[0])**2 + (self.draw_pos[1] - player.draw_pos[1])**2
             pursuit_radius_sq = (10 * self.tile_size) ** 2 # 10 tiles radius
             stop_radius_sq = (2 * self.tile_size) ** 2

             if dist_sq < pursuit_radius_sq:
                 if dist_sq > stop_radius_sq:
                     # Update target to player's position
                     self.target_pos = player.draw_pos
                 else:
                     # Too close, stop
                     self.target_pos = None

        if self.target_pos and dungeon_map:
            dx, dy = self.move_along_path(delta_time, self.draw_pos, self.target_pos, self.move_speed * self.tile_size, self.tile_size, dungeon_map)
            
            if dx != 0 or dy != 0:
                self.draw_pos[0] += dx
                self.draw_pos[1] += dy
                self.state = 'move'
                if dx > 0:
                    self.facing_right = True
                elif dx < 0:
                    self.facing_right = False
            else:
                self.state = 'idle'
                
            # Update sprite position
            if self.sprite:
                self.sprite.center_x = self.draw_pos[0]
                self.sprite.center_y = self.draw_pos[1]
        
        # Update grid position for visibility checks
        self.pos = (int(self.draw_pos[0] / self.tile_size), int(self.draw_pos[1] / self.tile_size))
        
        self._update_animation(delta_time)

    def _update_animation(self, delta_time):
        if not self.sprite:
            return
            
        frames = self.animations.get(self.state, [])
        if not frames:
            return

        self.time_since_last_frame += delta_time
        if self.time_since_last_frame > self.frame_rate:
            self.time_since_last_frame = 0
            self.current_frame_index = (self.current_frame_index + 1) % len(frames)
            texture = frames[self.current_frame_index]
            
            # Flip texture if needed
            # Note: Arcade textures are shared, so we might need load_texture with flipped=True if we want unique flipped textures,
            # but usually we can just set scale negative or use flipped_horizontally property on sprite (if supported in this version).
            # Arcade 2.6+ supports sprite.texture_transform or we can just flip logic.
            # Assuming standard behavior:
            self.sprite.texture = texture

    def set_target(self, x, y):
        self.target_pos = (x, y)

    def get_display_text(self):
        return "Приветствую! У меня пока нет товаров."

    def interact(self):
        self.show_popup = not self.show_popup
