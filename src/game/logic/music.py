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

    if preferred_filename:
        preferred_path = os.path.join(folder_path, preferred_filename)
        if os.path.isfile(preferred_path):
            return preferred_path

    music_files = []
    try:
        for file in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file)
            if os.path.isfile(file_path):
                ext = os.path.splitext(file)[1].lower()
                if ext in valid_extensions:
                    music_files.append(file_path)
    except Exception:
        return None

    if music_files:
        return music_files[0]
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
