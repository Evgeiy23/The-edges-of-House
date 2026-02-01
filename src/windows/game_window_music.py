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
        # Отключено для обеспечения непрерывного воспроизведения одного трека
        # self.current_level_music_path = None
        pass

    def play_game_music(self):
        """Воспроизведение игровой музыки"""
        if not ProjectSettings.MUSIC_ENABLED:
            return
            
        # Пасхалка 40 уровня (оставляем или убираем? Пользователь просил "жестко зафиксировать один музыкальный трек")
        # "один музыкальный трек, который будет непрерывно воспроизводиться... без перерывов и переключений"
        # Наверное, лучше убрать и пасхалку, чтобы быть строгим. Но 40 уровень это спец случай.
        # Оставим спец. уровень, если это критично, но для обычного геймплея фиксируем.
        # Допустим, пользователь хочет ОДИН трек вообще.
        
        # Фиксируем трек (берем первый из списка или конкретный)
        if not hasattr(self, 'current_level_music_path') or self.current_level_music_path is None:
            # Всегда используем первый трек из списка вариантов для стабильности
            if MusicManager.PATH_LEVEL_OPTIONS:
                self.current_level_music_path = MusicManager.PATH_LEVEL_OPTIONS[0]
            else:
                return # Нет музыки
        
        # Играем с высоким приоритетом, чтобы ничего не перебило?
        # Или просто играем.
        MusicManager().play(
            self.current_level_music_path,
            MusicManager.PRIORITY_LEVEL,
            loop=True,
            volume=getattr(self, 'music_volume', 1.0)
        )

    def stop_game_music(self):
        """Остановка игровой музыки"""
        # Не останавливаем, если хотим непрерывность?
        # Но при выходе в меню надо остановить.
        # Метод вызывается при смене view.
        MusicManager().stop(priority_threshold=MusicManager.PRIORITY_LEVEL_SPECIAL)

    def play_suspense_music(self):
        """Воспроизведение музыки в комнате с боссом"""
        # Отключено по запросу пользователя (без переключений)
        pass

    def stop_suspense_music(self):
        """Останавливает музыку комнаты с выходом"""
        # Отключено
        pass
        
    def update_music(self, delta_time):
        MusicManager().update(delta_time)
