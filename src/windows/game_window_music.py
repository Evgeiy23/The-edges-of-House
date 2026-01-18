"""
Модуль для управления музыкой и звуками
"""
from game.logic.music import find_music_file, play_loop, stop_player, play_once


class GameWindowMusic:
    """Класс-миксин для методов управления музыкой"""
    
    def find_music_file(self, preferred_filename=None, folder_path=None):
        """Поиск музыкального файла"""
        return find_music_file(preferred_filename, folder_path)

    def play_game_music(self):
        """Воспроизведение игровой музыки"""
        path = self.find_music_file("dark_grim_horror_ambience.mp3")
        self.stop_game_music()
        self.game_music_player, self.game_music_sound = play_loop(
            path, self.music_volume)

    def stop_game_music(self):
        """Остановка игровой музыки"""
        stop_player(self.game_music_player)
        self.game_music_player = None
        self.game_music_sound = None

    def play_suspense_music(self):
        """Воспроизведение музыки в комнате с боссом"""
        path = "/Users/evgen/Downloads/The-edges-of-House 4/music/suspense-horror-music-loop-382813.mp3"
        self.stop_suspense_music()
        if path:
            self.suspense_player, _ = play_loop(path, self.music_volume)

    def stop_suspense_music(self):
        """Останавливает музыку комнаты с выходом"""
        if self.suspense_player:
            stop_player(self.suspense_player)
            self.suspense_player = None
