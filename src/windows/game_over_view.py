import arcade
import arcade.gui

class GameOverView(arcade.View):
    def __init__(self, game_view):
        super().__init__()
        self.game_view = game_view
        self.ui_manager = arcade.gui.UIManager()
        self.ui_manager.enable()
        
        # Create layout
        self.v_box = arcade.gui.UIBoxLayout()
        
        # Game Over Label
        game_over_label = arcade.gui.UILabel(
            text="ИГРА ОКОНЧЕНА",
            font_size=50,
            font_name="Kenney Future",
            text_color=arcade.color.RED,
            bold=True
        )
        self.v_box.add(game_over_label.with_space_around(bottom=20))
        
        # Restart Button
        restart_button = arcade.gui.UIFlatButton(text="Заново", width=200)
        self.v_box.add(restart_button.with_space_around(bottom=20))
        
        # Exit Button
        exit_button = arcade.gui.UIFlatButton(text="Выход", width=200)
        self.v_box.add(exit_button.with_space_around(bottom=20))
        
        # Handlers
        restart_button.on_click = self.on_restart_click
        exit_button.on_click = self.on_exit_click
        
        # Anchor widget
        self.ui_manager.add(
            arcade.gui.UIAnchorWidget(
                anchor_x="center_x",
                anchor_y="center_y",
                child=self.v_box)
        )

    def on_restart_click(self, event):
        # Reset game
        self.game_view.setup_game()
        self.window.show_view(self.game_view)
        
    def on_exit_click(self, event):
        arcade.close_window()

    def on_draw(self):
        self.clear()
        # Draw game view in background (dimmed) if possible, or just black
        # self.game_view.on_draw()
        arcade.draw_rectangle_filled(self.window.width / 2, self.window.height / 2,
                                     self.window.width, self.window.height,
                                     (0, 0, 0, 200))
        self.ui_manager.draw()
