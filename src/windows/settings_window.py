import arcade
import arcade.gui
import os
import json
import pyglet
import platform
from project import ProjectSettings
from utils import get_config_path


class SettingsView(arcade.View):
    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view
        self.manager = arcade.gui.UIManager()
        self.manager.enable()

        self.saved_window_width = None
        self.saved_window_height = None
        if self.window:
            self.saved_window_width = self.window.width
            self.saved_window_height = self.window.height

        self.available_resolutions = self.get_available_resolutions()

        self.current_resolution_index = 0
        self.current_window_mode = ProjectSettings.Settings.DEFAULT_WINDOW_MODE
        self.sounds_folder = ProjectSettings.Settings.DEFAULT_SOUNDS_FOLDER
        self.sound_volume = ProjectSettings.Settings.DEFAULT_SOUND_VOLUME
        self.music_volume = ProjectSettings.Settings.DEFAULT_MUSIC_VOLUME
        self.custom_sounds = []

        self.background_texture = None
        self.background_list = arcade.SpriteList()
        self.background_sprite = None
        self._bg_sprite = None
        self._bg_sprite_list = None

        self.setup_ui()
        self.load_settings()
        self._ensure_background_sprite()

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
            # print(f"Ошибка получения разрешений: {e}")
            return ProjectSettings.Settings.RESOLUTIONS

    def setup_ui(self):
        settings = ProjectSettings.Settings

        main_box = arcade.gui.UIBoxLayout(vertical=True, space_between=15)

        title_label = arcade.gui.UILabel(
            text="НАСТРОЙКИ",
            font_size=32,
            text_color=arcade.color.WHITE,
            width=settings.SETTINGS_PANEL_WIDTH,
            align="center"
        )
        main_box.add(title_label)

        resolution_label = arcade.gui.UILabel(
            text="Разрешение экрана:",
            font_size=settings.LABEL_FONT_SIZE,
            text_color=arcade.color.WHITE,
            width=settings.SETTINGS_PANEL_WIDTH
        )
        main_box.add(resolution_label)

        resolution_container = arcade.gui.UIBoxLayout(
            vertical=True, space_between=5)
        self.resolution_buttons = []

        buttons_per_row = 4
        for row_start in range(0, len(self.available_resolutions), buttons_per_row):
            row_box = arcade.gui.UIBoxLayout(vertical=False, space_between=5)
            row_resolutions = self.available_resolutions[row_start:row_start + buttons_per_row]

            for i, (w, h) in enumerate(row_resolutions):
                idx = row_start + i
                btn = arcade.gui.UIFlatButton(
                    text=f"{w}x{h}",
                    width=140,
                    height=settings.BUTTON_HEIGHT
                )
                btn.style = {
                    "normal": {
                        "bg_color": arcade.color.DARK_GRAY,
                        "border_color": arcade.color.WHITE,
                        "border_width": 2
                    },
                    "hover": {
                        "bg_color": arcade.color.GRAY,
                        "border_color": arcade.color.WHITE,
                        "border_width": 2
                    },
                    "press": {
                        "bg_color": arcade.color.BLUE,
                        "border_color": arcade.color.WHITE,
                        "border_width": 2
                    }
                }
                btn.on_click = lambda e, index=idx: self.on_resolution_select(
                    index)
                self.resolution_buttons.append(btn)
                row_box.add(btn)

            resolution_container.add(row_box)

        main_box.add(resolution_container)

        window_mode_label = arcade.gui.UILabel(
            text="Режим окна:",
            font_size=settings.LABEL_FONT_SIZE,
            text_color=arcade.color.WHITE,
            width=settings.SETTINGS_PANEL_WIDTH
        )
        main_box.add(window_mode_label)

        window_mode_box = arcade.gui.UIBoxLayout(
            vertical=False, space_between=10)
        self.window_mode_buttons = []
        mode_texts = ["Полноэкранный", "Полноэкранный в окне", "В окне"]
        mode_values = [
            ProjectSettings.Settings.WINDOW_MODE_FULLSCREEN,
            ProjectSettings.Settings.WINDOW_MODE_FULLSCREEN_WINDOWED,
            ProjectSettings.Settings.WINDOW_MODE_WINDOWED
        ]
        for i, (text, value) in enumerate(zip(mode_texts, mode_values)):
            btn = arcade.gui.UIFlatButton(
                text=text,
                width=200,
                height=settings.BUTTON_HEIGHT
            )
            btn.style = {
                "normal": {
                    "bg_color": arcade.color.DARK_GRAY,
                    "border_color": arcade.color.WHITE,
                    "border_width": 2
                },
                "hover": {
                    "bg_color": arcade.color.GRAY,
                    "border_color": arcade.color.WHITE,
                    "border_width": 2
                },
                "press": {
                    "bg_color": arcade.color.BLUE,
                    "border_color": arcade.color.WHITE,
                    "border_width": 2
                }
            }
            btn.on_click = lambda e, val=value: self.on_window_mode_select(val)
            self.window_mode_buttons.append(btn)
            window_mode_box.add(btn)
        main_box.add(window_mode_box)

        sounds_folder_label = arcade.gui.UILabel(
            text="Папка со звуками:",
            font_size=settings.LABEL_FONT_SIZE,
            text_color=arcade.color.WHITE,
            width=settings.SETTINGS_PANEL_WIDTH
        )
        main_box.add(sounds_folder_label)

        self.sounds_folder_input = arcade.gui.UIInputText(
            text=self.sounds_folder,
            width=settings.SETTINGS_PANEL_WIDTH - 20,
            height=settings.BUTTON_HEIGHT,
            font_size=14
        )
        self.sounds_folder_input.on_enter = self.on_sounds_folder_enter
        main_box.add(self.sounds_folder_input)

        add_sound_label = arcade.gui.UILabel(
            text="Добавить кастомный звук (путь к файлу):",
            font_size=settings.LABEL_FONT_SIZE,
            text_color=arcade.color.WHITE,
            width=settings.SETTINGS_PANEL_WIDTH
        )
        main_box.add(add_sound_label)

        add_sound_box = arcade.gui.UIBoxLayout(
            vertical=False, space_between=10)
        self.add_sound_input = arcade.gui.UIInputText(
            text="",
            width=settings.SETTINGS_PANEL_WIDTH - 150,
            height=settings.BUTTON_HEIGHT,
            font_size=14
        )
        self.add_sound_input.on_enter = self.on_add_sound_enter
        add_sound_box.add(self.add_sound_input)

        add_sound_button = arcade.gui.UIFlatButton(
            text="Добавить",
            width=120,
            height=settings.BUTTON_HEIGHT
        )
        add_sound_button.on_click = self.on_add_custom_sound
        add_sound_box.add(add_sound_button)
        main_box.add(add_sound_box)

        self.custom_sounds_label = arcade.gui.UILabel(
            text="Кастомные звуки:",
            font_size=settings.LABEL_FONT_SIZE,
            text_color=arcade.color.WHITE,
            width=settings.SETTINGS_PANEL_WIDTH
        )
        main_box.add(self.custom_sounds_label)

        self.custom_sounds_list_label = arcade.gui.UILabel(
            text="Нет добавленных звуков",
            font_size=14,
            text_color=arcade.color.LIGHT_GRAY,
            width=settings.SETTINGS_PANEL_WIDTH
        )
        main_box.add(self.custom_sounds_list_label)

        self.sound_volume_label = arcade.gui.UILabel(
            text=f"Громкость звуков: {int(self.sound_volume * 100)}%",
            font_size=settings.LABEL_FONT_SIZE,
            text_color=arcade.color.WHITE,
            width=settings.SETTINGS_PANEL_WIDTH
        )
        main_box.add(self.sound_volume_label)

        sound_volume_box = arcade.gui.UIBoxLayout(
            vertical=False, space_between=10)
        minus_btn = arcade.gui.UIFlatButton(
            text="-", width=50, height=settings.BUTTON_HEIGHT)
        minus_btn.on_click = lambda e: self.on_sound_volume_change(-0.1)
        sound_volume_box.add(minus_btn)

        plus_btn = arcade.gui.UIFlatButton(
            text="+", width=50, height=settings.BUTTON_HEIGHT)
        plus_btn.on_click = lambda e: self.on_sound_volume_change(0.1)
        sound_volume_box.add(plus_btn)
        main_box.add(sound_volume_box)

        self.music_volume_label = arcade.gui.UILabel(
            text=f"Громкость музыки: {int(self.music_volume * 100)}%",
            font_size=settings.LABEL_FONT_SIZE,
            text_color=arcade.color.WHITE,
            width=settings.SETTINGS_PANEL_WIDTH
        )
        main_box.add(self.music_volume_label)

        music_volume_box = arcade.gui.UIBoxLayout(
            vertical=False, space_between=10)
        minus_btn = arcade.gui.UIFlatButton(
            text="-", width=50, height=settings.BUTTON_HEIGHT)
        minus_btn.on_click = lambda e: self.on_music_volume_change(-0.1)
        music_volume_box.add(minus_btn)

        plus_btn = arcade.gui.UIFlatButton(
            text="+", width=50, height=settings.BUTTON_HEIGHT)
        plus_btn.on_click = lambda e: self.on_music_volume_change(0.1)
        music_volume_box.add(plus_btn)
        main_box.add(music_volume_box)

        buttons_box = arcade.gui.UIBoxLayout(vertical=False, space_between=20)

        save_button = arcade.gui.UIFlatButton(
            text="Сохранить",
            width=settings.BUTTON_WIDTH,
            height=settings.BUTTON_HEIGHT
        )
        save_button.style = {
            "normal": {
                "bg_color": arcade.color.DARK_GREEN,
                "border_color": arcade.color.WHITE,
                "border_width": 2
            },
            "hover": {
                "bg_color": arcade.color.GREEN,
                "border_color": arcade.color.WHITE,
                "border_width": 2
            },
            "press": {
                "bg_color": arcade.color.DARK_GREEN,
                "border_color": arcade.color.WHITE,
                "border_width": 2
            }
        }
        save_button.on_click = self.on_save_click
        buttons_box.add(save_button)

        cancel_button = arcade.gui.UIFlatButton(
            text="Отмена",
            width=settings.BUTTON_WIDTH,
            height=settings.BUTTON_HEIGHT
        )
        cancel_button.style = {
            "normal": {
                "bg_color": arcade.color.DARK_RED,
                "border_color": arcade.color.WHITE,
                "border_width": 2
            },
            "hover": {
                "bg_color": arcade.color.RED,
                "border_color": arcade.color.WHITE,
                "border_width": 2
            },
            "press": {
                "bg_color": arcade.color.DARK_RED,
                "border_color": arcade.color.WHITE,
                "border_width": 2
            }
        }
        cancel_button.on_click = self.on_cancel_click
        buttons_box.add(cancel_button)

        main_box.add(buttons_box)

        anchor_layout = arcade.gui.UIAnchorLayout()
        anchor_layout.add(
            child=main_box,
            anchor_x="center_x",
            anchor_y="center_y"
        )
        self.manager.add(anchor_layout)

    def on_resolution_select(self, index):
        self.current_resolution_index = index
        for i, btn in enumerate(self.resolution_buttons):
            if i == index:
                btn.style = {
                    "normal": {
                        "bg_color": arcade.color.BLUE,
                        "border_color": arcade.color.WHITE,
                        "border_width": 2
                    },
                    "hover": {
                        "bg_color": arcade.color.LIGHT_BLUE,
                        "border_color": arcade.color.WHITE,
                        "border_width": 2
                    },
                    "press": {
                        "bg_color": arcade.color.DARK_BLUE,
                        "border_color": arcade.color.WHITE,
                        "border_width": 2
                    }
                }
            else:
                btn.style = {
                    "normal": {
                        "bg_color": arcade.color.DARK_GRAY,
                        "border_color": arcade.color.WHITE,
                        "border_width": 2
                    },
                    "hover": {
                        "bg_color": arcade.color.GRAY,
                        "border_color": arcade.color.WHITE,
                        "border_width": 2
                    },
                    "press": {
                        "bg_color": arcade.color.BLUE,
                        "border_color": arcade.color.WHITE,
                        "border_width": 2
                    }
                }

    def on_window_mode_select(self, mode):
        self.current_window_mode = mode

    def on_sounds_folder_enter(self):
        folder_path = self.sounds_folder_input.text.strip()
        if folder_path:
            if os.path.isdir(folder_path):
                self.sounds_folder = folder_path
            else:
                self.sounds_folder = folder_path

    def on_add_sound_enter(self):
        self.on_add_custom_sound(None)

    def on_add_custom_sound(self, event):
        sound_path = self.add_sound_input.text.strip()
        if sound_path:
            if os.path.isfile(sound_path):
                valid_extensions = ['.wav', '.mp3', '.ogg', '.flac', '.m4a']
                if any(sound_path.lower().endswith(ext) for ext in valid_extensions):
                    if sound_path not in self.custom_sounds:
                        self.custom_sounds.append(sound_path)
                        self.update_custom_sounds_list()
                        self.add_sound_input.text = ""
                else:
                    print(f"Неподдерживаемый формат файла: {sound_path}")
            else:
                print(f"Файл не найден: {sound_path}")

    def update_custom_sounds_list(self):
        if self.custom_sounds:
            sounds_text = "\n".join([os.path.basename(s)
                                    for s in self.custom_sounds[:5]])
            if len(self.custom_sounds) > 5:
                sounds_text += f"\n... и еще {len(self.custom_sounds) - 5}"
            self.custom_sounds_list_label.text = sounds_text
        else:
            self.custom_sounds_list_label.text = "Нет добавленных звуков"

    def on_sound_volume_change(self, delta):
        self.sound_volume = max(0.0, min(1.0, self.sound_volume + delta))
        self.sound_volume_label.text = f"Громкость звуков: {int(self.sound_volume * 100)}%"

    def on_music_volume_change(self, delta):
        self.music_volume = max(0.0, min(1.0, self.music_volume + delta))
        self.music_volume_label.text = f"Громкость музыки: {int(self.music_volume * 100)}%"

    def on_save_click(self, event):
        self.on_sounds_folder_enter()
        self.save_settings()
        self.show_restart_message()
        if self.window and self.saved_window_width and self.saved_window_height:
            if not self.window.fullscreen:
                try:
                    self.window.set_size(
                        self.saved_window_width, self.saved_window_height)
                except Exception:
                    pass
        self.window.show_view(self.parent_view)

    def show_restart_message(self):
        print("Настройки сохранены! Для применения изменений разрешения и режима окна перезапустите игру.")

    def on_cancel_click(self, event):
        if self.window and self.saved_window_width and self.saved_window_height:
            if not self.window.fullscreen:
                try:
                    self.window.set_size(
                        self.saved_window_width, self.saved_window_height)
                except Exception:
                    pass
        self.window.show_view(self.parent_view)

    def load_settings(self):
        config_file = get_config_path()
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    saved_index = config.get('resolution_index', 0)
                    if 0 <= saved_index < len(self.available_resolutions):
                        self.current_resolution_index = saved_index
                    else:
                        self.current_resolution_index = 0
                    self.current_window_mode = config.get(
                        'window_mode', self.current_window_mode)
                    self.sounds_folder = config.get(
                        'sounds_folder', self.sounds_folder)
                    self.sound_volume = config.get(
                        'sound_volume', self.sound_volume)
                    self.music_volume = config.get(
                        'music_volume', self.music_volume)
                    self.custom_sounds = config.get('custom_sounds', [])
                    if hasattr(self, 'sounds_folder_input'):
                        self.sounds_folder_input.text = self.sounds_folder
                    if hasattr(self, 'sound_volume_label'):
                        self.sound_volume_label.text = f"Громкость звуков: {int(self.sound_volume * 100)}%"
                    if hasattr(self, 'music_volume_label'):
                        self.music_volume_label.text = f"Громкость музыки: {int(self.music_volume * 100)}%"
                    if hasattr(self, 'resolution_buttons'):
                        self.on_resolution_select(
                            self.current_resolution_index)
                    self.update_custom_sounds_list()
            except Exception as e:
                print(f"Ошибка загрузки настроек: {e}")

    def save_settings(self):
        config = {
            'resolution_index': self.current_resolution_index,
            'window_mode': self.current_window_mode,
            'sounds_folder': self.sounds_folder,
            'sound_volume': self.sound_volume,
            'music_volume': self.music_volume,
            'custom_sounds': self.custom_sounds
        }
        try:
            with open(get_config_path(), 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")

    def on_show_view(self):
        self.manager.enable()
        arcade.set_background_color(ProjectSettings.BACKGROUND_COLOR)
        if self.window:
            if self.saved_window_width is None:
                self.saved_window_width = self.window.width
            if self.saved_window_height is None:
                self.saved_window_height = self.window.height
            if not self.window.fullscreen:
                if self.window.width != self.saved_window_width or self.window.height != self.saved_window_height:
                    try:
                        self.window.set_size(
                            self.saved_window_width, self.saved_window_height)
                    except Exception:
                        pass

            self._ensure_background_sprite()
            self.update_background_scale()

    def on_hide_view(self):
        self.manager.disable()

    def on_draw(self):
        self.clear()

        # Сначала настраиваем viewport и матрицы проекции для правильных координат
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

        # Рисуем фон напрямую через draw_texture_rectangle (центрированно)
        # Оптимизация для macOS - используем более стабильный метод отрисовки
        self._ensure_background_sprite()
        if self.background_texture:
            try:
                # Центр экрана
                center_x = self.width / 2.0
                center_y = self.height / 2.0

                # Масштабируем так, чтобы покрыть весь экран
                texture_width = self.background_texture.width
                texture_height = self.background_texture.height

                if texture_width > 0 and texture_height > 0:
                    scale_x = self.width / texture_width
                    scale_y = self.height / texture_height
                    scale = max(scale_x, scale_y)
                    
                    # Используем SpriteList для отрисовки (работает везде)
                    if not hasattr(self, '_bg_sprite') or self._bg_sprite is None:
                        self._bg_sprite = arcade.Sprite()
                        self._bg_sprite.texture = self.background_texture
                        self._bg_sprite_list = arcade.SpriteList()
                        self._bg_sprite_list.append(self._bg_sprite)
                    
                    self._bg_sprite.center_x = center_x
                    self._bg_sprite.center_y = center_y
                    self._bg_sprite.scale = scale
                    self._bg_sprite_list.draw()
            except Exception as e:
                print(f"Ошибка отрисовки фона: {e}")

        # Рисуем UI элементы
        self.manager.draw()

    def on_update(self, delta_time):
        pass

    def _ensure_background_sprite(self):
        """Ensure background texture is loaded."""
        try:
            bg_path = getattr(ProjectSettings.StartWindow,
                              'BACKGROUND_IMAGE', None)
            if not bg_path:
                return

            if self.background_texture is None:
                try:
                    self.background_texture = arcade.load_texture(bg_path)
                except Exception:
                    try:
                        sprite = arcade.Sprite(bg_path)
                        if sprite and sprite.texture:
                            self.background_texture = sprite.texture
                    except Exception:
                        self.background_texture = None
        except Exception:
            self.background_texture = None

    def update_background_scale(self):
        # Теперь масштабирование делается в on_draw, этот метод оставлен для совместимости
        pass

    def on_resize(self, width, height):
        self.update_background_scale()
