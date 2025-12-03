import arcade
import arcade.gui
import os
import pyglet
from project import ProjectSettings


class StartWindow(arcade.Window):
    def __init__(self):
        super().__init__(
            fullscreen=ProjectSettings.FULLSCREEN,
            title=ProjectSettings.WINDOW_TITLE
        )

        self.screen_width = self.width
        self.screen_height = self.height

        self.manager = arcade.gui.UIManager()
        self.manager.enable()

        self.start_game = False
        self.show_settings = False

        self.settings_sound = None
        self.settings_player = None
        self.main_music_sound = None
        self.main_music_player = None

        self.available_resolutions = [
            (800, 600), (1024, 768), (1280, 720), (1600, 900), (1920, 1080)
        ]
        try:
            current_w, current_h = self.get_size()
            if (current_w, current_h) in self.available_resolutions:
                self.current_resolution_index = self.available_resolutions.index((current_w, current_h))
            else:
                self.current_resolution_index = 1
        except Exception:
            self.current_resolution_index = 1

        self.display_modes = ["Полноэкранный", "Полноэкранный в окне", "В окне"]
        self.current_mode_index = 0 if ProjectSettings.FULLSCREEN else 2

        
        self.music_volume = 1.0
        self.sound_volume = 1.0

        self.res_label = None
        self.mode_label = None
        
        self.music_volume_slider = None
        self.sound_volume_slider = None

        arcade.set_background_color(ProjectSettings.BACKGROUND_COLOR)

        self.title_x = 0
        self.title_y = 0

        self.background_list = arcade.SpriteList()
        try:
            background_sprite = arcade.Sprite(
                ProjectSettings.StartWindow.BACKGROUND_IMAGE)
            background_sprite.center_x = self.screen_width // 2
            background_sprite.center_y = self.screen_height // 2
            scale_x = self.screen_width / background_sprite.width
            scale_y = self.screen_height / background_sprite.height
            background_sprite.scale = max(scale_x, scale_y)
            self.background_list.append(background_sprite)
        except:
            pass

        self.setup_ui()
        self.play_main_music()

    def setup_ui(self):
        settings = ProjectSettings.StartWindow

        v_box = arcade.gui.UIBoxLayout(
            vertical=True,
            space_between=settings.BUTTON_SPACING
        )

        start_button = arcade.gui.UIFlatButton(
            text="",
            width=settings.BUTTON_WIDTH,
            height=settings.BUTTON_HEIGHT
        )
        start_button.on_click = self.on_start_click
        v_box.add(start_button)

        settings_button = arcade.gui.UIFlatButton(
            text="",
            width=settings.BUTTON_WIDTH,
            height=settings.BUTTON_HEIGHT
        )
        settings_button.on_click = self.on_settings_click
        v_box.add(settings_button)

        exit_button = arcade.gui.UIFlatButton(
            text="",
            width=settings.BUTTON_WIDTH,
            height=settings.BUTTON_HEIGHT
        )
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

        self.title_x = self.screen_width // 2
        self.title_y = self.screen_height // 2 + \
            settings.TITLE_TOP_OFFSET + 150

    def on_start_click(self, event):
        self.start_game = True

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

        self.background_list.draw()

        settings = ProjectSettings.StartWindow

        shadow_offset = 3
        arcade.draw_text(
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

        arcade.draw_text(
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

        if self.show_settings:
            panel_w, panel_h = self.settings_panel_dimensions()
            center_x = self.width // 2
            center_y = self.height // 2

            left, right = 0, self.width
            bottom, top = 0, self.height
            arcade.draw_lrbt_rectangle_filled(left, right, bottom, top, (0, 0, 0, 160))

            left = center_x - panel_w // 2
            right = center_x + panel_w // 2
            bottom = center_y - panel_h // 2
            top = center_y + panel_h // 2
            arcade.draw_lrbt_rectangle_filled(left, right, bottom, top, (30, 30, 30, 240))
            arcade.draw_lrbt_rectangle_outline(left, right, bottom, top, arcade.color.WHITE, border_width=2)

            title = ProjectSettings.StartWindow.SETTINGS_TITLE_TEXT
            arcade.draw_text(
                title,
                center_x,
                center_y + panel_h // 2 - 50,
                arcade.color.WHITE,
                ProjectSettings.StartWindow.TITLE_FONT_SIZE // 2,
                anchor_x="center",
                anchor_y="center",
                bold=True
            )

            pass

        self.manager.draw()

        for button, text in zip(self.buttons, self.button_texts):
            if hasattr(button, 'rect'):
                button_x = button.rect.center_x
                button_y = button.rect.center_y
                arcade.draw_text(
                    text,
                    button_x,
                    button_y,
                    arcade.color.WHITE,
                    settings.BUTTON_FONT_SIZE,
                    anchor_x="center",
                    anchor_y="center",
                    bold=True
                )

    def on_update(self, delta_time):
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
            
            label_h + slider_h +
            label_h + slider_h +
            row_h + row_h
        )
        total_spacers = 10
        total_h = items_h + spacing * total_spacers + 40
        panel_h = min(total_h, self.screen_height - 120)
        panel_w = min(560, self.screen_width - 120)
        return panel_w, panel_h

    def setup_settings_ui(self):
        s = ProjectSettings.StartWindow
        v_box = arcade.gui.UIBoxLayout(vertical=True, space_between=s.BUTTON_SPACING)

        v_box.add(arcade.gui.UILabel(text=""))
        res_title = arcade.gui.UILabel(text="Разрешение", text_color=arcade.color.WHITE)
        v_box.add(res_title)

        res_row = arcade.gui.UIBoxLayout(vertical=False, space_between=20)
        res_left = arcade.gui.UIFlatButton(text="", width=60, height=s.BUTTON_HEIGHT)
        res_left.on_click = self.on_resolution_left
        res_right = arcade.gui.UIFlatButton(text="", width=60, height=s.BUTTON_HEIGHT)
        res_right.on_click = self.on_resolution_right
        self.res_label = arcade.gui.UILabel(text=self.resolution_text(), text_color=arcade.color.LIGHT_GRAY)
        res_row.add(res_left)
        res_row.add(self.res_label)
        res_row.add(res_right)
        v_box.add(res_row)

        mode_title = arcade.gui.UILabel(text="Режим экрана", text_color=arcade.color.WHITE)
        v_box.add(mode_title)

        mode_row = arcade.gui.UIBoxLayout(vertical=False, space_between=20)
        mode_left = arcade.gui.UIFlatButton(text="", width=60, height=s.BUTTON_HEIGHT)
        mode_left.on_click = self.on_mode_left
        mode_right = arcade.gui.UIFlatButton(text="", width=60, height=s.BUTTON_HEIGHT)
        mode_right.on_click = self.on_mode_right
        self.mode_label = arcade.gui.UILabel(text=self.mode_text(), text_color=arcade.color.LIGHT_GRAY)
        mode_row.add(mode_left)
        mode_row.add(self.mode_label)
        mode_row.add(mode_right)
        v_box.add(mode_row)

        music_title = arcade.gui.UILabel(text="Громкость музыки", text_color=arcade.color.WHITE)
        v_box.add(music_title)
        self.music_volume_slider = arcade.gui.UISlider(value=int(self.music_volume * 100), width=400)
        v_box.add(self.music_volume_slider)

        sound_title = arcade.gui.UILabel(text="Громкость звуков", text_color=arcade.color.WHITE)
        v_box.add(sound_title)
        self.sound_volume_slider = arcade.gui.UISlider(value=int(self.sound_volume * 100), width=400)
        v_box.add(self.sound_volume_slider)

        apply_button = arcade.gui.UIFlatButton(text="", width=s.BUTTON_WIDTH, height=s.BUTTON_HEIGHT)
        apply_button.on_click = self.on_apply_settings_click
        v_box.add(apply_button)

        close_button = arcade.gui.UIFlatButton(text="", width=s.BUTTON_WIDTH, height=s.BUTTON_HEIGHT)
        close_button.on_click = self.on_close_settings_click
        v_box.add(close_button)

        self.buttons = [apply_button, close_button, res_left, res_right, mode_left, mode_right]
        self.button_texts = ["Сохранить", s.SETTINGS_CLOSE_TEXT, "<", ">", "<", ">"]

        anchor_layout = arcade.gui.UIAnchorLayout()
        anchor_layout.add(child=v_box, anchor_x="center_x", anchor_y="center_y")
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

    def on_apply_settings_click(self, event):
        self.music_volume = (self.music_volume_slider.value or 0) / 100.0
        self.sound_volume = (self.sound_volume_slider.value or 0) / 100.0
        if self.settings_player and hasattr(self.settings_player, "volume"):
            try:
                self.settings_player.volume = self.music_volume
            except Exception:
                pass
        self.apply_display_settings()

    def on_resolution_left(self, event):
        self.current_resolution_index = (self.current_resolution_index - 1) % len(self.available_resolutions)
        if self.res_label:
            self.res_label.text = self.resolution_text()

    def on_resolution_right(self, event):
        self.current_resolution_index = (self.current_resolution_index + 1) % len(self.available_resolutions)
        if self.res_label:
            self.res_label.text = self.resolution_text()

    def on_mode_left(self, event):
        self.current_mode_index = (self.current_mode_index - 1) % len(self.display_modes)
        if self.mode_label:
            self.mode_label.text = self.mode_text()

    def on_mode_right(self, event):
        self.current_mode_index = (self.current_mode_index + 1) % len(self.display_modes)
        if self.mode_label:
            self.mode_label.text = self.mode_text()

    def resolution_text(self):
        w, h = self.available_resolutions[self.current_resolution_index]
        return f"{w}×{h}"

    def mode_text(self):
        return self.display_modes[self.current_mode_index]

    def apply_display_settings(self):
        mode = self.display_modes[self.current_mode_index]
        w, h = self.available_resolutions[self.current_resolution_index]

        if mode == "Полноэкранный":
            try:
                if pyglet and hasattr(self, "set_style"):
                    self.set_style(pyglet.window.Window.WINDOW_STYLE_DEFAULT)
            except Exception:
                pass
            try:
                self.set_fullscreen(True)
            except Exception:
                pass
        elif mode == "Полноэкранный в окне":
            try:
                self.set_fullscreen(False)
            except Exception:
                pass
            try:
                if pyglet and hasattr(self, "set_style"):
                    self.set_style(pyglet.window.Window.WINDOW_STYLE_BORDERLESS)
            except Exception:
                pass
            try:
                self.set_location(0, 0)
            except Exception:
                pass
            try:
                self.set_size(self.screen_width, self.screen_height)
            except Exception:
                pass
        else:
            try:
                self.set_fullscreen(False)
            except Exception:
                pass
            try:
                if pyglet and hasattr(self, "set_style"):
                    self.set_style(pyglet.window.Window.WINDOW_STYLE_DEFAULT)
            except Exception:
                pass
            try:
                self.set_size(w, h)
            except Exception:
                pass
            try:
                self.set_location(100, 100)
            except Exception:
                pass

    def play_settings_music(self):
        path = ProjectSettings.StartWindow.SETTINGS_MUSIC_FILE
        if not path:
            return
        if not os.path.isabs(path):
            base_dir = os.path.dirname(os.path.dirname(__file__))
            path = os.path.join(base_dir, path)

        ext = os.path.splitext(path)[1].lower()
        try:
            if ext in ".mp3":
                media = pyglet.media.load(path, streaming=False)
                self.settings_player = media.play()
                self.settings_player.loop = True
                return
        except Exception:
            pass

        try:
            self.settings_sound = arcade.Sound(path)
            self.settings_player = self.settings_sound.play(loop=True)
        except Exception:
            try:
                sound = arcade.load_sound(path)
                self.settings_player = arcade.play_sound(sound)
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
        path = ProjectSettings.StartWindow.MAIN_MUSIC_FILE
        if not path:
            return
        if not os.path.isabs(path):
            base_dir = os.path.dirname(os.path.dirname(__file__))
            path = os.path.join(base_dir, path)
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
            self.main_music_player = self.main_music_sound.play(loop=True)
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
