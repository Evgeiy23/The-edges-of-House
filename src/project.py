import arcade
import os


class ProjectSettings:
    WINDOW_TITLE = "The Edges of House"
    FULLSCREEN = True
    BACKGROUND_COLOR = arcade.color.BLACK

    class StartWindow:
        BACKGROUND_IMAGE = "resources/background.jpg"

        TITLE_TEXT = "THE EDGES OF HOUSE"
        TITLE_FONT_SIZE = 48
        TITLE_WIDTH = 600
        TITLE_COLOR = arcade.color.WHITE
        TITLE_SHADOW_COLOR = arcade.color.BLACK
        TITLE_BOLD = True
        TITLE_BOTTOM_SPACING = 40
        TITLE_TOP_OFFSET = 100

        BUTTON_WIDTH = 300
        BUTTON_HEIGHT = 70
        BUTTON_FONT_SIZE = 24
        BUTTON_SPACING = 20

        BUTTON_START_TEXT = "Начать игру"
        BUTTON_SETTINGS_TEXT = "Настройки"
        BUTTON_EXIT_TEXT = "Выйти из игры"

        SETTINGS_TITLE_TEXT = "Настройки игры"
        SETTINGS_CLOSE_TEXT = "Закрыть"
        SETTINGS_PANEL_WIDTH = 700
        SETTINGS_PANEL_HEIGHT = 400

    class Game:
        SCREEN_WIDTH = 1024
        SCREEN_HEIGHT = 768
        TILE_SIZE = 64
        PLAYER_SPEED = 5
        TILESET_TILE_SIZE = 32
        FRAME_LIMIT_OPTIONS = ["unlimited", "240",
                               "165", "144", "120", "60", "vsync"]
        DEFAULT_FRAME_LIMIT = "240"

        DIFFICULTY_EASY = "easy"
        DIFFICULTY_MEDIUM = "medium"
        DIFFICULTY_HARD = "hard"

        MAP_WIDTH_MULTIPLIER = 4
        MAP_HEIGHT_MULTIPLIER = 4
        MIN_ROOM_SIZE = 4
        MAX_ROOM_SIZE = 10
        MIN_HALL_SIZE = 12
        MAX_HALL_SIZE = 20
        NUM_ROOMS = 40
        NUM_HALLS = 2
        SIDE_CORRIDOR_CHANCE = 0.4
        ROOMS_PER_SIDE_CORRIDOR = 3

    class Settings:
        WINDOW_MODE_FULLSCREEN = "fullscreen"
        WINDOW_MODE_FULLSCREEN_WINDOWED = "fullscreen_windowed"
        WINDOW_MODE_WINDOWED = "windowed"
        WINDOW_MODES = [
            WINDOW_MODE_FULLSCREEN,
            WINDOW_MODE_FULLSCREEN_WINDOWED,
            WINDOW_MODE_WINDOWED
        ]

        DEFAULT_RESOLUTION_INDEX = 0
        DEFAULT_WINDOW_MODE = WINDOW_MODE_FULLSCREEN
        DEFAULT_SOUNDS_FOLDER = os.path.join(os.path.dirname(
            os.path.dirname(__file__)), "music")
        DEFAULT_SOUND_VOLUME = 1.0
        DEFAULT_MUSIC_VOLUME = 1.0
        DEFAULT_FRAME_LIMIT = "240"

        SETTINGS_PANEL_WIDTH = 800
        SETTINGS_PANEL_HEIGHT = 600
        BUTTON_WIDTH = 250
        BUTTON_HEIGHT = 50
        SLIDER_WIDTH = 300
        SLIDER_HEIGHT = 30
        LABEL_FONT_SIZE = 18
        BUTTON_FONT_SIZE = 16
