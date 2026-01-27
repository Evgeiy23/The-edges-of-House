"""
Модуль для управления настройками в стартовом окне
"""
import os
import json
import pyglet
from project import ProjectSettings
from utils import get_config_path


class StartWindowSettings:
    """Класс-миксин для методов управления настройками StartWindow"""
    
    def load_settings(self):
        """Загрузка настроек из файла"""
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
                # print(f"Ошибка загрузки настроек: {e}")
                pass

    def save_settings(self):
        """Сохранение настроек в файл"""
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
            # print(f"Ошибка сохранения настроек: {e}")
            pass

    def get_window_mode_string(self):
        """Получение строки режима окна"""
        mode = self.display_modes[self.current_mode_index]
        if mode == "Полноэкранный":
            return ProjectSettings.Settings.WINDOW_MODE_FULLSCREEN
        elif mode == "Полноэкранный в окне":
            return ProjectSettings.Settings.WINDOW_MODE_FULLSCREEN_WINDOWED
        else:
            return ProjectSettings.Settings.WINDOW_MODE_WINDOWED

    def apply_display_settings(self):
        """Применение настроек отображения"""
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

    def get_native_resolution(self):
        """Получение нативного разрешения экрана"""
        try:
            display = pyglet.display.get_display()
            screen = display.get_default_screen()
            return screen.width, screen.height
        except Exception:
            return 1920, 1080

    def get_available_resolutions(self):
        """Получение списка доступных разрешений"""
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
