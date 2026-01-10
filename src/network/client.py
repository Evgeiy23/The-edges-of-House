"""
Клиент для подключения к серверу игры
"""
import asyncio
import json
import logging
import sys
import os
from typing import Optional, Callable, Dict, Any

# Try to import from dedicated_server, with fallback path modification
try:
    from dedicated_server.protocol import Message, MessageType
except ImportError:
    import sys
    import os
    # Add the parent directory to the Python path to import dedicated_server modules
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(os.path.dirname(current_dir))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    from dedicated_server.protocol import Message, MessageType


logger = logging.getLogger(__name__)


class GameClient:
    """Клиент для подключения к серверу игры"""

    def __init__(self, host: str = "127.0.0.1", port: int = 7777):
        self.host = host
        self.port = port
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.connected = False
        self.player_id: Optional[str] = None
        self.lobby_id: Optional[str] = None
        self.game_started = False

        # Callbacks для обработки сообщений
        self.message_handlers: Dict[MessageType, Callable] = {}
        self.on_connect_callback: Optional[Callable] = None
        self.on_disconnect_callback: Optional[Callable] = None

    async def connect(self, player_name: str) -> bool:
        """Подключается к серверу и отправляет сообщение о подключении"""
        try:
            self.reader, self.writer = await asyncio.open_connection(
                self.host, self.port
            )
            self.connected = True

            # Создаем и отправляем сообщение подключения
            connect_message = Message.create_client_connect(player_name)
            await self.send_message(connect_message)

            # Запускаем обработчик входящих сообщений
            asyncio.create_task(self._message_handler())

            logger.info(f"Connected to server {self.host}:{self.port}")
            if self.on_connect_callback:
                self.on_connect_callback()

            return True

        except Exception as e:
            logger.error(f"Failed to connect to server: {e}")
            self.connected = False
            return False

    async def disconnect(self):
        """Отключается от сервера"""
        self.connected = False
        if self.writer:
            self.writer.close()
            try:
                await self.writer.wait_closed()
            except:
                pass
        logger.info("Disconnected from server")
        if self.on_disconnect_callback:
            # Schedule the callback to run on the main thread to avoid OpenGL context issues
            try:
                import arcade
                arcade.schedule(lambda dt: self.on_disconnect_callback(), 0)
            except Exception:
                # If arcade is not available, call directly
                self.on_disconnect_callback()

    async def send_message(self, message: Message):
        """Отправляет сообщение на сервер"""
        if not self.connected or not self.writer:
            return

        try:
            message_json = message.to_json()
            message_bytes = message_json.encode('utf-8')
            length = len(message_bytes)

            # Отправляем длину сообщения (4 байта) и само сообщение
            self.writer.write(length.to_bytes(4, byteorder='big'))
            self.writer.write(message_bytes)
            await self.writer.drain()

        except Exception as e:
            logger.error(f"Error sending message: {e}")
            await self.disconnect()

    async def _message_handler(self):
        """Обрабатывает входящие сообщения от сервера"""
        while self.connected:
            try:
                # Читаем длину сообщения (4 байта)
                length_bytes = await self.reader.readexactly(4)
                length = int.from_bytes(length_bytes, byteorder='big')

                # Читаем само сообщение
                data = await self.reader.readexactly(length)
                message_str = data.decode('utf-8')

                # Парсим сообщение
                message = Message.from_json(message_str)
                await self._handle_message(message)

            except asyncio.IncompleteReadError:
                logger.info("Server closed connection")
                break
            except Exception as e:
                logger.error(f"Error reading message: {e}")
                break

        await self.disconnect()

    async def _handle_message(self, message: Message):
        """Обрабатывает полученное сообщение"""
        msg_type = message.type

        # Обработка специфичных типов сообщений
        if msg_type == MessageType.SERVER_ACCEPT:
            # Подключение принято
            self.player_id = message.data.get("player_id")
            lobby_state = message.data.get("game_state", {})
            self.lobby_id = lobby_state.get("lobby_id")
            self.game_started = lobby_state.get("game_started", False)
            logger.info(f"Connected successfully. Player ID: {self.player_id}")

        elif msg_type == MessageType.SERVER_REJECT:
            # Подключение отклонено
            reason = message.data.get("reason", "Unknown reason")
            logger.warning(f"Connection rejected: {reason}")
            await self.disconnect()

        elif msg_type == MessageType.PLAYER_JOIN:
            # Игрок присоединился к лобби
            logger.info(f"Player joined: {message.data}")

        elif msg_type == MessageType.PLAYER_LEAVE:
            # Игрок покинул лобби
            logger.info(f"Player left: {message.data}")

        elif msg_type == MessageType.LOBBY_UPDATE:
            # Обновление состояния лобби
            lobby_state = message.data.get("lobby_state", {})
            self.game_started = lobby_state.get("game_started", False)
            # Сохраняем информацию о других игроках
            self.lobby_players = lobby_state.get("players", [])
            logger.info(
                f"Lobby updated. Game started: {self.game_started}, Players: {len(self.lobby_players)}")

        elif msg_type == MessageType.GAME_START:
            # Игра началась
            self.game_started = True
            logger.info("Game started!")

        elif msg_type == MessageType.PLAYER_MOVE:
            # Движение игрока
            logger.debug(f"Player move: {message.data}")

        elif msg_type == MessageType.CHAT_BROADCAST:
            # Сообщение чата
            logger.info(
                f"Chat: {message.data.get('player_name', 'Unknown')}: {message.data.get('message', '')}")

        elif msg_type == MessageType.ERROR:
            # Ошибка от сервера
            error_msg = message.data.get("error", "Unknown error")
            logger.error(f"Server error: {error_msg}")

        # Вызов пользовательского обработчика
        if msg_type in self.message_handlers:
            await self.message_handlers[msg_type](message)

    def register_message_handler(self, msg_type: MessageType, handler: Callable):
        """Регистрирует обработчик для определенного типа сообщений"""
        self.message_handlers[msg_type] = handler

    def set_on_connect(self, callback: Callable):
        """Устанавливает callback для события подключения"""
        self.on_connect_callback = callback

    def set_on_disconnect(self, callback: Callable):
        """Устанавливает callback для события отключения"""
        self.on_disconnect_callback = callback

    async def send_player_move(self, x: int, y: int, facing: str = "front"):
        """Отправляет сообщение о движении игрока"""
        message = Message.create_player_move(self.player_id, (x, y), facing)
        await self.send_message(message)

    async def send_chat_message(self, message: str):
        """Отправляет сообщение в чат"""
        chat_msg = Message.create_chat_message(self.player_id, message)
        await self.send_message(chat_msg)

    async def send_lobby_ready(self, ready: bool = True):
        """Отправляет статус готовности в лобби"""
        message = Message.create_lobby_ready(self.player_id, ready)
        await self.send_message(message)

    async def send_start_game(self):
        """Отправляет запрос на начало игры (только для хоста)"""
        # Используем lobby_player_id вместо player_id, так как в лобби используется другой ID
        lobby_player_id = self.player_id  # player_id в лобби - это lobby_player_id
        message = Message.create_lobby_start_game(lobby_player_id)
        await self.send_message(message)
