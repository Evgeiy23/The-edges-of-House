"""
Модуль для управления фоном в стартовом окне
"""
import arcade
from project import ProjectSettings


class StartWindowBackground:
    """Класс-миксин для методов управления фоном StartWindow"""
    
    def _initialize_background_list(self):
        """Инициализация списка фоновых спрайтов"""
        if self.background_list is None:
            self.background_list = arcade.SpriteList()

    def _ensure_background_sprite(self):
        """Обеспечивает загрузку фонового спрайта"""
        try:
            bg_path = getattr(ProjectSettings.StartWindow,
                              'BACKGROUND_IMAGE', None)
            if not bg_path:
                return
            self._initialize_background_list()

            if self.background_sprite:
                try:
                    if getattr(self.background_sprite, 'texture', None):
                        if self.background_sprite not in self.background_list:
                            self.background_list.append(self.background_sprite)
                        return
                except Exception:
                    pass

            try:
                sprite = arcade.Sprite(bg_path)
                if getattr(sprite, 'texture', None):
                    self.background_sprite = sprite
                    if self.background_sprite not in self.background_list:
                        self.background_list.append(self.background_sprite)
                    return
                else:
                    try:
                        del sprite
                    except Exception:
                        pass
            except Exception:
                try:
                    texture = arcade.load_texture(bg_path)
                    if texture:
                        sprite = arcade.Sprite()
                        sprite.texture = texture
                        self.background_sprite = sprite
                        if self.background_sprite not in self.background_list:
                            self.background_list.append(self.background_sprite)
                except Exception:
                    self.background_sprite = None
        except Exception:
            self.background_sprite = None

    def update_background_scale(self):
        """Обновление масштаба фона"""
        if not self.window:
            return
        self.screen_width = self.window.width
        self.screen_height = self.window.height

        self._initialize_background_list()

        if self.background_sprite is None:
            self._ensure_background_sprite()

        if self.background_sprite and getattr(self.background_sprite, 'texture', None):
            try:
                self.background_sprite.center_x = self.screen_width // 2
                self.background_sprite.center_y = self.screen_height // 2

                original_width = self.background_sprite.texture.width
                original_height = self.background_sprite.texture.height

                if original_width <= 0 or original_height <= 0:
                    return

                scale_x = self.screen_width / original_width
                scale_y = self.screen_height / original_height
                self.background_sprite.scale = max(scale_x, scale_y)
            except Exception:
                self._ensure_background_sprite()
