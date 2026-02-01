import arcade
import arcade.gui

class GameOverView(arcade.View):
    def __init__(self, game_view, stats=None):
        super().__init__()
        self.game_view = game_view
        self.stats = stats or {}
        
        # Создание макета
        self.ui_manager = arcade.gui.UIManager()
        self.ui_manager.enable()

        # Надпись "Конец игры"
        self.text_area = arcade.gui.UILabel(
            text="ИГРА ОКОНЧЕНА",
            font_size=50,
            font_name="Kenney Future",
            text_color=arcade.color.RED,
            width=400,
            align="center"
        )
        
        self.v_box = arcade.gui.UIBoxLayout(space_between=20)
        self.v_box.add(self.text_area)

        # Статистика
        if self.stats:
            stats_box = arcade.gui.UIBoxLayout(vertical=True, space_between=10)
            if "chests" in self.stats:
                stats_box.add(arcade.gui.UILabel(
                    text=f"Сундуков открыто: {self.stats['chests']}",
                    font_size=16,
                    text_color=arcade.color.WHITE
                ))
            if "cheats" in self.stats:
                stats_box.add(arcade.gui.UILabel(
                    text=f"Использовано читов: {self.stats['cheats']}",
                    font_size=16,
                    text_color=arcade.color.WHITE
                ))
            self.v_box.add(stats_box)
        
        # Кнопка перезапуска
        restart_button = arcade.gui.UIFlatButton(text="Заново", width=200)
        
        # Кнопка выхода
        exit_button = arcade.gui.UIFlatButton(text="Выход", width=200)

        # Обработчики
        restart_button.on_click = self.on_restart
        exit_button.on_click = self.on_exit

        self.v_box.add(restart_button)
        self.v_box.add(exit_button)

        # Layout
        self.ui_anchor = arcade.gui.UIAnchorLayout()
        self.ui_anchor.add(child=self.v_box, anchor_x="center_x", anchor_y="center_y")
        self.ui_manager.add(self.ui_anchor)

    def on_restart(self, event):
        # Сброс игры
        self.game_view.setup_game()
        self.window.show_view(self.game_view)

    def on_exit(self, event):
        arcade.exit()

    def on_draw(self):
        self.clear()
        
        # Отрисовка игрового вида на фоне (затемненного) если возможно, или просто черный
        if self.game_view:
             self.game_view.on_draw()
        
        # Отрисовка интерфейса
        self.ui_manager.draw()
