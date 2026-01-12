import arcade
import arcade.gui
import os
import json
import math
from project import ProjectSettings
from utils import get_savegame_path


class GameStartDialog(arcade.View):
    DIFFICULTY_EASY = "easy"
    DIFFICULTY_MEDIUM = "medium"
    DIFFICULTY_HARD = "hard"

    def __init__(self):
        super().__init__()

        self.manager = arcade.gui.UIManager()
        self.manager.enable()

        self.selected_difficulty = self.DIFFICULTY_EASY
        self.load_save = False
        self.start_game = False
        self.transition_alpha = 0
        self.transitioning = False
        self.start_fx = 0
        self.start_button = None

        # Анимация выбора сложности
        self.difficulty_buttons = {}
        self.animation_time = 0.0
        self.selected_button_scale = 1.0

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
        print(f"Озвучка {status}")

    def on_next_click(self, event):
        """Обработка нажатия кнопки 'Дальше'"""
        print("Переход к следующей части истории")
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

        # Добавляем кнопки для озвучки и перехода
        story_box = arcade.gui.UIBoxLayout(vertical=False, space_between=10)

        # Кнопка включения озвучки
        voice_status = "Отключить озвучку" if getattr(
            ProjectSettings.Game, 'VOICE_ENABLED', True) else "Включить озвучку"
        voice_button = arcade.gui.UIFlatButton(
            text=voice_status,
            width=200,
            height=settings.BUTTON_HEIGHT
        )
        voice_button.style = {
            "normal": {
                "bg_color": arcade.color.DARK_BLUE,
                "border_color": arcade.color.WHITE,
                "border_width": 2
            },
            "hover": {
                "bg_color": arcade.color.BLUE,
                "border_color": arcade.color.WHITE,
                "border_width": 2
            },
            "press": {
                "bg_color": arcade.color.DARK_BLUE,
                "border_color": arcade.color.WHITE,
                "border_width": 2
            }
        }
        voice_button.on_click = self.on_voice_click
        story_box.add(voice_button)

        # Кнопка "Дальше" для пролистывания истории
        next_button = arcade.gui.UIFlatButton(
            text="Дальше",
            width=200,
            height=settings.BUTTON_HEIGHT
        )
        next_button.style = {
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
        next_button.on_click = self.on_next_click
        story_box.add(next_button)

        main_box.add(story_box)

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

        if not self.load_save:
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

            self.difficulty_buttons = {}
            for text, value in zip(difficulty_texts, difficulty_values):
                btn = arcade.gui.UIFlatButton(
                    text=text,
                    width=200,
                    height=settings.BUTTON_HEIGHT
                )
                is_selected = value == self.selected_difficulty
                btn.style = {
                    "normal": {
                        "bg_color": arcade.color.DARK_GRAY if not is_selected else arcade.color.BLUE,
                        "border_color": arcade.color.WHITE,
                        "border_width": 3 if is_selected else 2
                    },
                    "hover": {
                        "bg_color": arcade.color.GRAY if not is_selected else arcade.color.LIGHT_BLUE,
                        "border_color": arcade.color.WHITE,
                        "border_width": 3 if is_selected else 2
                    },
                    "press": {
                        "bg_color": arcade.color.BLUE,
                        "border_color": arcade.color.WHITE,
                        "border_width": 3
                    }
                }
                btn.on_click = lambda e, val=value: self.on_difficulty_select(
                    val)
                self.difficulty_buttons[value] = btn
                difficulty_box.add(btn)
            main_box.add(difficulty_box)

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

    def on_difficulty_select(self, difficulty):
        self.selected_difficulty = difficulty
        self.animation_time = 0.0  # Сброс анимации при выборе
        self.setup_ui()

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

        # Анимация выбранной кнопки сложности
        if self.difficulty_buttons and self.selected_difficulty in self.difficulty_buttons:
            selected_btn = self.difficulty_buttons[self.selected_difficulty]
            if hasattr(selected_btn, "rect") and selected_btn.rect:
                # Пульсация - изменение размера
                pulse = 1.0 + 0.05 * abs(math.sin(self.animation_time * 3.0))
                center_x = (selected_btn.rect.left +
                            selected_btn.rect.right) / 2
                center_y = (selected_btn.rect.bottom +
                            selected_btn.rect.top) / 2
                base_width = selected_btn.rect.right - selected_btn.rect.left
                base_height = selected_btn.rect.top - selected_btn.rect.bottom
                width = base_width * pulse
                height = base_height * pulse

                # Эффект свечения - несколько слоев с разной прозрачностью
                glow_alpha = int(
                    100 + 50 * abs(math.sin(self.animation_time * 2.0)))
                for i in range(3):
                    glow_offset = i * 6
                    glow_alpha_layer = max(0, glow_alpha - i * 30)
                    arcade.draw_lrbt_rectangle_outline(
                        center_x - width / 2 - glow_offset,
                        center_x + width / 2 + glow_offset,
                        center_y - height / 2 - glow_offset,
                        center_y + height / 2 + glow_offset,
                        (*arcade.color.CYAN[:3], glow_alpha_layer),
                        border_width=2 + i
                    )

                # Основной контур выбранной кнопки
                outline_alpha = int(
                    200 + 55 * abs(math.sin(self.animation_time * 2.5)))
                arcade.draw_lrbt_rectangle_outline(
                    selected_btn.rect.left - 3,
                    selected_btn.rect.right + 3,
                    selected_btn.rect.bottom - 3,
                    selected_btn.rect.top + 3,
                    (*arcade.color.CYAN[:3], outline_alpha),
                    border_width=4
                )

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
        # Обновление анимации выбора сложности
        self.animation_time += delta_time

        if self.start_fx > 0:
            self.start_fx = max(0, self.start_fx - delta_time)

        if self.start_game and self.transitioning:
            self.transition_alpha = min(
                255, self.transition_alpha + delta_time * 400)
            if self.transition_alpha >= 255 and self.window:
                from windows.loading_view import LoadingView
                loading_view = LoadingView(
                    difficulty=self.selected_difficulty,
                    load_save=self.load_save
                )
                self.window.show_view(loading_view)
