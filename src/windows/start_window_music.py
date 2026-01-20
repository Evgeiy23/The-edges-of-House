"""
Модуль для управления музыкой в стартовом окне
"""
import os
import pyglet
import arcade
from project import ProjectSettings
from game.logic.music import find_music_file as shared_find_music


class StartWindowMusic:
    """Класс-миксин для методов управления музыкой StartWindow"""
    
    def find_music_file(self, preferred_filename=None, folder_path=None):
        """Поиск музыкального файла"""
        return shared_find_music(preferred_filename, folder_path)

    def play_main_music(self):
        """Воспроизведение основной музыки главного меню"""
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
            if self.music_volume <= 0:
                self.main_music_player = self.main_music_sound.play(
                    loop=True, volume=0)
            else:
                self.main_music_player = self.main_music_sound.play(
                    loop=True, volume=self.music_volume)
        except Exception:
            try:
                self.main_music_sound = arcade.Sound(path)
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
        """Приостановка основной музыки"""
        if self.main_music_player:
            try:
                if hasattr(self.main_music_player, "pause"):
                    self.main_music_player.pause()
                else:
                    self.main_music_player.stop()
            except Exception:
                pass

    def resume_main_music(self):
        """Возобновление основной музыки"""
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

    def play_settings_music(self):
        """Воспроизведение музыки настроек"""
        path = self.find_music_file("/Users/evgen/Downloads/The-edges-of-House 8/music/background_music/easter_song.mp3")
        if not path:
            return

        ext = os.path.splitext(path)[1].lower()
        try:
            if ext in ".mp3":
                media = pyglet.media.load(path, streaming=False)
                self.settings_player = media.play()
                self.settings_player.loop = True
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
            if self.music_volume <= 0:
                self.settings_player = self.settings_sound.play(
                    loop=True, volume=0)
            else:
                self.settings_player = self.settings_sound.play(
                    loop=True, volume=self.music_volume)
        except Exception:
            try:
                sound = arcade.load_sound(path)
                if self.music_volume <= 0:
                    self.settings_player = arcade.play_sound(sound, volume=0)
                else:
                    self.settings_player = arcade.play_sound(
                        sound, volume=self.music_volume)
            except Exception:
                self.settings_sound = None
                self.settings_player = None

    def stop_settings_music(self):
        """Остановка музыки настроек"""
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
