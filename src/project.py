import arcade


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

    class Game:
        SCREEN_WIDTH = 1024
        SCREEN_HEIGHT = 768
        TILE_SIZE = 64
        PLAYER_SPEED = 5
        TILESET_TILE_SIZE = 32

        MAP_WIDTH_MULTIPLIER = 3
        MAP_HEIGHT_MULTIPLIER = 3
        MIN_ROOM_SIZE = 4
        MAX_ROOM_SIZE = 10
        MIN_HALL_SIZE = 12
        MAX_HALL_SIZE = 20
        NUM_ROOMS = 40
        NUM_HALLS = 2
        SIDE_CORRIDOR_CHANCE = 0.4
        ROOMS_PER_SIDE_CORRIDOR = 3

    class Settings:
        RESOLUTIONS = [
            (1920, 1080),
            (1680, 1050),
            (1600, 900),
            (1440, 900),
            (1366, 768),
            (1280, 720),
            (1024, 768),
            (800, 600)
        ]

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
        DEFAULT_SOUNDS_FOLDER = "resources/sounds"
        DEFAULT_SOUND_VOLUME = 1.0
        DEFAULT_MUSIC_VOLUME = 1.0

        SETTINGS_PANEL_WIDTH = 800
        SETTINGS_PANEL_HEIGHT = 600
        BUTTON_WIDTH = 250
        BUTTON_HEIGHT = 50
        SLIDER_WIDTH = 300
        SLIDER_HEIGHT = 30
        LABEL_FONT_SIZE = 18
        BUTTON_FONT_SIZE = 16
