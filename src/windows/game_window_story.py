"""
Модуль для управления историей и диалогами
"""
import arcade
import arcade.gui


class GameWindowStory:
    """Класс-миксин для методов управления историей"""
    
    def draw_story_text(self):
        """Отрисовка текста истории"""
        if not self.current_story_line or not self.window:
            return

        # Рисуем подложку для текста
        bg_height = 100
        bg_y = self.window.height * 0.2
        arcade.draw_lrbt_rectangle_filled(
            0,
            self.window.width,
            bg_y - bg_height // 2,
            bg_y + bg_height // 2,
            (0, 0, 0, 150)
        )

        if self.current_story_text_object:
            self.current_story_text_object.draw()

    def setup_story_ui(self):
        """Настройка UI для отображения истории с кнопкой Далее"""
        self.story_manager.clear()

        # Создаем UI элементы для отображения истории
        main_box = arcade.gui.UIBoxLayout(vertical=True, space_between=30)

        # Добавляем текст истории
        text_label = arcade.gui.UILabel(
            text="",
            font_size=18,
            text_color=arcade.color.WHITE,
            width=self.window.width * 0.8,
            height=100,
            multiline=True,
            align="center"
        )
        main_box.add(text_label)

        # Добавляем пустое пространство
        spacer = arcade.gui.UISpace(
            width=self.window.width * 0.8,
            height=50
        )
        main_box.add(spacer)

        # Кнопка "Далее"
        next_button = arcade.gui.UIFlatButton(
            text="Далее",
            width=200,
            height=50
        )
        next_button.style = {
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
                "bg_color": arcade.color.LIGHT_BLUE,
                "border_color": arcade.color.WHITE,
                "border_width": 2
            }
        }
        next_button.on_click = self.on_next_click
        main_box.add(next_button)

        anchor_layout = arcade.gui.UIAnchorLayout()
        anchor_layout.add(
            child=main_box,
            anchor_x="center_x",
            anchor_y="center_y"
        )
        self.story_manager.add(anchor_layout)

    def on_next_click(self, event):
        """Обработка нажатия кнопки 'Далее'"""
        # Пропускаем текущую строку истории
        self.current_story_line = None
        self.current_story_text_object = None
        self.story_line_timer = 0.0

        # Проверяем, есть ли еще строки истории
        if not self.story_lines:
            # Если строк больше нет, скрываем UI истории
            self.story_manager.disable()

    def toggle_story_ui(self, show):
        """Показать или скрыть UI истории"""
        if show:
            self.story_manager.enable()
        else:
            self.story_manager.disable()

    def display_story_text(self):
        """Инициализирует текст истории"""
        self.story_lines = [
            "Вы спускаетесь в темное подземелье...",
            "Впереди вас ждут опасности и тайны.",
            "Будьте осторожны!"
        ]
        if self.story_lines:
            self.current_story_line = self.story_lines.pop(0)
            self.story_line_timer = self.story_display_duration
