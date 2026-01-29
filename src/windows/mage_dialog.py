import arcade
import arcade.gui

class MageDialog:
    def __init__(self, window):
        self.window = window
        self.manager = arcade.gui.UIManager()
        self.is_visible = False
        
        self.setup_ui()

    def setup_ui(self):
        # Создаем вертикальный макет для содержимого
        self.v_box = arcade.gui.UIBoxLayout(space_between=20)
        
        # Заголовок
        title_label = arcade.gui.UILabel(
            text="Маг",
            font_size=20,
            text_color=arcade.color.AMETHYST,
            bold=True
        )
        self.v_box.add(title_label)
        
        # Текст
        text_label = arcade.gui.UILabel(
            text="Здесь будет диалоговое окно",
            font_size=14,
            text_color=arcade.color.WHITE,
            width=300,
            multiline=True,
            align="center"
        )
        self.v_box.add(text_label)
        
        # Close button
        close_button = arcade.gui.UIFlatButton(
            text="Закрыть",
            width=150
        )
        self.v_box.add(close_button)
        
        # Assign click handler
        close_button.on_click = self.on_close_click
        
        # Create a widget to hold the v_box with a background
        # Wrapper for padding and background
        self.bg_wrapper = self.v_box.with_padding(all=20).with_background(color=arcade.color.DARK_SLATE_GRAY).with_border(color=arcade.color.WHITE)
        
        # Center the wrapper on the screen
        self.ui_anchor = arcade.gui.UIAnchorLayout()
        self.ui_anchor.add(child=self.bg_wrapper, anchor_x="center", anchor_y="center")
        self.manager.add(self.ui_anchor)

    def show(self):
        self.is_visible = True
        self.manager.enable()

    def hide(self):
        self.is_visible = False
        self.manager.disable()

    def on_close_click(self, event):
        self.hide()
        
    def draw(self):
        if self.is_visible:
            # Draw a dim background overlay
            arcade.draw_lrtb_rectangle_filled(
                0, self.window.width, self.window.height, 0,
                (0, 0, 0, 150)
            )
            self.manager.draw()
            
    def on_key_press(self, key, modifiers):
        if self.is_visible:
            if key == arcade.key.ESCAPE:
                self.hide()
                return True
        return False
        
    def on_mouse_press(self, x, y, button, modifiers):
        if self.is_visible:
            # Проверка клика вне диалогового окна
            # Примечание: rect доступен после компоновки
            if self.bg_wrapper.rect and not self.bg_wrapper.rect.collide_with_point(x, y):
                self.hide()
                return True
        return False
