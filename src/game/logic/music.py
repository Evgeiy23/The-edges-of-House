import os
import pyglet
import arcade
from project import ProjectSettings


def find_music_file(preferred_filename=None, folder_path=None):
    if folder_path is None:
        folder_path = ProjectSettings.Settings.DEFAULT_SOUNDS_FOLDER

    if not os.path.exists(folder_path):
        return None

    valid_extensions = ['.mp3', '.wav', '.ogg', '.flac', '.m4a']

    # Если задано имя, ищем его по всем подпапкам
    if preferred_filename:
        try:
            for root, _, files in os.walk(folder_path):
                for name in files:
                    if name == preferred_filename:
                        candidate = os.path.join(root, name)
                        if os.path.isfile(candidate):
                            return candidate
        except Exception:
            pass

    # Иначе собираем первый подходящий файл из всех подпапок
    try:
        for root, _, files in os.walk(folder_path):
            for name in files:
                ext = os.path.splitext(name)[1].lower()
                if ext in valid_extensions:
                    return os.path.join(root, name)
    except Exception:
        pass

    return None


def play_loop(path, volume=1.0):
    if not path:
        return None, None
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == ".mp3":
            media = pyglet.media.load(path, streaming=False)
            player = media.play()
            player.loop = True
            try:
                player.volume = volume
            except Exception:
                pass
            return player, None
    except Exception:
        pass

    try:
        sound = arcade.Sound(path)
        player = sound.play(loop=True, volume=volume)
        return player, sound
    except Exception:
        try:
            sound = arcade.Sound(path)
            player = sound.play(loop=True)
            if hasattr(player, 'volume'):
                player.volume = volume
            return player, sound
        except Exception:
            return None, None


def stop_player(player):
    if not player:
        return
    try:
        if hasattr(player, "pause"):
            try:
                player.loop = False
            except Exception:
                pass
            player.pause()
            try:
                player.delete()
            except Exception:
                pass
        else:
            player.stop()
    except Exception:
        pass


def play_once(path, volume=1.0):
    if not path:
        return None, None
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == ".mp3":
            media = pyglet.media.load(path, streaming=False)
            player = media.play()
            try:
                player.volume = volume
            except Exception:
                pass
            return player, None
    except Exception:
        pass
    try:
        sound = arcade.Sound(path)
        player = sound.play(volume=volume)
        return player, sound
    except Exception:
        try:
            sound = arcade.Sound(path)
            player = sound.play()
            if hasattr(player, 'volume'):
                player.volume = volume
            return player, sound
        except Exception:
            return None, None
