import os
import platform


def get_app_data_dir():
    system = platform.system()
    if system == "Windows":
        appdata = os.getenv("LOCALAPPDATA")
        if appdata:
            return os.path.join(os.path.dirname(appdata), "LocalLow", "TheEdgesOfHouse")
        else:
            return os.path.join(os.path.expanduser("~"), "AppData", "LocalLow", "TheEdgesOfHouse")
    else:
        return os.path.join(os.path.expanduser("~"), "TheEdgesOfHouse")


def get_config_path():
    app_dir = get_app_data_dir()
    os.makedirs(app_dir, exist_ok=True)
    return os.path.join(app_dir, "config.json")


def get_savegame_path():
    app_dir = get_app_data_dir()
    os.makedirs(app_dir, exist_ok=True)
    return os.path.join(app_dir, "savegame.json")
