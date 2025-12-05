import arcade
import arcade.gui
from project import ProjectSettings


class DifficultyDialog(arcade.View):
    DIFFICULTY_EASY = "easy"
    DIFFICULTY_MEDIUM = "medium"
    DIFFICULTY_HARD = "hard"

    def __init__(self, current_difficulty, parent_view):
        super().__init__()
        self.parent_view = parent_view
        self.current_difficulty = current_difficulty
        self.selected_difficulty = current_difficulty

        self.manager = arcade.gui.UIManager()
        self.manager.enable()

        self.setup_ui()

    def setup_ui(self):
        settings = ProjectSettings.Settings

        main_box = arcade.gui.UIBoxLayout(vertical=True, space_between=15)

        title_label = arcade.gui.UILabel(
            text="ИЗМЕНИТЬ СЛОЖНОСТЬ",
            font_size=32,
            text_color=arcade.color.WHITE,
            width=settings.SETTINGS_PANEL_WIDTH,
            align="center"
        )
        main_box.add(title_label)

        difficulty_label = arcade.gui.UILabel(
            text="Сложность:",
            font_size=settings.LABEL_FONT_SIZE,
            text_color=arcade.color.WHITE,
            width=settings.SETTINGS_PANEL_WIDTH
        )
        main_box.add(difficulty_label)

        difficulty_box = arcade.gui.UIBoxLayout(
            vertical=False, space_between=10)
        difficulty_texts = ["Легкий", "Средний", "Сложный"]
        difficulty_values = [self.DIFFICULTY_EASY,
                             self.DIFFICULTY_MEDIUM, self.DIFFICULTY_HARD]

        for text, value in zip(difficulty_texts, difficulty_values):
            btn = arcade.gui.UIFlatButton(
                text=text,
                width=200,
                height=settings.BUTTON_HEIGHT
            )
            btn.style = {
                "normal": {
                    "bg_color": arcade.color.DARK_GRAY if value != self.selected_difficulty else arcade.color.BLUE,
                    "border_color": arcade.color.WHITE,
                    "border_width": 2
                },
                "hover": {
                    "bg_color": arcade.color.GRAY if value != self.selected_difficulty else arcade.color.LIGHT_BLUE,
                    "border_color": arcade.color.WHITE,
                    "border_width": 2
                },
                "press": {
                    "bg_color": arcade.color.BLUE,
                    "border_color": arcade.color.WHITE,
                    "border_width": 2
                }
            }
            btn.on_click = lambda e, val=value: self.on_difficulty_select(val)
            difficulty_box.add(btn)
        main_box.add(difficulty_box)

        buttons_box = arcade.gui.UIBoxLayout(vertical=False, space_between=20)

        apply_button = arcade.gui.UIFlatButton(
            text="Применить",
            width=settings.BUTTON_WIDTH,
            height=settings.BUTTON_HEIGHT
        )
        apply_button.style = {
            "normal": {
                "bg_color": arcade.color.DARK_GREEN,
                "border_color": arcade.color.WHITE,
                "border_width": 2
            },
            "hover": {
                "bg_color": arcade.color.GREEN,
                "border_color": arcade.color.WHITE,
                "border_width": 2
            },
            "press": {
                "bg_color": arcade.color.DARK_GREEN,
                "border_color": arcade.color.WHITE,
                "border_width": 2
            }
        }
        apply_button.on_click = self.on_apply_click
        buttons_box.add(apply_button)

        cancel_button = arcade.gui.UIFlatButton(
            text="Отмена",
            width=settings.BUTTON_WIDTH,
            height=settings.BUTTON_HEIGHT
        )
        cancel_button.style = {
            "normal": {
                "bg_color": arcade.color.DARK_RED,
                "border_color": arcade.color.WHITE,
                "border_width": 2
            },
            "hover": {
                "bg_color": arcade.color.RED,
                "border_color": arcade.color.WHITE,
                "border_width": 2
            },
            "press": {
                "bg_color": arcade.color.DARK_RED,
                "border_color": arcade.color.WHITE,
                "border_width": 2
            }
        }
        cancel_button.on_click = self.on_cancel_click
        buttons_box.add(cancel_button)

        main_box.add(buttons_box)

        anchor_layout = arcade.gui.UIAnchorLayout()
        anchor_layout.add(
            child=main_box,
            anchor_x="center_x",
            anchor_y="center_y"
        )
        self.manager.add(anchor_layout)

    def on_difficulty_select(self, difficulty):
        self.selected_difficulty = difficulty
        self.manager.clear()
        self.setup_ui()

    def on_apply_click(self, event):
        if self.parent_view:
            self.parent_view.difficulty = self.selected_difficulty
        if self.window:
            self.window.show_view(self.parent_view)

    def on_cancel_click(self, event):
        if self.window:
            self.window.show_view(self.parent_view)

    def on_show_view(self):
        self.manager.enable()
        arcade.set_background_color(arcade.color.DARK_GRAY)

    def on_hide_view(self):
        self.manager.disable()

    def on_draw(self):
        self.clear()
        left, right = 0, self.width
        bottom, top = 0, self.height
        arcade.draw_lrbt_rectangle_filled(
            left, right, bottom, top, (0, 0, 0, 200))
        self.manager.draw()
