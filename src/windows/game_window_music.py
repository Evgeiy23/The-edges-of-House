"""
Модуль для управления музыкой и звуками
"""
import random
from game.logic.music_manager import MusicManager
from project import ProjectSettings

class GameWindowMusic:
    """Класс-миксин для методов управления музыкой"""

    def reset_level_music(self):
        """Сброс выбранной музыки уровня (вызывается при переходе на новый уровень)"""
        self.current_level_music_path = None

    def play_game_music(self):
        """Воспроизведение игровой музыки"""
        if not ProjectSettings.MUSIC_ENABLED:
            return
            
        # Пасхалка 40 уровня
        if hasattr(self, 'level') and self.level == 40:
            MusicManager().play(
                MusicManager.PATH_LEVEL_40,
                MusicManager.PRIORITY_LEVEL_SPECIAL,
                loop=True,
                volume=getattr(self, 'music_volume', 1.0)
            )
            return

        # Обычная музыка уровня
        # Выбрать один случайный трек из вариантов, если еще не выбран
        if not hasattr(self, 'current_level_music_path') or self.current_level_music_path is None:
            self.current_level_music_path = random.choice(MusicManager.PATH_LEVEL_OPTIONS)
        
        MusicManager().play(
            self.current_level_music_path,
            MusicManager.PRIORITY_LEVEL,
            loop=True,
            volume=getattr(self, 'music_volume', 1.0)
        )

    def stop_game_music(self):
        """Остановка игровой музыки"""
        # Остановить все до приоритета уровня (включая музыку уровня)
        MusicManager().stop(priority_threshold=MusicManager.PRIORITY_LEVEL_SPECIAL)

    def play_suspense_music(self):
        """Воспроизведение музыки в комнате с боссом"""
        if not ProjectSettings.MUSIC_ENABLED:
            return

        MusicManager().play(
            MusicManager.PATH_BOSS,
            MusicManager.PRIORITY_BOSS,
            loop=True,
            volume=getattr(self, 'music_volume', 1.0)
        )

    def stop_suspense_music(self):
        """Останавливает музыку комнаты с выходом"""
        # Остановить музыку босса.
        MusicManager().stop(priority_threshold=MusicManager.PRIORITY_BOSS)
        
        # Опционально возобновить музыку игры, если мы не выходим из игры
        # self.play_game_music() # Это может быть рискованно, если вызвано во время очистки
        
    def update_music(self, delta_time):
        MusicManager().update(delta_time)
