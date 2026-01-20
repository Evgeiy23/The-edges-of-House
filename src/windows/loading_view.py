import arcade
import os
import pyglet
import random
import threading
import time
import traceback
import math
import json
import platform
import subprocess

from project import ProjectSettings
from game.logic.map.storage import generate_and_store_map
from windows.game_window import GameWindow
from utils import get_config_path


class LoadingView(arcade.View):
    def __init__(self, difficulty=None, load_save=False, map_name="current"):
        super().__init__()
        self.difficulty = difficulty or ProjectSettings.Game.DIFFICULTY_EASY
        self.load_save = load_save
        self.map_name = map_name

        self.status = "pending"
        self.error = None
        self.progress_text = "Идет генерация карты"

        self.map_payload = None
        self.spawn_corner = None

        self._worker_thread = None
        self._switch_scheduled = False
        self._started_at = time.time()
        self._switch_when_done = False

        # Initialize story UI manager
        self.story_manager = arcade.gui.UIManager()

        self.story_lines = []
        self.current_story_line = None
        self.current_story_text = None
        self.story_line_timer = 0.0
        self.story_line_duration = 10.0
        self.story_audio_player = None
        self.pending_audio_path = None
        self.story_initialized = False
        self.show_start_prompt = False
        self.prompt_display_timer = 0.0
        
        # Новые поля для аудиофайлов
        self.story_audio_files = []
        self.current_story_audio_index = 0
        self.afplay_process = None
        
        self.sound_volume = 1.0
        self.load_settings()
        self._spinner_angle = 0.0
        self._spinner_speed = 180.0
        self._overlay_start_time = time.time()
        self._enter_loading_active = False
        self._enter_loading_timer = 0.0
        self._enter_loading_duration = 3.0

    def load_settings(self):
        try:
            config_path = get_config_path()
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    self.sound_volume = config.get("sound_volume", 1.0)
        except Exception:
            pass

    def setup_story_ui(self):
        """Setup UI for story display with 'Next' button"""
        self.story_manager.clear()

        # Create UI elements for story display
        main_box = arcade.gui.UIBoxLayout(vertical=True, space_between=30)

        # Empty label for story text (text will be drawn separately)
        text_label = arcade.gui.UILabel(
            text="",
            font_size=18,
            text_color=arcade.color.WHITE,
            width=self.width * 0.8 if hasattr(self, 'width') else 600,
            height=100,
            multiline=True,
            align="center"
        )
        main_box.add(text_label)

        # Spacer for better layout
        spacer = arcade.gui.UISpace(
            width=self.width * 0.8 if hasattr(self, 'width') else 600,
            height=50
        )
        main_box.add(spacer)

        # Next button
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
        self.story_manager.disable()  # Initially disabled, will be enabled when showing story

    def on_next_click(self, event):
        """Handle 'Next' button click"""
        # Move to next story line or show start prompt
        self.current_story_line = self.story_lines.pop(
            0) if self.story_lines else None
        self.current_story_audio_index += 1
        self.story_line_timer = self.story_line_duration if self.current_story_line else 0.0
        if self.current_story_line:
            self.play_story_audio_line(self.current_story_audio_index)
        else:
            self.show_start_prompt = True
            # Disable story UI when no more story lines
            self.story_manager.disable()

    def on_show_view(self):
        arcade.set_background_color(ProjectSettings.BACKGROUND_COLOR)
        # Initially disable the story UI until story is ready to be shown
        self.story_manager.disable()
        self._start_worker()

    def _start_worker(self):
        if self._worker_thread:
            return
        self._worker_thread = threading.Thread(
            target=self._generate_map_worker, daemon=True)
        self._worker_thread.start()

    def _generate_map_worker(self):
        try:
            if self.load_save:
                self.status = "done"
                return

            game_cfg = ProjectSettings.Game
            map_width, map_height = GameWindow.compute_map_dimensions(
                1, game_cfg)

            self.spawn_corner = random.choice(
                ["bottom_left", "bottom_right"])
            self.progress_text = "Идет генерация карты"

            self.map_payload = generate_and_store_map(
                map_width, map_height, game_cfg, self.spawn_corner, map_name=self.map_name)
            self.status = "done"
        except Exception as e:
            self.error = str(e)
            traceback.print_exc()
            self.status = "error"

    def on_draw(self):
        self.clear()

        if self._enter_loading_active:
            w, h = self.width, self.height
            arcade.draw_lrbt_rectangle_filled(0, w, 0, h, (0, 0, 0, 180))
            text = "Генерация карты..."
            r = int(min(w, h) * 0.06)
            text_y = h // 2 + int(r * 0.8)
            arcade.draw_text(text, w // 2, text_y, arcade.color.WHITE, 28, anchor_x="center", anchor_y="center", bold=True)
            r = int(min(w, h) * 0.06)
            cx, cy = w // 2, h // 2 - r * 2
            arcade.draw_arc_outline(cx, cy, r * 2, r * 2, arcade.color.DARK_GRAY, 0, 360, 6)
            sa = self._spinner_angle
            arcade.draw_arc_outline(cx, cy, r * 2, r * 2, arcade.color.LIGHT_BLUE, sa, sa + 120, 8)
            return

        if self.error:
            msg = f"Ошибка генерации: {self.error}"
            arcade.draw_text(msg, self.width // 2, self.height // 2, arcade.color.WHITE, 24,
                             anchor_x="center", anchor_y="center", align="center",
                             width=int(self.width * 0.8), multiline=True)
            return

        if self.status == "pending" or self.status == "generating":
            w, h = self.width, self.height
            arcade.draw_lrbt_rectangle_filled(0, w, 0, h, (0, 0, 0, 180))
            text = "Генерация карты..."
            r = int(min(w, h) * 0.06)
            text_y = h // 2 + int(r * 0.8)
            arcade.draw_text(text, w // 2, text_y, arcade.color.WHITE, 28, anchor_x="center", anchor_y="center", bold=True)
            r = int(min(w, h) * 0.06)
            cx, cy = w // 2, h // 2 - r * 2
            arcade.draw_arc_outline(cx, cy, r * 2, r * 2, arcade.color.DARK_GRAY, 0, 360, 6)
            sa = self._spinner_angle
            arcade.draw_arc_outline(cx, cy, r * 2, r * 2, arcade.color.LIGHT_BLUE, sa, sa + 120, 8)
            return

        if self.status == "done":
            if self.current_story_line:
                bg_h = 160
                center_y = self.height // 2
                arcade.draw_lrbt_rectangle_filled(
                    0, self.width, center_y - bg_h // 2, center_y +
                    bg_h // 2, (0, 0, 0, 180)
                )
                arcade.draw_text(
                    self.current_story_line,
                    self.width // 2,
                    center_y,
                    arcade.color.WHITE,
                    22,
                    anchor_x="center",
                    anchor_y="center",
                    align="center",
                    width=int(self.width * 0.85),
                    multiline=True,
                )
                # Draw the story UI with the next button
                self.story_manager.draw()
                # Corner ESC notification (top-right)
                notice = "Нажмите ESC, чтобы пропустить предысторию"
                margin = 20
                arcade.draw_text(
                    notice,
                    self.width - margin,
                    self.height - margin,
                    arcade.color.LIGHT_GRAY,
                    16,
                    anchor_x="right",
                    anchor_y="top",
                    align="right",
                )
            elif self.show_start_prompt:
                # Экран заставки с текстом "Нажмите ENTER чтобы продолжить"
                # Добавляем эффект мигания текста
                alpha = int(180 + 75 * abs(math.sin(self.prompt_display_timer * 2.0)))
                arcade.draw_text(
                    "Нажмите ENTER чтобы продолжить",
                    self.width // 2,
                    self.height // 2,
                    (*arcade.color.LIGHT_GREEN[:3], alpha),
                    28,
                    anchor_x="center",
                    anchor_y="center",
                    bold=True
                )
                # Добавляем подсказку о пропуске истории
                if hasattr(self, 'story_lines') and len(self.story_lines) > 0:
                    skip_text = "Нажмите ESCAPE чтобы пропустить предысторию"
                    arcade.draw_text(
                        skip_text,
                        self.width // 2,
                        self.height // 2 - 50,
                        (*arcade.color.GRAY[:3], alpha // 2),
                        18,
                        anchor_x="center",
                        anchor_y="center",
                    )

    def on_update(self, delta_time):
        if self.story_audio_player and hasattr(self.story_audio_player, 'time'):
            # Debug: print playback time occasionally
            if int(time.time() * 10) % 20 == 0:
                 pass # print(f"Playback time: {self.story_audio_player.time}")

        if self.pending_audio_path:
            try:
                if os.path.exists(self.pending_audio_path):
                    if self.story_audio_player:
                        try:
                            if hasattr(self.story_audio_player, "pause"):
                                self.story_audio_player.pause()
                            arcade.stop_sound(self.story_audio_player)
                        except:
                            pass
                    sound = arcade.load_sound(self.pending_audio_path)
                    if sound:
                        self.story_audio_player = arcade.play_sound(sound, volume=self.sound_volume)
                    self.pending_audio_path = None
            except Exception:
                self.pending_audio_path = None

        # Переход в игру только после завершения генерации
        if self._switch_when_done and self.status == "done" and self.window:
            self._switch_when_done = False
            self._switch_scheduled = False
            next_view = GameWindow(
                difficulty=ProjectSettings.Game.DIFFICULTY_EASY,
                load_save=self.load_save,
                map_payload=self.map_payload,
                map_name=self.map_name,
                spawn_corner=self.spawn_corner,
                level_override=1
            )
            self.window.show_view(next_view)

        if self.status == "done":
            if not self.story_initialized:
                self._init_story()
                self.story_initialized = True
            
            if not self.story_lines and not self.current_story_line:
                self.show_start_prompt = True
                # Increment timer when prompt is shown
                self.prompt_display_timer += delta_time
            else:
                self._update_story(delta_time)

        if self.story_manager:
            self.story_manager.on_update(delta_time)
        if self.status in ("pending", "generating") or self._enter_loading_active:
            self._spinner_angle = (self._spinner_angle + self._spinner_speed * delta_time) % 360.0
        if self._enter_loading_active and self.window:
            self._enter_loading_timer += delta_time
            if self._enter_loading_timer >= self._enter_loading_duration:
                self._enter_loading_active = False
                self._enter_loading_timer = 0.0
                next_view = GameWindow(
                    difficulty=ProjectSettings.Game.DIFFICULTY_EASY,
                    load_save=self.load_save,
                    map_payload=self.map_payload,
                    map_name=self.map_name,
                    spawn_corner=self.spawn_corner,
                    level_override=1
                )
                self.window.show_view(next_view)

    def on_key_press(self, symbol, modifiers):
        if symbol == arcade.key.ESCAPE and self.status == "done":
            if self.current_story_line or (hasattr(self, 'story_lines') and len(self.story_lines) > 0):
                if self.story_audio_player:
                    try:
                        if hasattr(self.story_audio_player, "pause"):
                            self.story_audio_player.pause()
                        arcade.stop_sound(self.story_audio_player)
                    except:
                        pass
                    self.story_audio_player = None
                if self.afplay_process:
                    try:
                        self.afplay_process.terminate()
                        self.afplay_process = None
                    except:
                        pass
                self.current_story_line = None
                if hasattr(self, 'story_lines'):
                    self.story_lines = []
                self.show_start_prompt = True
                self.story_manager.disable()
                return
        if symbol == arcade.key.ENTER:
            if self.status == "done" and self.window:
                if hasattr(self, 'story_start_time') and time.time() - self.story_start_time < 1.5:
                    return
                self.story_manager.disable()
                self.current_story_line = None
                self.show_start_prompt = False
                self._enter_loading_active = True
                self._enter_loading_timer = 0.0
                return
            self.status = "generating"
            self.progress_text = "Идет генерация карты"
            if self.story_audio_player:
                try:
                    if hasattr(self.story_audio_player, "pause"):
                        self.story_audio_player.pause()
                    arcade.stop_sound(self.story_audio_player)
                except:
                    pass
                self.story_audio_player = None
            if self.afplay_process:
                try:
                    self.afplay_process.terminate()
                    self.afplay_process = None
                except:
                    pass
            self.current_story_line = None
            self.show_start_prompt = False
            self.story_manager.disable()
            if not self._switch_scheduled:
                self._switch_scheduled = True
                self._switch_when_done = True

    def _init_story(self):
        text = (
            "Герой — Элиас, скромный картограф и алхимик из приграничного городка Валемар. "
            "Его жена, Лира, талантливая травница, тяжело заболела «Каменной Чумой» — "
            "болезнью, которая постепенно превращает плоть в холодный, инертный камень. "
            "Все известные методы лечения оказались бессильны.\n"
            "В отчаянии Элиас находит старую карту, нарисованную его же рукой много лет назад, "
            "но места на ней он не помнит. Карта ведёт в заброшенное подземелье под Валемаром, "
            "где, по легенде, хранится Сердце Камня — источник энергии, породивший Каменную Чуму.\n"
            "Элиас спускается в подземелье, надеясь уничтожить источник и спасти Лиру."
        )
        self.story_lines = [line.strip()
                            for line in text.split("\n") if line.strip()]
        
        # Загружаем все аудиофайлы из папки story_audio, отсортированные по имени
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        story_dir = os.path.join(root_dir, "music", "story_audio")
        if os.path.isdir(story_dir):
            files = [os.path.join(story_dir, f) for f in os.listdir(story_dir) if f.lower().endswith(".mp3")]
            files.sort()
            self.story_audio_files = files
        else:
            self.story_audio_files = []
        
        self.current_story_line = self.story_lines.pop(
            0) if self.story_lines else None
        self.current_story_audio_index = 0
        self.story_line_timer = self.story_line_duration
        self.story_start_time = time.time() # Track when story started
        
        if self.current_story_line:
            self.play_story_audio_line(self.current_story_audio_index)
            # Enable story UI when there's a story line to show
            self.story_manager.enable()

    def _update_story(self, delta_time):
        if self.current_story_line:
            self.story_line_timer -= delta_time
            if self.story_line_timer <= 0:
                self.current_story_line = self.story_lines.pop(
                    0) if self.story_lines else None
                self.current_story_audio_index += 1
                self.story_line_timer = self.story_line_duration if self.current_story_line else 0.0
                if self.current_story_line:
                    self.play_story_audio_line(self.current_story_audio_index)
                else:
                    self.show_start_prompt = True

    def play_story_audio_line(self, audio_index):
        """Воспроизводит аудиофайл для конкретной линии"""
        if 0 <= audio_index < len(self.story_audio_files):
            audio_path = self.story_audio_files[audio_index]
            if os.path.exists(audio_path):
                try:
                    # Останавливаем предыдущее аудио
                    if self.story_audio_player:
                        try:
                            if hasattr(self.story_audio_player, "pause"):
                                self.story_audio_player.pause()
                            arcade.stop_sound(self.story_audio_player)
                        except:
                            pass
                        self.story_audio_player = None

                    # Останавливаем afplay если запущен
                    if self.afplay_process:
                        try:
                            self.afplay_process.terminate()
                            self.afplay_process = None
                        except:
                            pass
                    
                    duration = 0
                    is_mp3 = audio_path.lower().endswith('.mp3')
                    
                    # 1. Сначала пробуем Pyglet (для корректного определения длительности)
                    try:
                        # Используем streaming=False как в успешном тесте
                        media = pyglet.media.load(audio_path, streaming=False)
                        if hasattr(media, 'duration'):
                            duration = media.duration
                            
                        # Если мы на macOS и громкость > 0, используем afplay для гарантии звука
                        if platform.system() == 'Darwin' and self.sound_volume > 0:
                            print(f"Используем afplay (macOS) для: {audio_path}")
                            # afplay поддерживает опцию -v для громкости (0-255? Нет, 0-1 или логарифмически)
                            # man afplay: -v VOLUME (high quality linear volume, 1 is normal)
                            vol_str = str(max(0.0, min(1.0, self.sound_volume)))
                            self.afplay_process = subprocess.Popen(['afplay', '-v', vol_str, audio_path])
                            # Не используем self.story_audio_player
                        else:
                            # Для других ОС или если afplay не нужен
                            self.story_audio_player = media.play()
                            try:
                                self.story_audio_player.volume = self.sound_volume
                            except:
                                pass
                                
                    except Exception as e:
                        print(f"Pyglet error: {e}")
                        # Fallback to arcade
                        try:
                            sound = arcade.load_sound(audio_path)
                            if sound:
                                self.story_audio_player = arcade.play_sound(sound, volume=self.sound_volume)
                                if duration == 0:
                                    if hasattr(sound, 'get_length'):
                                        duration = sound.get_length()
                                    elif hasattr(sound, 'source') and hasattr(sound.source, 'duration'):
                                        duration = sound.source.duration
                        except Exception as e2:
                            print(f"Arcade error: {e2}")

                    if duration > 0:
                        self.story_line_duration = duration + 0.5 # Add small buffer
                        self.story_line_timer = self.story_line_duration
                        
                    print(f"Воспроизводится аудиофайл: {audio_path}, длительность: {duration}")
                except Exception as e:
                    print(f"Ошибка воспроизведения аудио: {e}")
            else:
                print(f"Аудиофайл не найден: {audio_path}")

    # Генерация TTS озвучки удалена; используется папка story_audio
