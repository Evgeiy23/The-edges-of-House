"""
Модуль для управления музыкой в стартовом окне
"""
from game.logic.music_manager import MusicManager

class StartWindowMusic:
    """Класс-миксин для методов управления музыкой StartWindow"""
    
    def play_main_music(self):
        """Воспроизведение основной музыки главного меню"""
        MusicManager().play(
            MusicManager.PATH_MENU_MAIN, 
            MusicManager.PRIORITY_MENU, 
            loop=True, 
            volume=getattr(self, 'music_volume', 1.0)
        )

    def play_settings_music(self):
        """Воспроизведение музыки настроек"""
        MusicManager().play(
            MusicManager.PATH_MENU_SETTINGS, 
            MusicManager.PRIORITY_MENU, 
            loop=True, 
            volume=getattr(self, 'music_volume', 1.0)
        )
        
    def stop_settings_music(self):
        """Остановка музыки настроек"""
        # MusicManager автоматически обрабатывает переключение, поэтому это может быть холостая операция
        # или мы можем остановить, если строго хотим тишины перед следующим треком
        pass

    def resume_main_music(self):
        """Возобновление основной музыки"""
        self.play_main_music()

    def pause_main_music(self):
        """Приостановка основной музыки (фактически остановка)"""
        MusicManager().stop()
        
    def stop_music(self):
        """Остановка музыки"""
        MusicManager().stop()

    def update_music(self, delta_time):
        """Обновление менеджера музыки"""
        MusicManager().update(delta_time)
