import arcade
import arcade.gui
from project import ProjectSettings


class StartWindow(arcade.Window):
    def __init__(self):
        super().__init__(
            fullscreen=ProjectSettings.FULLSCREEN,
            title=ProjectSettings.WINDOW_TITLE
        )

        self.screen_width = self.width
        self.screen_height = self.height

        self.manager = arcade.gui.UIManager()
        self.manager.enable()

        self.start_game = False
        self.show_settings = False

        arcade.set_background_color(ProjectSettings.BACKGROUND_COLOR)

        self.title_x = 0
        self.title_y = 0

        self.background_list = arcade.SpriteList()
        try:
            background_sprite = arcade.Sprite(
                ProjectSettings.StartWindow.BACKGROUND_IMAGE)
            background_sprite.center_x = self.screen_width // 2
            background_sprite.center_y = self.screen_height // 2
            scale_x = self.screen_width / background_sprite.width
            scale_y = self.screen_height / background_sprite.height
            background_sprite.scale = max(scale_x, scale_y)
            self.background_list.append(background_sprite)
        except:
            pass

        self.setup_ui()

    def setup_ui(self):
        settings = ProjectSettings.StartWindow

        v_box = arcade.gui.UIBoxLayout(
            vertical=True,
            space_between=settings.BUTTON_SPACING
        )

        start_button = arcade.gui.UIFlatButton(
            text="",
            width=settings.BUTTON_WIDTH,
            height=settings.BUTTON_HEIGHT
        )
        start_button.on_click = self.on_start_click
        v_box.add(start_button)

        settings_button = arcade.gui.UIFlatButton(
            text="",
            width=settings.BUTTON_WIDTH,
            height=settings.BUTTON_HEIGHT
        )
        settings_button.on_click = self.on_settings_click
        v_box.add(settings_button)

        exit_button = arcade.gui.UIFlatButton(
            text="",
            width=settings.BUTTON_WIDTH,
            height=settings.BUTTON_HEIGHT
        )
        exit_button.on_click = self.on_exit_click
        v_box.add(exit_button)

        self.buttons = [start_button, settings_button, exit_button]
        self.button_texts = [
            settings.BUTTON_START_TEXT,
            settings.BUTTON_SETTINGS_TEXT,
            settings.BUTTON_EXIT_TEXT
        ]

        anchor_layout = arcade.gui.UIAnchorLayout()
        anchor_layout.add(
            child=v_box,
            anchor_x="center_x",
            anchor_y="center_y"
        )
        self.manager.add(anchor_layout)

        self.title_x = self.screen_width // 2
        self.title_y = self.screen_height // 2 + \
            settings.TITLE_TOP_OFFSET + 150

    def on_start_click(self, event):
        self.start_game = True

    def on_settings_click(self, event):
        self.show_settings = True

    def on_exit_click(self, event):
        arcade.exit()

    def on_draw(self):
        self.clear()

        self.background_list.draw()

        settings = ProjectSettings.StartWindow

        shadow_offset = 3
        arcade.draw_text(
            settings.TITLE_TEXT,
            self.title_x + shadow_offset,
            self.title_y - shadow_offset,
            settings.TITLE_SHADOW_COLOR,
            settings.TITLE_FONT_SIZE,
            width=settings.TITLE_WIDTH,
            align="center",
            bold=settings.TITLE_BOLD,
            anchor_x="center",
            anchor_y="center"
        )

        arcade.draw_text(
            settings.TITLE_TEXT,
            self.title_x,
            self.title_y,
            settings.TITLE_COLOR,
            settings.TITLE_FONT_SIZE,
            width=settings.TITLE_WIDTH,
            align="center",
            bold=settings.TITLE_BOLD,
            anchor_x="center",
            anchor_y="center"
        )

        self.manager.draw()

        for button, text in zip(self.buttons, self.button_texts):
            if hasattr(button, 'rect'):
                button_x = button.rect.center_x
                button_y = button.rect.center_y
                arcade.draw_text(
                    text,
                    button_x,
                    button_y,
                    arcade.color.WHITE,
                    settings.BUTTON_FONT_SIZE,
                    anchor_x="center",
                    anchor_y="center",
                    bold=True
                )

    def on_update(self, delta_time):
        pass
