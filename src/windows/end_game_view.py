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
        
        # Paths
        self.video_path = os.path.join(os.getcwd(), "resources", "videos", "theend.mp4")
        self.music_path = os.path.join(os.getcwd(), "music", "theend.wav")
        
        # State
        self.PHASE_VIDEO = 0
        self.PHASE_END_SCREEN = 1
        self.current_phase = self.PHASE_VIDEO
        
        # Video
        self.video_player = None
        self.video_texture = None
        
        # Audio
        self.music_player = None
        
        # UI
        self.ui_manager = arcade.gui.UIManager()
        self.ui_manager.enable()
        self.setup_ui()
        self.ui_manager.disable() # Enable only in end screen phase
        
        # Start sequence
        self.start_sequence()

    def start_sequence(self):
        # 1. Stop all game sounds
        if self.game_view:
            self.game_view.stop_suspense_music()
            self.game_view.stop_game_music()
            # Stop any other sounds if possible
            arcade.stop_sound(self.game_view.story_audio_player) if self.game_view.story_audio_player else None
            
        # 2. Start Video
        if os.path.exists(self.video_path):
            try:
                source = pyglet.media.load(self.video_path)
                self.video_player = pyglet.media.Player()
                self.video_player.queue(source)
                self.video_player.volume = 0 # Mute video sound as requested ("все игровые звуки обрываются")
                self.video_player.play()
                print("End game video started.")
            except Exception as e:
                print(f"Error loading end video: {e}")
                self.current_phase = self.PHASE_END_SCREEN
        else:
            print(f"End video not found: {self.video_path}")
            self.current_phase = self.PHASE_END_SCREEN

        # 3. Start Music ("начинает играть музыка")
        if os.path.exists(self.music_path):
            try:
                # Use MusicManager if available or direct play
                # Direct play for simplicity in this view
                sound = arcade.load_sound(self.music_path)
                self.music_player = arcade.play_sound(sound, loop=True, volume=1.0)
            except Exception as e:
                print(f"Error loading end music: {e}")
        
    def setup_ui(self):
        # Text "Спасибо, что помогли Элиасу"
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
        
        # Buttons
        menu_button = arcade.gui.UIFlatButton(text="В главное меню", width=250)
        stats_button = arcade.gui.UIFlatButton(text="Статистика", width=250)
        
        menu_button.on_click = self.on_menu_click
        stats_button.on_click = self.on_stats_click
        
        self.v_box.add(menu_button)
        self.v_box.add(stats_button)
        
        # Layout
        self.ui_anchor = arcade.gui.UIAnchorLayout()
        self.ui_anchor.add(child=self.v_box, anchor_x="center_x", anchor_y="center_y")
        self.ui_manager.add(self.ui_anchor)

    def on_menu_click(self, event):
        # Return to main menu (restart game for now as main menu might not be separate)
        # Or close app? Usually "Main Menu" implies restart or title screen.
        # Assuming setup_game resets everything.
        # But wait, we might need to go to a TitleView if it exists.
        # Checking LoadingView... it switches to GameWindow.
        # I'll restart the GameWindow for now.
        self.cleanup()
        self.game_view.setup_game()
        self.window.show_view(self.game_view)

    def on_stats_click(self, event):
        # Show stats
        # We can reuse GameOverView or show a popup.
        # Let's switch to GameOverView which already has stats display
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
        
        # Draw Video
        if self.current_phase == self.PHASE_VIDEO and self.video_texture:
            self.video_texture.blit(0, 0, width=self.window.width, height=self.window.height)
        elif self.current_phase == self.PHASE_END_SCREEN:
            # Draw background (maybe last video frame or black)
            arcade.draw_lrbt_rectangle_filled(0, self.window.width, 0, self.window.height, arcade.color.BLACK)
            self.ui_manager.draw()
