import arcade
import random
import threading
import time
import traceback

from project import ProjectSettings
from game.logic.map.storage import generate_and_store_map
from windows.game_window import GameWindow


class LoadingView(arcade.View):
    """Отдельный экран загрузки, который генерирует карту и сохраняет ее в CSV."""

    def __init__(self, difficulty=None, load_save=False, map_name="current"):
        super().__init__()
        self.difficulty = difficulty or ProjectSettings.Game.DIFFICULTY_EASY
        self.load_save = load_save
        self.map_name = map_name

        self.status = "pending"
        self.error = None
        self.progress_text = "Подготовка..."

        self.map_payload = None
        self.spawn_corner = None

        self._worker_thread = None
        self._switch_scheduled = False
        self._started_at = time.time()

    def on_show_view(self):
        arcade.set_background_color(ProjectSettings.BACKGROUND_COLOR)
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
                # Для загрузки сохранения карту не создаем — сразу переходим в игру
                self.status = "done"
                return

            game_cfg = ProjectSettings.Game
            map_width, map_height = GameWindow.compute_map_dimensions(
                1, game_cfg)

            self.spawn_corner = random.choice(
                ["bottom_left", "bottom_right"])
            self.progress_text = "Генерация случайной карты..."

            self.map_payload = generate_and_store_map(
                map_width, map_height, game_cfg, self.spawn_corner, map_name=self.map_name)
            self.status = "done"
        except Exception as e:
            self.error = str(e)
            traceback.print_exc()
            self.status = "error"

    def on_draw(self):
        self.clear()

        message = self.progress_text
        if self.error:
            message = f"Ошибка генерации: {self.error}"
        elif self.status == "done":
            message = "Загрузка завершена, переход к игре..."
        elif self.status == "pending":
            message = "Подготовка к генерации карты..."

        arcade.draw_text(
            message,
            self.width // 2,
            self.height // 2,
            arcade.color.WHITE,
            24,
            anchor_x="center",
            anchor_y="center",
            align="center",
        )

    def on_update(self, delta_time):
        if self.status == "done" and not self._switch_scheduled and self.window:
            self._switch_scheduled = True
            next_view = GameWindow(
                difficulty=self.difficulty,
                load_save=self.load_save,
                map_payload=self.map_payload,
                map_name=self.map_name,
                spawn_corner=self.spawn_corner,
                level_override=1
            )
            self.window.show_view(next_view)
        elif self.status == "error" and not self._switch_scheduled:
            # Показываем сообщение об ошибке на экране; переход не выполняем
            pass

