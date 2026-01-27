import arcade
import arcade.gui
import os
from project import ProjectSettings
from utils import get_savegame_path


class GameStartDialog(arcade.View):
    DIFFICULTY_EASY = "easy"  # Only easy difficulty is available

    def __init__(self):
        super().__init__()

        self.manager = arcade.gui.UIManager()
        self.manager.enable()

        self.selected_difficulty = self.DIFFICULTY_EASY  # Always easy
        self.load_save = False
        self.start_game = False
        self.transition_alpha = 0
        self.transitioning = False
        self.start_fx = 0
        self.start_button = None

        self.setup_ui()

    def on_voice_click(self, event):
        """Обработка нажатия кнопки включения озвучки"""
        # Переключение состояния озвучки
        from project import ProjectSettings
        ProjectSettings.Game.VOICE_ENABLED = not getattr(
            ProjectSettings.Game, 'VOICE_ENABLED', True)

        # Обновление текста кнопки в зависимости от состояния
        if hasattr(self, 'manager'):
            self.manager.clear()
            self.setup_ui()

        status = "включена" if getattr(
            ProjectSettings.Game, 'VOICE_ENABLED', True) else "отключена"
        # print(f"Озвучка {status}")

    def on_next_click(self, event):
        """Обработка нажатия кнопки 'Дальше'"""
        # print("Переход к следующей части истории")
        # Здесь можно добавить функционал пролистывания истории

    def setup_ui(self):
        self.manager.clear()
        settings = ProjectSettings.Settings

        main_box = arcade.gui.UIBoxLayout(vertical=True, space_between=15)

        title_label = arcade.gui.UILabel(
            text="НАЧАТЬ ИГРУ",
            font_size=32,
            text_color=arcade.color.WHITE,
            width=settings.SETTINGS_PANEL_WIDTH,
            align="center"
        )
        main_box.add(title_label)

        pass

        save_exists = os.path.exists(get_savegame_path())

        if save_exists:
            game_mode_label = arcade.gui.UILabel(
                text="Режим игры:",
                font_size=settings.LABEL_FONT_SIZE,
                text_color=arcade.color.WHITE,
                width=settings.SETTINGS_PANEL_WIDTH
            )
            main_box.add(game_mode_label)

            game_mode_box = arcade.gui.UIBoxLayout(
                vertical=False, space_between=10)

            self.new_game_btn = arcade.gui.UIFlatButton(
                text="Новая игра",
                width=200,
                height=settings.BUTTON_HEIGHT
            )
            self.update_game_mode_button_styles()
            self.new_game_btn.on_click = lambda e: self.on_game_mode_select(
                False)
            game_mode_box.add(self.new_game_btn)

            self.load_game_btn = arcade.gui.UIFlatButton(
                text="Загрузить сохранение",
                width=200,
                height=settings.BUTTON_HEIGHT
            )
            self.update_game_mode_button_styles()
            self.load_game_btn.on_click = lambda e: self.on_game_mode_select(
                True)
            game_mode_box.add(self.load_game_btn)

            main_box.add(game_mode_box)

        # Difficulty selection removed - only easy difficulty is available

        buttons_box = arcade.gui.UIBoxLayout(vertical=False, space_between=20)

        start_button = arcade.gui.UIFlatButton(
            text="Начать",
            width=settings.BUTTON_WIDTH,
            height=settings.BUTTON_HEIGHT
        )
        self.start_button = start_button
        start_button.style = {
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
        start_button.on_click = self.on_start_click
        buttons_box.add(start_button)

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

    def update_game_mode_button_styles(self):
        if hasattr(self, 'new_game_btn') and hasattr(self, 'load_game_btn'):
            self.new_game_btn.style = {
                "normal": {
                    "bg_color": arcade.color.DARK_GRAY if self.load_save else arcade.color.BLUE,
                    "border_color": arcade.color.WHITE,
                    "border_width": 2
                },
                "hover": {
                    "bg_color": arcade.color.GRAY if self.load_save else arcade.color.LIGHT_BLUE,
                    "border_color": arcade.color.WHITE,
                    "border_width": 2
                },
                "press": {
                    "bg_color": arcade.color.BLUE,
                    "border_color": arcade.color.WHITE,
                    "border_width": 2
                }
            }
            self.load_game_btn.style = {
                "normal": {
                    "bg_color": arcade.color.DARK_GRAY if not self.load_save else arcade.color.BLUE,
                    "border_color": arcade.color.WHITE,
                    "border_width": 2
                },
                "hover": {
                    "bg_color": arcade.color.GRAY if not self.load_save else arcade.color.LIGHT_BLUE,
                    "border_color": arcade.color.WHITE,
                    "border_width": 2
                },
                "press": {
                    "bg_color": arcade.color.BLUE,
                    "border_color": arcade.color.WHITE,
                    "border_width": 2
                }
            }

    def on_game_mode_select(self, load_save):
        self.load_save = load_save
        if hasattr(self, 'new_game_btn') and hasattr(self, 'load_game_btn'):
            self.update_game_mode_button_styles()
        else:
            self.manager.clear()
            self.setup_ui()

    # Difficulty selection removed - always uses easy difficulty

    def on_start_click(self, event):
        self.start_game = True
        self.transitioning = True
        self.transition_alpha = 0
        self.start_fx = 0.2

    def on_cancel_click(self, event):
        if self.window:
            from windows.start_window import StartWindow
            start_view = StartWindow()
            self.window.show_view(start_view)

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

        # Difficulty selection animation removed

        if self.start_button and self.start_fx > 0 and hasattr(self.start_button, "rect"):
            alpha = int(max(0, min(255, 255 * (self.start_fx / 0.2))))
            arcade.draw_lrbt_rectangle_outline(
                self.start_button.rect.left,
                self.start_button.rect.right,
                self.start_button.rect.bottom,
                self.start_button.rect.top,
                (*arcade.color.WHITE[:3], alpha),
                border_width=3
            )
        if self.transitioning:
            alpha = int(self.transition_alpha)
            arcade.draw_lrbt_rectangle_filled(0, self.width, 0,
                                              self.height, (0, 0, 0, alpha))

    def on_update(self, delta_time):
        if self.start_fx > 0:
            self.start_fx = max(0, self.start_fx - delta_time)

        if self.start_game and self.transitioning:
            self.transition_alpha = min(
                255, self.transition_alpha + delta_time * 400)
            if self.transition_alpha >= 255 and self.window:
                from windows.loading_view import LoadingView
                from project import ProjectSettings
                # Always use easy difficulty
                loading_view = LoadingView(
                    difficulty=ProjectSettings.Game.DIFFICULTY_EASY,
                    load_save=self.load_save
                )
                self.window.show_view(loading_view)
