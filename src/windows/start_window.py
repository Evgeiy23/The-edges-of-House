import arcade
import arcade.gui
import arcade.camera as arcade_camera
import os
import json
import pyglet
from project import ProjectSettings
from utils import get_config_path
from game.logic.music import find_music_file as shared_find_music
from windows.start_window_music import StartWindowMusic
from windows.start_window_background import StartWindowBackground
from windows.start_window_settings import StartWindowSettings


class StartWindow(arcade.View, StartWindowMusic, StartWindowBackground, StartWindowSettings):
    def __init__(self):
        super().__init__()

        self.screen_width = 0
        self.screen_height = 0
        self.transition_alpha = 0
        self.transitioning = False

        self.manager = arcade.gui.UIManager()
        self.manager.enable()

        self.start_game = False
        self.show_settings = False

        self.settings_sound = None
        self.settings_player = None
        self.main_music_sound = None
        self.main_music_player = None

        self.available_resolutions = self.get_available_resolutions()
        try:
            current_w, current_h = self.get_size()
            if (current_w, current_h) in self.available_resolutions:
                self.current_resolution_index = self.available_resolutions.index(
                    (current_w, current_h))
            else:
                self.current_resolution_index = 0
        except Exception:
            self.current_resolution_index = 0

        self.display_modes = ["Полноэкранный",
                              "Полноэкранный в окне", "В окне"]
        self.current_mode_index = 0 if ProjectSettings.FULLSCREEN else 2
        self.frame_limit_options = ProjectSettings.Game.FRAME_LIMIT_OPTIONS
        self.frame_limit_index = self.frame_limit_options.index(
            ProjectSettings.Game.DEFAULT_FRAME_LIMIT
        ) if ProjectSettings.Game.DEFAULT_FRAME_LIMIT in ProjectSettings.Game.FRAME_LIMIT_OPTIONS else 0

        self.music_volume = 1.0
        self.sound_volume = 1.0

        self.res_label = None
        self.mode_label = None

        self.music_volume_slider = None
        self.sound_volume_slider = None

        arcade.set_background_color(ProjectSettings.BACKGROUND_COLOR)

        self.title_x = 0
        self.title_y = 0

        self.background_list = None
        self.background_sprite = None
        self.camera = None
        self.button_fx = {}
        self.start_button = None
        
        self.settings_title_text_object = None
        self.title_text_object = None
        self.title_shadow_text_object = None
        self.button_text_objects = {}

        self.setup_ui()
        self.load_settings()
        self._ensure_background_sprite()
        self.play_main_music()

    def _initialize_background_list(self):
        """Initialize background sprite list safely with proper OpenGL context"""
        if self.background_list is None:
            self.background_list = arcade.SpriteList()

    def get_available_resolutions(self):
        try:
            display = pyglet.display.get_display()
            screen = display.get_default_screen()
            modes = screen.get_modes()

            resolutions = []
            seen = set()
            for mode in modes:
                res = (mode.width, mode.height)
                if res not in seen:
                    seen.add(res)
                    resolutions.append(res)

            resolutions.sort(key=lambda x: x[0] * x[1], reverse=True)

            if not resolutions:
                current_res = (screen.width, screen.height)
                resolutions = [current_res]

            return resolutions
        except Exception as e:
            print(f"Ошибка получения разрешений: {e}")
            return ProjectSettings.Settings.RESOLUTIONS

    def get_native_resolution(self):
        try:
            display = pyglet.display.get_display()
            screen = display.get_default_screen()
            return screen.width, screen.height
        except Exception:
            return 1920, 1080

    def find_music_file(self, preferred_filename=None, folder_path=None):
        return shared_find_music(preferred_filename, folder_path)

    def setup_ui(self):
        settings = ProjectSettings.StartWindow

        # Common button style for consistency and readability
        # Improved contrast and font size for better readability
        button_style = {
            "normal": {
                "font_size": 20,
                "font_name": ("Arial", "Roboto", "sans-serif"),
                "bg_color": arcade.color.DARK_SLATE_BLUE,
                "font_color": arcade.color.WHITE,
                "border_color": arcade.color.WHITE,
                "border_width": 3,
            },
            "hover": {
                "font_size": 20,
                "font_name": ("Arial", "Roboto", "sans-serif"),
                "bg_color": arcade.color.SLATE_BLUE,
                "font_color": arcade.color.WHITE,
                "border_color": arcade.color.WHITE,
                "border_width": 3,
            },
            "press": {
                "font_size": 20,
                "font_name": ("Arial", "Roboto", "sans-serif"),
                "bg_color": arcade.color.DARK_BLUE,
                "font_color": arcade.color.WHITE,
                "border_color": arcade.color.WHITE,
                "border_width": 3,
            }
        }

        v_box = arcade.gui.UIBoxLayout(
            vertical=True,
            space_between=settings.BUTTON_SPACING
        )

        start_button = arcade.gui.UIFlatButton(
            text=settings.BUTTON_START_TEXT,
            width=settings.BUTTON_WIDTH,
            height=settings.BUTTON_HEIGHT
        )
        start_button.style = button_style
        start_button.on_click = self.on_start_click
        self.start_button = start_button
        v_box.add(start_button)

        settings_button = arcade.gui.UIFlatButton(
            text=settings.BUTTON_SETTINGS_TEXT,
            width=settings.BUTTON_WIDTH,
            height=settings.BUTTON_HEIGHT
        )
        settings_button.style = button_style
        settings_button.on_click = self.on_settings_click
        v_box.add(settings_button)

        exit_button = arcade.gui.UIFlatButton(
            text=settings.BUTTON_EXIT_TEXT,
            width=settings.BUTTON_WIDTH,
            height=settings.BUTTON_HEIGHT
        )
        exit_button.style = button_style
        exit_button.on_click = self.on_exit_click
        v_box.add(exit_button)

        self.buttons = [start_button, settings_button, exit_button]
        self.button_texts = [
            settings.BUTTON_START_TEXT,
            settings.BUTTON_SETTINGS_TEXT,
            settings.BUTTON_EXIT_TEXT
        ]

        anchor_layout = arcade.gui.UIAnchorLayout()
        anchor_layout.add(
            child=v_box,
            anchor_x="center_x",
            anchor_y="center_y"
        )
        self.manager.add(anchor_layout)

        self.title_x = 0
        self.title_y = 0

    def on_start_click(self, event):
        self.button_fx[self.start_button] = 0.2
        self.transitioning = True
        self.transition_alpha = 0
        self.pause_main_music()

    pass

    def on_settings_click(self, event):
        self.show_settings = True
        self.manager.clear()
        self.setup_settings_ui()
        try:
            self.pause_main_music()
        except Exception:
            pass
        self.play_settings_music()

    def on_exit_click(self, event):
        arcade.exit()

    def on_draw(self):
        self.clear()

        try:
            if self.camera is None:
                self.camera = arcade_camera.Camera2D()
            cam_x = self.width // 2
            cam_y = self.height // 2
            self.camera.position = (cam_x, cam_y)
            self.camera.use()
        except Exception:
            pass

        self.update_background_scale()
        try:
            # Initialize background list if needed
            self._initialize_background_list()
            self.background_list.draw()
        except Exception:
            self._ensure_background_sprite()

        try:
            import pyglet
            pyglet.gl.glViewport(0, 0, self.width, self.height)
            pyglet.gl.glMatrixMode(pyglet.gl.GL_PROJECTION)
            pyglet.gl.glLoadIdentity()
            pyglet.gl.glOrtho(0, self.width, 0, self.height, -1, 1)
            pyglet.gl.glMatrixMode(pyglet.gl.GL_MODELVIEW)
            pyglet.gl.glLoadIdentity()
        except Exception:
            pass

        settings = ProjectSettings.StartWindow

        if self.show_settings:
            if self.window:
                self.screen_width = self.window.width
                self.screen_height = self.window.height

            panel_w, panel_h = self.settings_panel_dimensions()
            cx = self.width // 2
            cy = self.height // 2
            left = cx - panel_w // 2
            right = cx + panel_w // 2
            bottom = cy - panel_h // 2
            top = cy + panel_h // 2

            arcade.draw_lrbt_rectangle_filled(
                0, self.width, 0, self.height, (0, 0, 0, 180))
            arcade.draw_lrbt_rectangle_filled(
                left, right, bottom, top, (30, 30, 30, 240))
            arcade.draw_lrbt_rectangle_outline(
                left, right, bottom, top, arcade.color.WHITE, border_width=2)

            title = ProjectSettings.StartWindow.SETTINGS_TITLE_TEXT
            if not self.settings_title_text_object:
                self.settings_title_text_object = arcade.Text(
                    title, cx, top - 48,
                    arcade.color.WHITE, ProjectSettings.StartWindow.TITLE_FONT_SIZE // 2,
                    anchor_x="center", anchor_y="center", bold=True)
            else:
                self.settings_title_text_object.x = cx
                self.settings_title_text_object.y = top - 48
            self.settings_title_text_object.draw()

            try:
                self.manager.draw()
            except Exception:
                pass

        # Draw UI (buttons, labels)
        try:
            self.manager.draw()
        except Exception:
            pass

        if not self.show_settings:
            try:
                if self.buttons and hasattr(self.buttons[0], 'rect'):
                    bx = self.buttons[0].rect.center_x
                    by_top = self.buttons[0].rect.top
                    self.title_x = bx
                    self.title_y = by_top + settings.TITLE_BOTTOM_SPACING + settings.TITLE_FONT_SIZE
            except Exception:
                pass

            shadow_offset = 3
            if not self.title_shadow_text_object:
                self.title_shadow_text_object = arcade.Text(
                    settings.TITLE_TEXT,
                    self.title_x + shadow_offset,
                    self.title_y - shadow_offset,
                    settings.TITLE_SHADOW_COLOR,
                    settings.TITLE_FONT_SIZE,
                    width=settings.TITLE_WIDTH,
                    align="center",
                    bold=settings.TITLE_BOLD,
                    anchor_x="center",
                    anchor_y="center"
                )
            else:
                self.title_shadow_text_object.x = self.title_x + shadow_offset
                self.title_shadow_text_object.y = self.title_y - shadow_offset
            self.title_shadow_text_object.draw()

            if not self.title_text_object:
                self.title_text_object = arcade.Text(
                    settings.TITLE_TEXT,
                    self.title_x,
                    self.title_y,
                    settings.TITLE_COLOR,
                    settings.TITLE_FONT_SIZE,
                    width=settings.TITLE_WIDTH,
                    align="center",
                    bold=settings.TITLE_BOLD,
                    anchor_x="center",
                    anchor_y="center"
                )
            else:
                self.title_text_object.x = self.title_x
                self.title_text_object.y = self.title_y
            self.title_text_object.draw()

        for button, text in zip(self.buttons, self.button_texts):
            if hasattr(button, 'rect'):
                if getattr(button, 'text', '') == '':
                    button_x = button.rect.center_x
                    button_y = button.rect.center_y
                    if button not in self.button_text_objects or self.button_text_objects[button].text != text:
                        self.button_text_objects[button] = arcade.Text(
                            text,
                            button_x,
                            button_y,
                            arcade.color.WHITE,
                            settings.BUTTON_FONT_SIZE,
                            anchor_x="center",
                            anchor_y="center",
                            bold=True
                        )
                    else:
                        self.button_text_objects[button].x = button_x
                        self.button_text_objects[button].y = button_y
                    self.button_text_objects[button].draw()
                if not self.show_settings and button in self.button_fx:
                    alpha = int(
                        max(0, min(255, 255 * (self.button_fx[button] / 0.2))))
                    left = button.rect.left
                    right = button.rect.right
                    bottom = button.rect.bottom
                    top = button.rect.top
                    arcade.draw_lrbt_rectangle_outline(
                        left, right, bottom, top, (*arcade.color.WHITE[:3], alpha), border_width=3)

        if self.transitioning:
            alpha = int(self.transition_alpha)
            left, right = 0, self.width
            bottom, top = 0, self.height
            arcade.draw_lrbt_rectangle_filled(
                left, right, bottom, top, (0, 0, 0, alpha))

    def on_show_view(self):
        # Called when this view becomes active
        try:
            self.manager.enable()
        except Exception:
            pass

        arcade.set_background_color(ProjectSettings.BACKGROUND_COLOR)
        if self.window:
            if not self.window.fullscreen:
                try:
                    self.window.set_size(self.window.width, self.window.height)
                except Exception:
                    pass

            self.screen_width = self.window.width
            self.screen_height = self.window.height

            settings = ProjectSettings.StartWindow
            self.title_x = self.screen_width // 2
            self.title_y = self.screen_height // 2 + settings.TITLE_TOP_OFFSET + 150

            self._ensure_background_sprite()

            self.update_background_scale()

            try:
                if self.camera is None:
                    self.camera = arcade_camera.Camera2D()
                self.camera.position = (
                    self.screen_width // 2, self.screen_height // 2)
            except Exception:
                pass

            if hasattr(self, 'main_music_player') and self.main_music_player:
                try:
                    if hasattr(self.main_music_player, "volume"):
                        self.main_music_player.volume = self.music_volume
                except Exception:
                    pass

        # Ensure main menu music is playing when view is shown
        try:
            if not self.main_music_player:
                self.play_main_music()
            else:
                self.resume_main_music()
        except Exception:
            pass

        # Ensure volume is properly applied after view is shown
        if self.main_music_player and hasattr(self.main_music_player, "volume"):
            try:
                self.main_music_player.volume = self.music_volume
            except Exception:
                pass

    def _ensure_background_sprite(self):
        """Ensure background_sprite is loaded and present in background_list."""
        try:
            bg_path = getattr(ProjectSettings.StartWindow,
                              'BACKGROUND_IMAGE', None)
            if not bg_path:
                return
            # Initialize background list if needed
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
        if not self.window:
            return
        self.screen_width = self.window.width
        self.screen_height = self.window.height

        # Initialize background list if needed
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

    def on_resize(self, width, height):
        self.screen_width = width
        self.screen_height = height
        self.update_background_scale()
        settings = ProjectSettings.StartWindow
        self.title_x = self.screen_width // 2
        self.title_y = self.screen_height // 2 + settings.TITLE_TOP_OFFSET + 150
        try:
            if self.camera:
                self.camera.position = (
                    self.screen_width // 2, self.screen_height // 2)
        except Exception:
            pass

    def on_hide_view(self):
        try:
            self.manager.disable()
        except Exception:
            pass

    def on_update(self, delta_time):
        if self.window:
            current_width = self.window.width
            current_height = self.window.height
            if current_width != self.screen_width or current_height != self.screen_height:
                self.screen_width = current_width
                self.screen_height = current_height
                self.update_background_scale()
                settings = ProjectSettings.StartWindow
                self.title_x = self.screen_width // 2
                self.title_y = self.screen_height // 2 + settings.TITLE_TOP_OFFSET + 150

        if self.show_settings and self.music_volume_slider:
            try:
                v = (self.music_volume_slider.value or 0) / 100.0
                if abs(v - self.music_volume) > 0.001:
                    self.music_volume = v
                    if self.settings_player and hasattr(self.settings_player, "volume"):
                        try:
                            self.settings_player.volume = self.music_volume
                        except Exception:
                            pass
            except Exception:
                pass
        try:
            if self.main_music_player and hasattr(self.main_music_player, "volume") and not self.show_settings:
                self.main_music_player.volume = self.music_volume
        except Exception:
            pass

        # Always ensure the volume is applied regardless of settings state
        # This handles the case where volume is 0
        try:
            if self.main_music_player and hasattr(self.main_music_player, "volume"):
                self.main_music_player.volume = self.music_volume
        except Exception:
            pass

        expired = []
        for btn, t in list(self.button_fx.items()):
            t -= delta_time
            if t <= 0:
                expired.append(btn)
            else:
                self.button_fx[btn] = t
        for btn in expired:
            self.button_fx.pop(btn, None)

        if self.transitioning:
            self.transition_alpha = min(
                255, self.transition_alpha + delta_time * 400)
            if self.transition_alpha >= 255 and self.window:
                from windows.game_start_dialog import GameStartDialog
                dialog = GameStartDialog()
                self.window.show_view(dialog)

    def settings_panel_dimensions(self):
        s = ProjectSettings.StartWindow
        spacing = s.BUTTON_SPACING
        label_h = s.BUTTON_FONT_SIZE + 12
        row_h = s.BUTTON_HEIGHT

        slider_h = 24
        items_h = (
            label_h +
            label_h + row_h +
            label_h + row_h +
            label_h + row_h +

            label_h + slider_h +
            label_h + slider_h +
            row_h + row_h
        )
        total_spacers = 10
        total_h = items_h + spacing * total_spacers + 40
        min_h = max(int(self.screen_height * 0.6), total_h)
        panel_h = min(min_h, self.screen_height - 120)
        base_w = max(1000, int(self.screen_width * 0.7))
        panel_w = min(base_w, self.screen_width - 120)
        return panel_w, panel_h

    def setup_settings_ui(self):
        s = ProjectSettings.StartWindow
        v_box = arcade.gui.UIBoxLayout(
            vertical=True, space_between=s.BUTTON_SPACING)

        v_box.add(arcade.gui.UILabel(text=""))
        res_title = arcade.gui.UILabel(
            text="Разрешение", text_color=arcade.color.WHITE)
        v_box.add(res_title)

        res_row = arcade.gui.UIBoxLayout(vertical=False, space_between=20)
        res_left = arcade.gui.UIFlatButton(
            text="", width=60, height=s.BUTTON_HEIGHT)
        res_left.on_click = self.on_resolution_left
        res_right = arcade.gui.UIFlatButton(
            text="", width=60, height=s.BUTTON_HEIGHT)
        res_right.on_click = self.on_resolution_right
        self.res_label = arcade.gui.UILabel(
            text=self.resolution_text(), text_color=arcade.color.LIGHT_GRAY)
        res_row.add(res_left)
        res_row.add(self.res_label)
        res_row.add(res_right)
        v_box.add(res_row)

        mode_title = arcade.gui.UILabel(
            text="Режим экрана", text_color=arcade.color.WHITE)
        v_box.add(mode_title)

        mode_row = arcade.gui.UIBoxLayout(vertical=False, space_between=20)
        mode_left = arcade.gui.UIFlatButton(
            text="", width=60, height=s.BUTTON_HEIGHT)
        mode_left.on_click = self.on_mode_left
        mode_right = arcade.gui.UIFlatButton(
            text="", width=60, height=s.BUTTON_HEIGHT)
        mode_right.on_click = self.on_mode_right
        self.mode_label = arcade.gui.UILabel(
            text=self.mode_text(), text_color=arcade.color.LIGHT_GRAY)
        mode_row.add(mode_left)
        mode_row.add(self.mode_label)
        mode_row.add(mode_right)
        v_box.add(mode_row)

        fps_title = arcade.gui.UILabel(
            text="Ограничение FPS", text_color=arcade.color.WHITE)
        v_box.add(fps_title)

        fps_row = arcade.gui.UIBoxLayout(vertical=False, space_between=20)
        fps_left = arcade.gui.UIFlatButton(
            text="", width=60, height=s.BUTTON_HEIGHT)
        fps_left.on_click = self.on_fps_left
        fps_right = arcade.gui.UIFlatButton(
            text="", width=60, height=s.BUTTON_HEIGHT)
        fps_right.on_click = self.on_fps_right
        self.fps_label = arcade.gui.UILabel(
            text=self.fps_text(), text_color=arcade.color.LIGHT_GRAY)
        fps_row.add(fps_left)
        fps_row.add(self.fps_label)
        fps_row.add(fps_right)
        v_box.add(fps_row)

        music_title = arcade.gui.UILabel(
            text="Громкость музыки", text_color=arcade.color.WHITE)
        v_box.add(music_title)
        self.music_volume_slider = arcade.gui.UISlider(
            value=int(self.music_volume * 100), width=400)
        v_box.add(self.music_volume_slider)

        sound_title = arcade.gui.UILabel(
            text="Громкость звуков", text_color=arcade.color.WHITE)
        v_box.add(sound_title)
        self.sound_volume_slider = arcade.gui.UISlider(
            value=int(self.sound_volume * 100), width=400)
        v_box.add(self.sound_volume_slider)

        if self.res_label:
            self.res_label.text = self.resolution_text()
        if self.mode_label:
            self.mode_label.text = self.mode_text()
        if hasattr(self, "fps_label") and self.fps_label:
            self.fps_label.text = self.fps_text()

        apply_button = arcade.gui.UIFlatButton(
            text="", width=s.BUTTON_WIDTH, height=s.BUTTON_HEIGHT)
        apply_button.on_click = self.on_apply_settings_click
        v_box.add(apply_button)

        close_button = arcade.gui.UIFlatButton(
            text="", width=s.BUTTON_WIDTH, height=s.BUTTON_HEIGHT)
        close_button.on_click = self.on_close_settings_click
        v_box.add(close_button)

        self.buttons = [apply_button, close_button,
                        res_left, res_right, mode_left, mode_right,
                        fps_left, fps_right]
        self.button_texts = ["Сохранить",
                             s.SETTINGS_CLOSE_TEXT, "<", ">", "<", ">", "<", ">"]

        anchor_layout = arcade.gui.UIAnchorLayout()
        anchor_layout.add(child=v_box, anchor_x="center_x",
                          anchor_y="center_y")
        self.manager.add(anchor_layout)

    def on_close_settings_click(self, event):
        self.stop_settings_music()
        self.show_settings = False
        self.manager.clear()
        self.setup_ui()
        try:
            self.resume_main_music()
        except Exception:
            pass
        # Ensure the main music volume is applied after closing settings
        if self.main_music_player and hasattr(self.main_music_player, "volume"):
            try:
                self.main_music_player.volume = self.music_volume
            except Exception:
                pass

    def on_apply_settings_click(self, event):
        self.music_volume = (self.music_volume_slider.value or 0) / 100.0
        self.sound_volume = (self.sound_volume_slider.value or 0) / 100.0
        if self.settings_player and hasattr(self.settings_player, "volume"):
            try:
                self.settings_player.volume = self.music_volume
            except Exception:
                pass
        self.apply_display_settings()
        self.save_settings()

    def on_resolution_left(self, event):
        self.current_resolution_index = (
            self.current_resolution_index - 1) % len(self.available_resolutions)
        if self.res_label:
            self.res_label.text = self.resolution_text()

    def on_resolution_right(self, event):
        self.current_resolution_index = (
            self.current_resolution_index + 1) % len(self.available_resolutions)
        if self.res_label:
            self.res_label.text = self.resolution_text()

    def on_fps_left(self, event):
        self.frame_limit_index = (
            self.frame_limit_index - 1) % len(self.frame_limit_options)
        if hasattr(self, "fps_label") and self.fps_label:
            self.fps_label.text = self.fps_text()

    def on_fps_right(self, event):
        self.frame_limit_index = (
            self.frame_limit_index + 1) % len(self.frame_limit_options)
        if hasattr(self, "fps_label") and self.fps_label:
            self.fps_label.text = self.fps_text()

    def on_mode_left(self, event):
        self.current_mode_index = (
            self.current_mode_index - 1) % len(self.display_modes)
        if self.mode_label:
            self.mode_label.text = self.mode_text()
        if hasattr(self, "fps_label") and self.fps_label:
            self.fps_label.text = self.fps_text()

    def on_mode_right(self, event):
        self.current_mode_index = (
            self.current_mode_index + 1) % len(self.display_modes)
        if self.mode_label:
            self.mode_label.text = self.mode_text()

    def resolution_text(self):
        w, h = self.available_resolutions[self.current_resolution_index]
        return f"{w}×{h}"

    def mode_text(self):
        return self.display_modes[self.current_mode_index]

    def fps_text(self):
        try:
            return self.frame_limit_options[self.frame_limit_index]
        except Exception:
            return ProjectSettings.Game.DEFAULT_FRAME_LIMIT

    def apply_display_settings(self):
        if not self.window:
            return

        mode = self.display_modes[self.current_mode_index]
        w, h = self.available_resolutions[self.current_resolution_index]

        try:
            if mode == "Полноэкранный":
                self.window.set_fullscreen(True)
            elif mode == "Полноэкранный в окне":
                self.window.set_fullscreen(False)
                native_width, native_height = self.get_native_resolution()
                self.window.set_size(native_width, native_height)
                self.window.set_location(0, 0)
            else:
                self.window.set_fullscreen(False)
                self.window.set_size(w, h)
                display = pyglet.display.get_display()
                screen = display.get_default_screen()
                x = (screen.width - w) // 2
                y = (screen.height - h) // 2
                self.window.set_location(x, y)

            self.screen_width = self.window.width
            self.screen_height = self.window.height
            self.update_background_scale()

            settings = ProjectSettings.StartWindow
            self.title_x = self.screen_width // 2
            self.title_y = self.screen_height // 2 + settings.TITLE_TOP_OFFSET + 150

        except Exception as e:
            print(f"Ошибка установки режима экрана: {e}")

    def get_window_mode_string(self):
        mode = self.display_modes[self.current_mode_index]
        if mode == "Полноэкранный":
            return ProjectSettings.Settings.WINDOW_MODE_FULLSCREEN
        elif mode == "Полноэкранный в окне":
            return ProjectSettings.Settings.WINDOW_MODE_FULLSCREEN_WINDOWED
        else:
            return ProjectSettings.Settings.WINDOW_MODE_WINDOWED

    def load_settings(self):
        config_file = get_config_path()
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                    saved_index = config.get('resolution_index', None)
                    if saved_index is not None and 0 <= saved_index < len(self.available_resolutions):
                        self.current_resolution_index = saved_index

                    window_mode = config.get('window_mode', None)
                    if window_mode:
                        if window_mode == ProjectSettings.Settings.WINDOW_MODE_FULLSCREEN or window_mode == "fullscreen":
                            self.current_mode_index = 0
                        elif window_mode == ProjectSettings.Settings.WINDOW_MODE_FULLSCREEN_WINDOWED or window_mode == "fullscreen_windowed":
                            self.current_mode_index = 1
                        elif window_mode == ProjectSettings.Settings.WINDOW_MODE_WINDOWED or window_mode == "windowed":
                            self.current_mode_index = 2

                    music_vol = config.get('music_volume', None)
                    if music_vol is not None:
                        self.music_volume = float(music_vol)
                    sound_vol = config.get('sound_volume', None)
                    if sound_vol is not None:
                        self.sound_volume = float(sound_vol)
                    frame_limit = config.get('frame_limit')
                    if frame_limit and frame_limit in ProjectSettings.Game.FRAME_LIMIT_OPTIONS:
                        self.frame_limit_index = ProjectSettings.Game.FRAME_LIMIT_OPTIONS.index(
                            frame_limit)

            except Exception as e:
                print(f"Ошибка загрузки настроек: {e}")

    def save_settings(self):
        config = {
            'resolution_index': self.current_resolution_index,
            'window_mode': self.get_window_mode_string(),
            'music_volume': self.music_volume,
            'sound_volume': self.sound_volume,
            'frame_limit': self.frame_limit_options[self.frame_limit_index]
        }
        try:
            with open(get_config_path(), 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")

    def play_settings_music(self):
        path = self.find_music_file("НТР - Теорема Лагранжа (Mix&Master).mp3")
        if not path:
            return

        ext = os.path.splitext(path)[1].lower()
        try:
            if ext in ".mp3":
                media = pyglet.media.load(path, streaming=False)
                self.settings_player = media.play()
                self.settings_player.loop = True
                # Apply volume to settings music player
                if hasattr(self.settings_player, "volume"):
                    if self.music_volume <= 0:
                        self.settings_player.volume = 0
                    else:
                        self.settings_player.volume = self.music_volume
                return
        except Exception:
            pass

        try:
            self.settings_sound = arcade.Sound(path)
            # Explicitly handle volume = 0 case for settings music
            if self.music_volume <= 0:
                self.settings_player = self.settings_sound.play(
                    loop=True, volume=0)
            else:
                self.settings_player = self.settings_sound.play(
                    loop=True, volume=self.music_volume)
        except Exception:
            try:
                sound = arcade.load_sound(path)
                # Apply volume when playing sound
                if self.music_volume <= 0:
                    self.settings_player = arcade.play_sound(sound, volume=0)
                else:
                    self.settings_player = arcade.play_sound(
                        sound, volume=self.music_volume)
            except Exception:
                self.settings_sound = None
                self.settings_player = None

    def stop_settings_music(self):
        if self.settings_player:
            try:
                if hasattr(self.settings_player, "pause"):
                    try:
                        self.settings_player.loop = False
                    except Exception:
                        pass
                    self.settings_player.pause()
                    try:
                        self.settings_player.delete()
                    except Exception:
                        pass
                else:
                    self.settings_player.stop()
            except Exception:
                pass
            self.settings_player = None

    def play_main_music(self):
        # Prefer specific track, fallback to any available in folder
        path = self.find_music_file("scary_horror_theme.mp3")
        if not path:
            path = self.find_music_file()
        if not path:
            return
        ext = os.path.splitext(path)[1].lower()
        try:
            if ext in ".mp3":
                media = pyglet.media.load(path, streaming=False)
                self.main_music_player = media.play()
                self.main_music_player.loop = True
                try:
                    self.main_music_player.volume = self.music_volume
                except Exception:
                    pass
                return
        except Exception:
            pass
        try:
            self.main_music_sound = arcade.Sound(path)
            # Explicitly handle volume = 0 case
            if self.music_volume <= 0:
                self.main_music_player = self.main_music_sound.play(
                    loop=True, volume=0)
            else:
                self.main_music_player = self.main_music_sound.play(
                    loop=True, volume=self.music_volume)
        except Exception:
            try:
                self.main_music_sound = arcade.Sound(path)
                # Explicitly handle volume = 0 case
                if self.music_volume <= 0:
                    self.main_music_player = self.main_music_sound.play(
                        volume=0)
                else:
                    self.main_music_player = self.main_music_sound.play(
                        volume=self.music_volume)
                if hasattr(self.main_music_player, 'volume'):
                    self.main_music_player.volume = self.music_volume
            except Exception:
                self.main_music_sound = None
                self.main_music_player = None

    def pause_main_music(self):
        if self.main_music_player:
            try:
                if hasattr(self.main_music_player, "pause"):
                    self.main_music_player.pause()
                else:
                    self.main_music_player.stop()
            except Exception:
                pass

    def resume_main_music(self):
        if self.main_music_player:
            try:
                if hasattr(self.main_music_player, "play"):
                    self.main_music_player.play()
                    try:
                        self.main_music_player.loop = True
                    except Exception:
                        pass
                    try:
                        self.main_music_player.volume = self.music_volume
                    except Exception:
                        pass
            except Exception:
                pass
