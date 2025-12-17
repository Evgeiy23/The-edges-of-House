import arcade
import os
import glob


class Player:
    def __init__(self, tile_size):
        self.tile_size = tile_size
        self.pos = [0, 0]
        self.draw_pos = [0.0, 0.0]
        self.facing = 'front'
        self.state = 'idle'
        self.last_move_direction = None
        self.sprite = arcade.Sprite()
        self.sprite.center_x = 0
        self.sprite.center_y = 0
        self.sprite.scale = 1.0
        self.sprite_list = arcade.SpriteList()
        self.sprite_list.append(self.sprite)
        self.is_attacking = False
        self.attack_timer = 0.0
        self.attack_duration = 0.5
        self.animations = {}
        self.current_animation_frames = []
        self.current_frame_index = 0
        self.animation_timer = 0.0
        self.animation_speed = 0.1
        self._load_animations()
        self._update_animation()

    def _load_animations(self):
        base_path = "resources/character"
        directions = ['Front', 'Back', 'Left', 'Right']
        actions = {
            'idle': 'Idle',
            'idle_blinking': 'Idle Blinking',
            'walking': 'Walking',
            'running': 'Running',
            'attacking': 'Attacking',
            'hurt': 'Hurt',
            'dying': 'Dying'
        }

        for direction in directions:
            for action_key, action_name in actions.items():
                if action_key == 'dying':
                    folder_path = os.path.join(base_path, action_name)
                else:
                    folder_path = os.path.join(
                        base_path, f"{direction} - {action_name}")

                if os.path.exists(folder_path):
                    pattern = os.path.join(folder_path, "*.png")
                    files = sorted(glob.glob(pattern))

                    if files:
                        textures = []
                        for file_path in files:
                            texture = arcade.load_texture(file_path)
                            textures.append(texture)

                        key = f"{direction.lower()}_{action_key}"
                        self.animations[key] = textures

                        if self.sprite.scale == 1.0 and textures:
                            texture_width = textures[0].width
                            self.sprite.scale = self.tile_size / texture_width

    def _get_animation_key(self):
        if self.state == 'dying':
            return 'dying'

        direction = self.facing.lower()
        state_key = self.state

        return f"{direction}_{state_key}"

    def _update_animation(self):
        animation_key = self._get_animation_key()

        if animation_key in self.animations:
            self.current_animation_frames = self.animations[animation_key]
            self.current_frame_index = 0
            self.animation_timer = 0.0

            if self.current_animation_frames:
                self.sprite.texture = self.current_animation_frames[0]
        else:
            if self.animations:
                first_key = list(self.animations.keys())[0]
                self.current_animation_frames = self.animations[first_key]
                if self.current_animation_frames:
                    self.sprite.texture = self.current_animation_frames[0]

    def update_animation(self, delta_time):
        if self.is_attacking:
            self.attack_timer += delta_time
            if self.attack_timer >= self.attack_duration:
                self.is_attacking = False
                self.attack_timer = 0.0
                self.state = 'idle'
                self._update_animation()

        if not self.current_animation_frames:
            return

        self.animation_timer += delta_time

        if self.animation_timer >= self.animation_speed:
            self.animation_timer = 0.0
            self.current_frame_index = (
                self.current_frame_index + 1) % len(self.current_animation_frames)
            self.sprite.texture = self.current_animation_frames[self.current_frame_index]

    def update_draw_pos(self):
        left = self.pos[0] * self.tile_size
        bottom = self.pos[1] * self.tile_size
        self.sprite.left = left
        self.sprite.bottom = bottom

    def draw(self):
        self.sprite_list.draw()

    def move(self, dx, dy):
        self.pos[0] += dx
        self.pos[1] += dy

        if dx != 0 or dy != 0:
            self.last_move_direction = (dx, dy)

        self.update_draw_pos()

    def set_pos(self, x, y):
        self.pos[0] = x
        self.pos[1] = y
        self.update_draw_pos()

    def set_state(self, state):
        if self.state != state:
            self.state = state
            self._update_animation()

    def attack(self):
        if not self.is_attacking:
            self.is_attacking = True
            self.attack_timer = 0.0
            self.state = 'attacking'
            self._update_animation()
