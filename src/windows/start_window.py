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

        self.setup_ui()

    def setup_ui(self):
        settings = ProjectSettings.StartWindow

        v_box = arcade.gui.UIBoxLayout(
            vertical=True,
            space_between=settings.BUTTON_SPACING
        )

        title_label = arcade.gui.UILabel(
            text=settings.TITLE_TEXT,
            text_color=settings.TITLE_COLOR,
            font_size=settings.TITLE_FONT_SIZE,
            bold=settings.TITLE_BOLD,
            width=settings.TITLE_WIDTH,
            align="center"
        )
        v_box.add(title_label)

        start_button = arcade.gui.UIFlatButton(
            text=settings.BUTTON_START_TEXT,
            width=settings.BUTTON_WIDTH,
            height=settings.BUTTON_HEIGHT
        )
        start_button.on_click = self.on_start_click
        v_box.add(start_button)

        settings_button = arcade.gui.UIFlatButton(
            text=settings.BUTTON_SETTINGS_TEXT,
            width=settings.BUTTON_WIDTH,
            height=settings.BUTTON_HEIGHT
        )
        settings_button.on_click = self.on_settings_click
        v_box.add(settings_button)

        exit_button = arcade.gui.UIFlatButton(
            text=settings.BUTTON_EXIT_TEXT,
            width=settings.BUTTON_WIDTH,
            height=settings.BUTTON_HEIGHT
        )
        exit_button.on_click = self.on_exit_click
        v_box.add(exit_button)

        anchor_layout = arcade.gui.UIAnchorLayout()
        anchor_layout.add(
            child=v_box,
            anchor_x="center_x",
            anchor_y="center_y"
        )
        self.manager.add(anchor_layout)

    def on_start_click(self, event):
        self.start_game = True

    def on_settings_click(self, event):
        self.show_settings = True

    def on_exit_click(self, event):
        arcade.exit()

    def on_draw(self):
        self.clear()
        self.manager.draw()

    def on_update(self, delta_time):
        pass
