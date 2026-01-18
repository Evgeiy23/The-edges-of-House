"""
Окно лобби для сетевой игры
"""
import arcade
import arcade.gui
import threading
from typing import Optional, List, Dict, Any


class LobbyWindow(arcade.View):
    def __init__(self, client):
        super().__init__()
        self.manager = arcade.gui.UIManager()
        self.manager.enable()

        self.client = client
        self.is_host = False
        self.players = []
        self.game_started = False

        # Import protocol after arcade window is available
        from dedicated_server.protocol import MessageType

        # Callbacks для обработки сообщений
        self.client.register_message_handler(
            MessageType.SERVER_ACCEPT,
            self._handle_server_accept
        )
        self.client.register_message_handler(
            MessageType.LOBBY_UPDATE,
            self._handle_lobby_update
        )
        self.client.register_message_handler(
            MessageType.GAME_START,
            self._handle_game_start
        )
        self.client.register_message_handler(
            MessageType.PLAYER_JOIN,
            self._handle_player_join
        )
        self.client.register_message_handler(
            MessageType.PLAYER_LEAVE,
            self._handle_player_leave
        )

        self.setup_ui()
        self.update_lobby_info()

    def setup_ui(self):
        self.manager.clear()

        main_box = arcade.gui.UIBoxLayout(vertical=True, space_between=20)

        # Заголовок
        title_label = arcade.gui.UILabel(
            text="ЛОББИ ИГРЫ",
            font_size=32,
            text_color=arcade.color.WHITE,
            width=600,
            align="center"
        )
        main_box.add(title_label)

        # Информация о лобби
        self.lobby_info_label = arcade.gui.UILabel(
            text="Загрузка информации о лобби...",
            font_size=18,
            text_color=arcade.color.LIGHT_GRAY,
            width=600,
            align="center"
        )
        main_box.add(self.lobby_info_label)

        # Список игроков
        self.players_list_label = arcade.gui.UILabel(
            text="Игроки:\n",
            font_size=16,
            text_color=arcade.color.WHITE,
            width=600,
            align="left"
        )
        main_box.add(self.players_list_label)

        # Кнопки
        buttons_box = arcade.gui.UIBoxLayout(vertical=False, space_between=20)

        self.start_game_button = arcade.gui.UIFlatButton(
            text="Начать игру",
            width=200,
            height=50
        )
        self.start_game_button.on_click = self.on_start_game_click
        self.start_game_button.enabled = False  # Доступна только для хоста
        buttons_box.add(self.start_game_button)

        back_button = arcade.gui.UIFlatButton(
            text="Выйти из лобби",
            width=200,
            height=50
        )
        back_button.on_click = self.on_back_click
        buttons_box.add(back_button)

        main_box.add(buttons_box)

        anchor_layout = arcade.gui.UIAnchorLayout()
        anchor_layout.add(
            child=main_box,
            anchor_x="center_x",
            anchor_y="center_y"
        )
        self.manager.add(anchor_layout)

    def update_lobby_info(self):
        """Обновляет информацию о лобби"""
        if not self.client:
            return

        # Обновляем информацию на основе данных клиента
        player_count = len(self.players)
        lobby_text = f"ID лобби: {self.client.lobby_id[:8] if self.client.lobby_id else 'N/A'}\n"
        # Предполагаем max_players = 10
        lobby_text += f"Игроки: {player_count}/{10}"
        self.lobby_info_label.text = lobby_text

        # Обновляем список игроков
        players_text = "Игроки в лобби:\n"
        if not self.players:
            players_text += "- Нет игроков\n"
        else:
            for player in self.players:
                if isinstance(player, dict):
                    player_name = player.get('player_name', 'Unknown')
                    is_host = player.get('is_host', False)
                    is_ready = player.get('ready', False)
                    status = " (ХОСТ)" if is_host else " (Гость)"
                    ready_status = " [ГОТОВ]" if is_ready else ""
                    players_text += f"- {player_name}{status}{ready_status}\n"
                else:
                    # If player is not a dict, try to get name directly
                    players_text += f"- {str(player)}\n"
        self.players_list_label.text = players_text

        # Обновляем состояние кнопки "Начать игру"
        self.start_game_button.enabled = self.is_host and not self.game_started

    def _handle_server_accept(self, message):
        """Обрабатывает подтверждение подключения от сервера"""
        lobby_state = message.data.get("game_state", {})
        self.game_started = lobby_state.get("game_started", False)

        # Проверяем, является ли текущий игрок хостом
        if hasattr(self.client, 'player_id'):
            host_id = lobby_state.get("host_id")
            self.is_host = self.client.player_id == host_id
        # Обновляем состояние кнопки "Начать игру" сразу после обновления is_host
        arcade.schedule(lambda dt: self.update_lobby_info(), 0)

        # Обновляем список игроков
        self.players = lobby_state.get("players", [])

        # Также обновляем список игроков в клиенте, чтобы он был синхронизирован
        if hasattr(self.client, 'lobby_players'):
            self.client.lobby_players = self.players

        # Обновляем UI в главном потоке
        arcade.schedule(lambda dt: self.update_lobby_info(), 0)

    def _handle_lobby_update(self, message):
        """Обрабатывает обновление состояния лобби"""
        lobby_state = message.data.get("lobby_state", {})
        self.game_started = lobby_state.get("game_started", False)

        # Проверяем, является ли текущий игрок хостом
        if hasattr(self.client, 'player_id'):
            host_id = lobby_state.get("host_id")
            self.is_host = self.client.player_id == host_id
        # Обновляем состояние кнопки "Начать игру" сразу после обновления is_host
        arcade.schedule(lambda dt: self.update_lobby_info(), 0)

        # Обновляем список игроков
        self.players = lobby_state.get("players", [])

        # Также обновляем список игроков в клиенте, чтобы он был синхронизирован
        if hasattr(self.client, 'lobby_players'):
            self.client.lobby_players = self.players

        # Обновляем UI в главном потоке
        arcade.schedule(lambda dt: self.update_lobby_info(), 0)

    def _handle_game_start(self, message):
        """Обрабатывает сообщение о начале игры"""
        self.game_started = True
        # Переключаемся в игровое окно
        arcade.schedule(lambda dt: self._switch_to_game_window(), 0)

    def _handle_player_join(self, message):
        """Обрабатывает присоединение игрока"""
        player_data = message.data.get("player_data", {})
        # Обновляем список игроков
        if player_data and player_data not in self.players:
            self.players.append(player_data)
        arcade.schedule(lambda dt: self.update_lobby_info(), 0)

    def _handle_player_leave(self, message):
        """Обрабатывает выход игрока"""
        player_id = message.data.get("player_id")
        # Удаляем игрока из списка
        self.players = [p for p in self.players if p.get(
            "player_id") != player_id]
        arcade.schedule(lambda dt: self.update_lobby_info(), 0)

    def on_start_game_click(self, event):
        """Обработчик нажатия кнопки 'Начать игру'"""
        if self.is_host and not self.game_started:
            # Отправляем запрос на начало игры
            # Используем asyncio.create_task для правильной отправки сообщения
            import asyncio
            try:
                # Проверяем, есть ли у нас цикл событий
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Если цикл запущен, используем create_task
                    asyncio.create_task(self.client.send_start_game())
                else:
                    # Если цикл не запущен, запускаем его
                    loop.run_until_complete(self.client.send_start_game())
            except RuntimeError:
                # Если нет активного цикла, создаем новый
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.client.send_start_game())
                loop.close()

    def on_back_click(self, event):
        """Обработчик нажатия кнопки 'Выйти из лобби'"""
        if self.client:
            # Отключаемся от сервера
            import asyncio

            def disconnect_client():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self.client.disconnect())
                    loop.close()
                except Exception as e:
                    print(f"Error disconnecting: {e}")

            threading.Thread(target=disconnect_client, daemon=True).start()

        # Возвращаемся в окно подключения
        arcade.schedule(lambda dt: self._switch_to_network_window(), 0)

    def _switch_to_game_window(self):
        """Переключение в игровое окно"""
        if self.window:
            from windows.game_window import GameWindow
            from project import ProjectSettings
            game_window = GameWindow(difficulty=ProjectSettings.Game.DIFFICULTY_EASY)
            game_window.client = self.client  # Передаем клиент в игровое окно
            # Также передаем информацию о том, что это сетевая игра
            game_window.is_network_game = True
            self.window.show_view(game_window)

    def _switch_to_network_window(self):
        """Переключение в окно подключения"""
        if self.window:
            from windows.network_window import NetworkWindow
            network_window = NetworkWindow()
            self.window.show_view(network_window)

    def on_draw(self):
        self.clear()
        arcade.draw_lrbt_rectangle_filled(
            0, self.width, 0, self.height, arcade.color.BLACK)
        self.manager.draw()

    def on_hide_view(self):
        self.manager.disable()

    def on_show_view(self):
        self.manager.enable()
