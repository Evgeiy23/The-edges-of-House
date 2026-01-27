import arcade
import os
from .base import BaseVendor
from game.entities.follower import Follower

class MageNPC(BaseVendor, Follower):
    def __init__(self, tile_size, pos=(0, 0)):
        BaseVendor.__init__(self, tile_size, pos)
        Follower.__init__(self)
        self.interaction_text = "Нажмите E чтобы поговорить"
        
        # Animation state
        self.spawn_anim_active = False
        self.spawn_anim_t = 0.0
        self.spawn_anim_duration = 0.5
        self.start_draw_pos = list(self.draw_pos)
        self.target_draw_pos = list(self.draw_pos)

    def _load_resources(self):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
        
        # Use Sage sprite but we will tint it in draw or update
        # Using a different idle frame to distinguish
        rel_path = os.path.join("resources", "npcs", "Sage", "PNG", "PNG Sequences", "Idle", "0_Sage_Idle_000.png")
        abs_path = os.path.join(base_dir, rel_path)
        
        texture = self._load_texture_from_path(abs_path)
        if not texture:
            # Fallback
            texture = self._load_texture_from_path(rel_path)

        if texture:
            self.sprite = arcade.Sprite()
            self.sprite.texture = texture
            if texture.width:
                self.sprite.scale = (self.tile_size / texture.width) * 0.9
            self.sprite.center_x = self.draw_pos[0]
            self.sprite.center_y = self.draw_pos[1]
            
            # Make it purple/blue to look like a Mage
            self.sprite.color = (150, 100, 255)
            self.sprite_list.append(self.sprite)
        else:
            self.sprite = arcade.SpriteSolidColor(self.tile_size, self.tile_size, arcade.color.PURPLE)
            self.sprite.center_x = self.draw_pos[0]
            self.sprite.center_y = self.draw_pos[1]
            self.sprite_list.append(self.sprite)

        # Popup texture for interaction hint
        rel_popup_path = os.path.join("resources", "npcs", "Warlord", "popup", "PNG", "popup_1.png")
        abs_popup_path = os.path.join(base_dir, rel_popup_path)
        self.popup_texture = self._load_texture_from_path(abs_popup_path) or self._load_texture_from_path(rel_popup_path)

    def update(self, delta_time, player_pos=None, dungeon_map=None):
        """Update mage state, including animations and movement."""
        # 1. Spawn animation
        if self.spawn_anim_active:
            self.spawn_anim_t += delta_time
            t = max(0.0, min(1.0, self.spawn_anim_t / max(0.0001, self.spawn_anim_duration)))
            
            # Simple fade-in and slide
            if self.sprite:
                self.sprite.alpha = int(255 * t)
                
            if t >= 1.0:
                self.spawn_anim_active = False
        
        # 2. Idle pulsing animation (for visual uniqueness)
        if self.sprite:
            # Pulse alpha or color slightly
            import math
            # time based pulse
            time_val = getattr(self, "_anim_timer", 0.0) + delta_time
            self._anim_timer = time_val
            
            # Pulse scale slightly
            base_scale = getattr(self, "_base_scale", self.sprite.scale)
            
            # Ensure base_scale is a float (Arcade 3.0+ might return [x, y])
            if isinstance(base_scale, (list, tuple)):
                base_scale = base_scale[0]
            
            if not hasattr(self, "_base_scale"):
                self._base_scale = base_scale
            
            scale_pulse = 1.0 + 0.05 * math.sin(time_val * 3.0)
            self.sprite.scale = base_scale * scale_pulse

        # 3. Follow logic
        if player_pos and dungeon_map and not self.spawn_anim_active:
            dx = self.draw_pos[0] - player_pos[0]
            dy = self.draw_pos[1] - player_pos[1]
            dist_sq = dx*dx + dy*dy
            min_dist_sq = (self.tile_size * 3) ** 2
            
            # If outside min distance, follow
            if dist_sq > min_dist_sq:
                move_speed = 60.0 # Pixels per second
                move_dx, move_dy = self.move_along_path(
                    delta_time,
                    self.draw_pos,
                    player_pos,
                    move_speed,
                    self.tile_size,
                    dungeon_map
                )
                
                if move_dx != 0 or move_dy != 0:
                    self.draw_pos[0] += move_dx
                    self.draw_pos[1] += move_dy
                    
                    # Update sprite position
                    if self.sprite:
                        self.sprite.center_x = self.draw_pos[0]
                        self.sprite.center_y = self.draw_pos[1]
                    
                    # Update grid position
                    self.pos = [int(self.draw_pos[0] / self.tile_size), 
                                int(self.draw_pos[1] / self.tile_size)]

    def draw_ui(self, player_pos, camera_pos=(0, 0)):
        """
        Draw UI elements for the Mage.
        Adds a visual highlight (circle) when player is close to indicate interaction.
        """
        super().draw_ui(player_pos, camera_pos)
        
        # Check distance for interaction indicator
        dx = self.draw_pos[0] - player_pos[0]
        dy = self.draw_pos[1] - player_pos[1]
        dist_sq = dx*dx + dy*dy
        interaction_dist_sq = (self.tile_size * 3) ** 2  # Slightly larger than interaction range
        
        if dist_sq < interaction_dist_sq:
            # Draw a glowing circle under/around the mage
            arcade.draw_circle_outline(
                self.draw_pos[0],
                self.draw_pos[1],
                self.tile_size * 0.8,
                (150, 100, 255, 150), # Purple with transparency
                3
            )

    def interact(self):
        """
        Interaction API for Mage NPC.
        
        Returns:
            bool: True if interaction was successful/handled.
            
        Description:
            This method is called when the player presses the interaction key (E)
            while in range of the Mage.
            
            Current implementation:
            - Signals the GameWindow to open the MageDialog.
            - Does not maintain internal dialog state; delegates to the UI manager.
            
        Future API plans:
            - Could accept an 'action' parameter to specify type of interaction (shop, quest, talk).
            - Could return a data structure describing the available dialogue options.
        """
        # We don't use the default popup logic here because we want a full dialog window.
        # This method will be called by GameWindow, but GameWindow also handles the UI.
        # So we can just return True to signal successful interaction request.
        return True
