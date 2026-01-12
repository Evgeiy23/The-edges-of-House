"""
Окно для подключения к сетевой игре
"""
import arcade
import arcade.gui
import socket
import threading
import asyncio
from typing import List, Dict, Optional

from network.client import GameClient


class NetworkWindow(arcade.View):
    def __init__(self):
        super().__init__()
        self.manager = arcade.gui.UIManager()
        self.manager.enable()

        self.servers: List[Dict[str, str]] = []  # Список найденных серверов
        self.scanning = False
        self.selected_server_index = -1
        self.client = None  # Добавляем атрибут для клиента

        self.setup_ui()
        self.start_server_scan()

    def setup_ui(self):
        self.manager.clear()

        main_box = arcade.gui.UIBoxLayout(vertical=True, space_between=15)

        # Заголовок
        title_label = arcade.gui.UILabel(
            text="ПОДКЛЮЧЕНИЕ К СЕРВЕРУ",
            font_size=32,
            text_color=arcade.color.WHITE,
            width=600,
            align="center"
        )
        main_box.add(title_label)

        # Список серверов
        self.server_list_label = arcade.gui.UILabel(
            text="Поиск серверов...",
            font_size=18,
            text_color=arcade.color.LIGHT_GRAY,
            width=600,
            align="center"
        )
        main_box.add(self.server_list_label)

        # Кнопки
        buttons_box = arcade.gui.UIBoxLayout(vertical=False, space_between=20)

        self.connect_button = arcade.gui.UIFlatButton(
            text="Подключиться",
            width=200,
            height=50
        )
        self.connect_button.on_click = self.on_connect_click
        self.connect_button.enabled = False
        buttons_box.add(self.connect_button)

        refresh_button = arcade.gui.UIFlatButton(
            text="Обновить",
            width=200,
            height=50
        )
        refresh_button.on_click = self.on_refresh_click
        buttons_box.add(refresh_button)

        back_button = arcade.gui.UIFlatButton(
            text="Назад",
            width=200,
            height=50
        )
        back_button.on_click = self.on_back_click
        buttons_box.add(back_button)

        main_box.add(buttons_box)

        # Прямой ввод IP
        ip_box = arcade.gui.UIBoxLayout(vertical=False, space_between=10)

        ip_label = arcade.gui.UILabel(
            text="Или введите IP:",
            font_size=16,
            text_color=arcade.color.WHITE,
            width=150
        )
        ip_box.add(ip_label)

        self.ip_input = arcade.gui.UIInputText(
            text="127.0.0.1:7777",
            width=200,
            height=40,
            text_color=arcade.color.WHITE
        )
        ip_box.add(self.ip_input)

        connect_ip_button = arcade.gui.UIFlatButton(
            text="Подключиться",
            width=150,
            height=40
        )
        connect_ip_button.on_click = self.on_connect_ip_click
        ip_box.add(connect_ip_button)

        main_box.add(ip_box)

        anchor_layout = arcade.gui.UIAnchorLayout()
        anchor_layout.add(
            child=main_box,
            anchor_x="center_x",
            anchor_y="center_y"
        )
        self.manager.add(anchor_layout)

    def start_server_scan(self):
        """Запускает сканирование серверов в локальной сети"""
        if self.scanning:
            return

        self.scanning = True
        self.servers = []
        self.server_list_label.text = "Поиск серверов..."

        # Запускаем сканирование в отдельном потоке
        thread = threading.Thread(target=self.scan_local_network, daemon=True)
        thread.start()

    def scan_local_network(self):
        """Сканирует локальную сеть на наличие серверов"""
        try:
            # Получаем локальный IP
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            ip_parts = local_ip.split('.')
            base_ip = '.'.join(ip_parts[:-1])

            # Сканируем диапазон IP (например, .1 - .254)
            found_servers = []
            port = 7777

            for i in range(1, 255):
                if not self.scanning:
                    break

                test_ip = f"{base_ip}.{i}"
                if self.check_server(test_ip, port):
                    found_servers.append({
                        "ip": test_ip,
                        "port": str(port),
                        "name": f"Сервер {test_ip}:{port}"
                    })
                    # Обновляем UI в главном потоке
                    arcade.schedule(self.update_server_list, 0)

            # Также проверяем localhost
            if self.check_server("127.0.0.1", port):
                found_servers.append({
                    "ip": "127.0.0.1",
                    "port": str(port),
                    "name": f"Локальный сервер (127.0.0.1:{port})"
                })
                arcade.schedule(self.update_server_list, 0)

            # Update the main servers list
            self.servers = found_servers

        except Exception as e:
            print(f"Ошибка при сканировании сети: {e}")

        finally:
            self.scanning = False
            arcade.schedule(self.finish_scan, 0)

    def check_server(self, ip: str, port: int, timeout: float = 0.5) -> bool:
        """Проверяет доступность сервера"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
        except Exception:
            return False

    def update_server_list(self, _dt):
        """Обновляет список серверов в UI"""
        if self.scanning:
            count = len(self.servers)
            self.server_list_label.text = f"Найдено серверов: {count}..."

    def finish_scan(self, _dt):
        """Завершает сканирование и обновляет UI"""
        if len(self.servers) == 0:
            self.server_list_label.text = "Серверы не найдены"
        else:
            server_names = [s["name"] for s in self.servers]
            self.server_list_label.text = "\n".join(server_names)
            self.selected_server_index = 0
            # Enable the connect button when servers are found
            self.connect_button.enabled = True

    def on_refresh_click(self, event):
        """Обновляет список серверов"""
        self.start_server_scan()

    def on_connect_click(self, event):
        """Подключается к выбранному серверу"""
        if self.selected_server_index >= 0 and self.selected_server_index < len(self.servers):
            server = self.servers[self.selected_server_index]
            self.connect_to_server(server["ip"], int(server["port"]))

    def on_connect_ip_click(self, event):
        """Подключается к серверу по введенному IP"""
        ip_text = self.ip_input.text.strip()
        try:
            if ':' in ip_text:
                ip, port = ip_text.split(':')
                port = int(port)
            else:
                ip = ip_text
                port = 7777
            self.connect_to_server(ip, port)
        except Exception as e:
            print(f"Ошибка подключения: {e}")
            # TODO: Показать сообщение об ошибке пользователю

    def connect_to_server(self, ip: str, port: int):
        """Подключается к серверу и переходит к игре"""
        # Создаем клиент и подключаемся к серверу
        self.client = GameClient(ip, port)

        # Устанавливаем callback для успешного подключения
        def on_connect():
            print(f"Successfully connected to {ip}:{port}")
            # После успешного подключения переходим в лобби
            # Schedule this to run on the main thread to avoid OpenGL context issues
            if self.window:
                import arcade
                arcade.schedule(lambda dt: self._switch_to_lobby_window(), 0)

        def on_disconnect():
            print("Disconnected from server")
            # При отключении возвращаемся в меню
            # Schedule this to run on the main thread to avoid OpenGL context issues
            if self.window:
                import arcade
                arcade.schedule(lambda dt: self._switch_to_start_window(), 0)

        # Устанавливаем callback для отключения
        self.client.set_on_connect(on_connect)
        self.client.set_on_disconnect(on_disconnect)

        # Запускаем подключение в отдельном потоке
        connect_thread = threading.Thread(
            target=lambda: asyncio.run(self._connect_with_name(ip, port)),
            daemon=True
        )
        connect_thread.start()

    def _switch_to_lobby_window(self):
        """Switch to lobby window on the main thread to avoid OpenGL context issues"""
        if self.window:
            from windows.lobby_window import LobbyWindow
            # Передаем клиент в окно лобби
            lobby_window = LobbyWindow(self.client)
            self.window.show_view(lobby_window)

    def _switch_to_start_window(self):
        """Switch to start window on the main thread to avoid OpenGL context issues"""
        if self.window:
            from windows.start_window import StartWindow
            start_window = StartWindow()
            self.window.show_view(start_window)

    async def _connect_with_name(self, ip: str, port: int):
        """Асинхронная функция подключения с выбором имени игрока"""
        # В реальной реализации здесь должен быть диалог ввода имени
        player_name = f"Player_{hash(ip + str(port)) % 10000}"  # Временное имя
        await self.client.connect(player_name)

    def on_back_click(self, event):
        """Возвращается в главное меню"""
        self.scanning = False
        if self.window:
            import arcade
            arcade.schedule(lambda dt: self._switch_to_start_window(), 0)

    def _switch_to_start_window(self):
        """Switch to start window on the main thread to avoid OpenGL context issues"""
        if self.window:
            from windows.start_window import StartWindow
            start_window = StartWindow()
            self.window.show_view(start_window)

    def on_draw(self):
        self.clear()
        arcade.draw_lrbt_rectangle_filled(
            0, self.width, 0, self.height, arcade.color.BLACK)
        self.manager.draw()

    def on_hide_view(self):
        self.manager.disable()
        self.scanning = False

    def on_show_view(self):
        self.manager.enable()
