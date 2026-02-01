import os
import argparse
from dotenv import load_dotenv

load_dotenv()

import arcade
import json
import pyglet
import warnings
# Подавить все предупреждения, включая PerformanceWarning от Arcade
warnings.filterwarnings("ignore")
from windows.start_window import StartWindow
from project import ProjectSettings
from utils import get_config_path


def load_window_settings():
    config_file = get_config_path()

    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                resolution_index = config.get('resolution_index', 0)
                window_mode = config.get(
                    'window_mode', ProjectSettings.Settings.DEFAULT_WINDOW_MODE)

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

                except Exception:
                    resolutions = ProjectSettings.Settings.RESOLUTIONS

                if 0 <= resolution_index < len(resolutions):
                    width, height = resolutions[resolution_index]
                else:
                    width, height = resolutions[0] if resolutions else (
                        1920, 1080)

                fullscreen = (
                    window_mode == ProjectSettings.Settings.WINDOW_MODE_FULLSCREEN)

                return width, height, fullscreen, window_mode

        except Exception as e:
            pass
            # print(f"Ошибка загрузки настроек: {e}")

    return 1920, 1080, ProjectSettings.FULLSCREEN, ProjectSettings.Settings.DEFAULT_WINDOW_MODE


def main():
    parser = argparse.ArgumentParser(description="The Edges of House Game")
    parser.add_argument("--wc", "--with-cheats", action="store_true", help="Enable cheats")
    parser.add_argument("--wom", "--without-music", action="store_true", help="Disable music")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode (show outlines)")
    args = parser.parse_args()

    ProjectSettings.CHEATS_ENABLED = args.wc
    ProjectSettings.MUSIC_ENABLED = not args.wom
    ProjectSettings.DEBUG_MODE = args.debug

    if ProjectSettings.CHEATS_ENABLED:
        ProjectSettings.VERSION += ".1-cheats"

    width, height, fullscreen, window_mode = load_window_settings()

    window = arcade.Window(
        width=width,
        height=height,
        title=ProjectSettings.WINDOW_TITLE,
        fullscreen=fullscreen
    )

    if window_mode == ProjectSettings.Settings.WINDOW_MODE_WINDOWED:
        try:
            display = pyglet.display.get_display()
            screen = display.get_default_screen()
            x = (screen.width - width) // 2
            y = (screen.height - height) // 2
            window.set_location(x, y)
        except Exception:
            pass

    start_view = StartWindow()
    window.show_view(start_view)
    arcade.run()


if __name__ == "__main__":
    main()
