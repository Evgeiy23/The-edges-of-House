import arcade
import arcade.gui
import os
import pyglet
from game.logic.music_manager import MusicManager
from windows.game_over_view import GameOverView # For reusing stats logic if needed, or just standard view
from windows.start_window import StartWindow

class EndGameView(arcade.View):
    def __init__(self, game_view, stats=None):
        super().__init__()
        self.game_view = game_view
        self.stats = stats or {}
        self.window = game_view.window
        
        # Пути
        self.video_path = os.path.join(os.getcwd(), "resources", "videos", "theend.mp4")
        self.music_path = os.path.join(os.getcwd(), "music", "theend.wav")
        
        # Состояние
        self.PHASE_VIDEO = 0
        self.PHASE_END_SCREEN = 1
        self.current_phase = self.PHASE_VIDEO
        
        # Видео
        self.video_player = None
        self.video_texture = None
        
        # Аудио
        self.music_player = None
        
        # Интерфейс
        self.ui_manager = arcade.gui.UIManager()
        self.ui_manager.enable()
        self.setup_ui()
        self.ui_manager.disable() # Включаем только в фазе экрана окончания
        
        # Последовательность запуска
        self.start_sequence()

    def start_sequence(self):
        # 1. Остановить все игровые звуки
        if self.game_view:
            self.game_view.stop_suspense_music()
            self.game_view.stop_game_music()
            # Остановить другие звуки, если возможно
            arcade.stop_sound(self.game_view.story_audio_player) if self.game_view.story_audio_player else None
            
        # 2. Запустить видео
        if os.path.exists(self.video_path):
            try:
                source = pyglet.media.load(self.video_path)
                self.video_player = pyglet.media.Player()
                self.video_player.queue(source)
                self.video_player.volume = 0 # Заглушить звук видео по запросу ("все игровые звуки обрываются")
                self.video_player.play()
                print("End game video started.")
            except Exception as e:
                print(f"Error loading end video: {e}")
                self.current_phase = self.PHASE_END_SCREEN
        else:
            print(f"End video not found: {self.video_path}")
            self.current_phase = self.PHASE_END_SCREEN

        # 3. Запустить музыку ("начинает играть музыка")
        if os.path.exists(self.music_path):
            try:
                # Использовать MusicManager если доступен или прямое воспроизведение
                # Прямое воспроизведение для простоты в этом виде
                sound = arcade.load_sound(self.music_path)
                self.music_player = arcade.play_sound(sound, loop=True, volume=1.0)
            except Exception as e:
                print(f"Error loading end music: {e}")
        
    def setup_ui(self):
        # Текст "Спасибо, что помогли Элиасу"
        text_label = arcade.gui.UILabel(
            text="Спасибо, что помогли Элиасу",
            font_size=30,
            font_name="Kenney Future",
            text_color=arcade.color.WHITE,
            width=800,
            align="center",
            multiline=True
        )
        
        self.v_box = arcade.gui.UIBoxLayout(space_between=20)
        self.v_box.add(text_label)
        
        # Кнопки
        menu_button = arcade.gui.UIFlatButton(text="В главное меню", width=250)
        stats_button = arcade.gui.UIFlatButton(text="Статистика", width=250)
        
        menu_button.on_click = self.on_menu_click
        stats_button.on_click = self.on_stats_click
        
        self.v_box.add(menu_button)
        self.v_box.add(stats_button)
        
        # Макет
        self.ui_anchor = arcade.gui.UIAnchorLayout()
        self.ui_anchor.add(child=self.v_box, anchor_x="center_x", anchor_y="center_y")
        self.ui_manager.add(self.ui_anchor)

    def on_menu_click(self, event):
        # Вернуться в главное меню (пока перезапуск игры, так как главное меню может не быть отдельным)
        # Или закрыть приложение? Обычно "Главное меню" подразумевает перезапуск или титульный экран.
        # Предполагаем, что setup_game сбрасывает все.
        # Но стоп, нам может понадобиться перейти к TitleView, если он существует.
        # Проверяем LoadingView... он переключается на GameWindow.
        # Я перезапущу GameWindow пока что.
        self.cleanup()
        self.game_view.setup_game()
        self.window.show_view(self.game_view)

    def on_stats_click(self, event):
        # Показать статистику
        # Мы можем переиспользовать GameOverView или показать всплывающее окно.
        # Давайте переключимся на GameOverView, у которого уже есть отображение статистики
        self.cleanup()
        game_over = GameOverView(self.game_view, self.stats)
        self.window.show_view(game_over)

    def cleanup(self):
        if self.video_player:
            self.video_player.pause()
            self.video_player.delete()
        if self.music_player:
            arcade.stop_sound(self.music_player)

    def on_update(self, delta_time):
        if self.current_phase == self.PHASE_VIDEO:
            if self.video_player:
                try:
                    if self.video_player.source and self.video_player.source.video_format:
                         if hasattr(self.video_player, 'texture'):
                            self.video_texture = self.video_player.texture
                         elif hasattr(self.video_player, 'get_texture'):
                            self.video_texture = self.video_player.get_texture()
                    
                    if self.video_player.time >= self.video_player.source.duration - 0.1:
                        self.current_phase = self.PHASE_END_SCREEN
                        self.ui_manager.enable()
                except Exception:
                    self.current_phase = self.PHASE_END_SCREEN
                    self.ui_manager.enable()
            else:
                self.current_phase = self.PHASE_END_SCREEN
                self.ui_manager.enable()

    def on_draw(self):
        self.clear()
        
        # Отрисовка видео
        if self.current_phase == self.PHASE_VIDEO and self.video_texture:
            self.video_texture.blit(0, 0, width=self.window.width, height=self.window.height)
        elif self.current_phase == self.PHASE_END_SCREEN:
            # Отрисовка фона (может быть последний кадр видео или черный)
            arcade.draw_lrbt_rectangle_filled(0, self.window.width, 0, self.window.height, arcade.color.BLACK)
            self.ui_manager.draw()
