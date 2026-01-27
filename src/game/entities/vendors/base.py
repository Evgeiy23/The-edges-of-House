
import arcade
import math
import os
from PIL import Image

class BaseVendor:
    def __init__(self, tile_size, pos=(0, 0)):
        self.tile_size = tile_size
        self.pos = list(pos)
        self.draw_pos = [pos[0] * tile_size + tile_size // 2,
                         pos[1] * tile_size + tile_size // 2]
        
        self.sprite = None
        self.sprite_list = arcade.SpriteList()
        self.popup_texture = None
        self.alpha = 255
        self.show_popup = False
        
        self.interaction_text = "Нажмите E чтобы поговорить"
        self.interaction_text_object = None
        
        # UI optimization
        self.text_object = None
        self.last_text_content = ""
        
        # To be implemented by subclasses
        self._load_resources()

    def _load_resources(self):
        """Load sprites and textures. Override in subclass."""
        pass

    def _load_texture_from_path(self, path):
        """Helper to load texture safely"""
        if not os.path.exists(path) or not os.access(path, os.R_OK):
            # print(f"[{self.__class__.__name__}] Texture not found/readable: {path}")
            return None
        
        try:
            return arcade.load_texture(path)
        except Exception:
            try:
                img = Image.open(path).convert("RGBA")
                return arcade.Texture(os.path.basename(path), img)
            except Exception as e:
                # print(f"[{self.__class__.__name__}] Failed to load texture {path}: {e}")
                return None

    def update(self, delta_time):
        pass

    def draw(self):
        if self.sprite_list:
            self.sprite_list.draw()

    def draw_ui(self, player_pos, camera_pos=(0,0)):
        # Distance check
        dx = self.draw_pos[0] - player_pos[0]
        dy = self.draw_pos[1] - player_pos[1]
        dist = math.sqrt(dx*dx + dy*dy)
        
        interaction_dist = self.tile_size * 2
        
        if dist < interaction_dist:
            if not self.show_popup:
                if not self.interaction_text_object:
                    self.interaction_text_object = arcade.Text(
                        self.interaction_text,
                        self.draw_pos[0],
                        self.draw_pos[1] + self.tile_size,
                        arcade.color.WHITE,
                        14,
                        anchor_x="center",
                        anchor_y="bottom"
                    )
                self.interaction_text_object.draw()
        else:
            self.show_popup = False 

        if self.show_popup and self.popup_texture:
            self._draw_popup()

    def _draw_popup(self):
        popup_width = 400
        popup_height = 200
        popup_x = self.draw_pos[0]
        popup_y = self.draw_pos[1] + self.tile_size * 2.5
        
        sp = arcade.Sprite()
        sp.texture = self.popup_texture
        sp.center_x = popup_x
        sp.center_y = popup_y
        sp.width = popup_width
        sp.height = popup_height
        
        sp_list = arcade.SpriteList()
        sp_list.append(sp)
        sp_list.draw()
        
        text_content = self.get_display_text()
        
        if text_content != self.last_text_content or not self.text_object:
            self.last_text_content = text_content
            self.text_object = arcade.Text(
                text_content,
                popup_x - popup_width * 0.4,
                popup_y + popup_height * 0.3,
                arcade.color.BLACK,
                12,
                width=int(popup_width * 0.8),
                multiline=True,
                anchor_x="left",
                anchor_y="top"
            )
        
        if self.text_object:
            self.text_object.draw()

    def get_display_text(self):
        return ""

    def interact(self):
        self.show_popup = not self.show_popup
