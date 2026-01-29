import os
import random
import pyglet
import arcade
from project import ProjectSettings
from game.logic.music import stop_player

class MusicManager:
    _instance = None
    
    # Приоритеты
    PRIORITY_NONE = 0
    PRIORITY_MENU = 10
    PRIORITY_LEVEL = 20
    PRIORITY_LEVEL_SPECIAL = 30
    PRIORITY_BOSS = 40
    PRIORITY_GAME_OVER = 50

    # Пути (относительно корня проекта)
    PATH_MENU_MAIN = os.path.join("music", "background_music", "scary_horror_theme.mp3")
    PATH_MENU_SETTINGS = os.path.join("music", "background_music", "menu_background_theme.mp3")
    
    PATH_LEVEL_OPTIONS = [
        os.path.join("music", "sound_effects", "circuit_grind_theme.mp3"),
        os.path.join("music", "background_music", "dark_grim_horror_ambience.mp3")
    ]
    
    PATH_LEVEL_40 = os.path.join("music", "background_music", "easter_song.mp3")
    
    PATH_BOSS = os.path.join("music", "sound_effects", "berserker_theme.mp3")
    PATH_GAME_OVER = os.path.join("music", "sound_effects", "game_over_voice.mp3")

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MusicManager, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        if self.initialized:
            return
        self.initialized = True
        self.current_player = None
        self.current_priority = self.PRIORITY_NONE
        self.current_track_path = None
        self.target_volume = 1.0
        self.current_volume = 0.0
        self.fade_speed = 0.5 # Изменение громкости в секунду
        self.state = "idle" # idle, fading_in, fading_out, playing (ожидание, нарастание, затухание, воспроизведение)
        
        # Сохраненный запрос
        self.pending_request = None
        
        # Определение корневого пути (e:\Projects\The-edges-of-House)
        # предполагается, что этот файл находится в src/game/logic/
        self.root_path = os.getcwd()

    def get_full_path(self, relative_path):
        # Сначала пробуем относительно текущего рабочего каталога
        if os.path.exists(relative_path):
            return relative_path
        # Пробуем объединить с корнем
        full = os.path.join(self.root_path, relative_path)
        if os.path.exists(full):
            return full
        return None 

    def play(self, relative_path, priority, loop=True, volume=1.0):
        if not ProjectSettings.MUSIC_ENABLED:
            return

        full_path = self.get_full_path(relative_path)
        if not full_path:
            print(f"MusicManager: File not found: {relative_path}")
            return

        # Если уже играет трек с более высоким приоритетом, игнорируем
        if self.current_player and self.current_priority > priority:
            return

        # Если играет тот же трек, просто обеспечиваем громкость/приоритет
        if self.current_track_path == full_path and self.current_player:
            self.current_priority = priority
            self.target_volume = volume
            if self.state != "playing":
                self.state = "fading_in"
            return
            
        # Очередь переключения
        self.pending_request = {
            "path": full_path,
            "priority": priority,
            "loop": loop,
            "volume": volume
        }
        self.state = "fading_out"

    def stop(self, priority_threshold=0):
        # Остановить, если текущий приоритет <= порога
        if self.current_priority <= priority_threshold:
             self.state = "fading_out"
             self.pending_request = None # Нет нового трека
             self.current_priority = 0

    def update(self, delta_time):
        if not ProjectSettings.MUSIC_ENABLED:
            if self.current_player:
                stop_player(self.current_player)
                self.current_player = None
                self.state = "idle"
            return

        # Затухание
        if self.state == "fading_out":
            self.current_volume -= self.fade_speed * delta_time
            if self.current_volume <= 0:
                self.current_volume = 0
                if self.current_player:
                    stop_player(self.current_player)
                    self.current_player = None
                
                # Переключиться на ожидающий, если есть
                if self.pending_request:
                    self._start_pending()
                else:
                    self.state = "idle"
            else:
                 self._set_volume(self.current_volume)

        # Нарастание
        elif self.state == "fading_in":
             if self.current_volume < self.target_volume:
                 self.current_volume += self.fade_speed * delta_time
                 if self.current_volume > self.target_volume:
                     self.current_volume = self.target_volume
                     self.state = "playing"
                 self._set_volume(self.current_volume)
             else:
                 self.state = "playing"
                 # Убедиться, что громкость установлена на целевую
                 self._set_volume(self.target_volume)

    def _start_pending(self):
        req = self.pending_request
        self.pending_request = None
        path = req["path"]
        
        try:
            # Попробовать загрузить с помощью pyglet сначала для mp3
            if path.endswith(".mp3"):
                media = pyglet.media.load(path, streaming=False)
                self.current_player = media.play()
                self.current_player.loop = req["loop"]
            else:
                sound = arcade.Sound(path)
                self.current_player = sound.play(loop=req["loop"], volume=0)
            
            self.current_track_path = path
            self.current_priority = req["priority"]
            self.target_volume = req["volume"]
            self.current_volume = 0
            self._set_volume(0)
            self.state = "fading_in"
            
        except Exception as e:
            print(f"MusicManager: Error playing music {path}: {e}")
            self.state = "idle"

    def set_volume(self, volume):
        self.target_volume = max(0.0, min(1.0, volume))
        # Если мы в состоянии воспроизведения, немедленно обновляем цель (логика затухания обрабатывает плавность,
        # но для ползунка настроек мы можем хотеть немедленной обратной связи или просто установить цель)
        # Пока просто установим цель, и если воспроизведение/нарастание, убедимся, что двигаемся к ней.
        # Если хотим немедленного обновления для ползунка:
        if self.current_player:
            try:
                self.current_player.volume = self.target_volume
                self.current_volume = self.target_volume
            except:
                pass

    def _set_volume(self, vol):
        if self.current_player:
            try:
                self.current_player.volume = vol
            except:
                pass
