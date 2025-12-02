import arcade


class ProjectSettings:
    WINDOW_TITLE = "The Edges of House"
    FULLSCREEN = True
    BACKGROUND_COLOR = arcade.color.BLACK

    class StartWindow:
        TITLE_TEXT = "THE EDGES OF HOUSE"
        TITLE_FONT_SIZE = 48
        TITLE_WIDTH = 600
        TITLE_COLOR = arcade.color.WHITE
        TITLE_BOLD = True
        TITLE_BOTTOM_SPACING = 40

        BUTTON_WIDTH = 300
        BUTTON_HEIGHT = 60
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
