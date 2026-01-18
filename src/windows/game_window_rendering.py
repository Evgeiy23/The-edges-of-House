"""
Модуль для отрисовки игрового окна
Содержит все методы, связанные с рендерингом
"""
import arcade
import arcade.camera as arcade_camera
import random
import time


class GameWindowRendering:
    """Класс-миксин для методов отрисовки GameWindow"""
    
    def draw_map(self):
        """Отрисовка карты, игрока и боссов - полная реализация"""
        if not self.dungeon_map or not self.camera:
            return

        tile_size = self.tile_size
        cam_x, cam_y = self.camera.position
        half_w = (self.window.width // 2) if self.window else 0
        half_h = (self.window.height // 2) if self.window else 0

        view_left = max(0, int((cam_x - half_w) / tile_size) - 1)
        view_right = min(self.dungeon_map.map_width,
                         int((cam_x + half_w) / tile_size) + 2)
        view_bottom = max(0, int((cam_y - half_h) / tile_size) - 1)
        view_top = min(self.dungeon_map.map_height,
                       int((cam_y + half_h) / tile_size) + 2)

        batches = {
            'visible_exit': [],
            'seen_exit': [],
            'visible_wall': [],
            'seen_wall': [],
            'visible_floor': [],
            'seen_floor': []
        }
        
        texture_batches = {}

        use_grid = self.visibility_grid is not None
        use_explored = self.explored_grid is not None

        view_bottom_clamped = max(0, view_bottom)
        view_top_clamped = min(self.dungeon_map.map_height, view_top)
        view_left_clamped = max(0, view_left)
        view_right_clamped = min(self.dungeon_map.map_width, view_right)

        tile_size_float = float(tile_size)

        for y in range(view_bottom_clamped, view_top_clamped):
            vis_row = self.visibility_grid[y] if use_grid else None
            screen_y = y * tile_size_float
            bottom = screen_y
            top = screen_y + tile_size_float
            cy = screen_y + tile_size_float / 2

            for x in range(view_left_clamped, view_right_clamped):
                if use_grid:
                    visible = vis_row[x]
                else:
                    visible = (x, y) in self.visible_tiles

                explored = False
                if use_explored:
                    explored = self.explored_grid[y][x]
                else:
                    explored = visible or (x, y) in getattr(
                        self, "explored_tiles", set())

                if not visible and not explored:
                    continue

                value = self.dungeon_map.get_tile_value(x, y)
                if value is None:
                    continue

                screen_x = x * tile_size_float
                cx = screen_x + tile_size_float / 2
                
                # Try to use texture
                tex = self.dungeon_map.textures.get(value) if hasattr(self.dungeon_map, 'textures') else None
                
                if tex:
                    if value not in texture_batches:
                        texture_batches[value] = {'visible': [], 'seen': []}
                    
                    key = 'visible' if visible else 'seen'
                    texture_batches[value][key].append((cx, cy))
                else:
                    # Fallback logic
                    left = screen_x
                    right = screen_x + tile_size_float
                    
                    if value == 3: # Exit
                        key = 'visible_exit' if visible else 'seen_exit'
                        batches[key].append((left, right, bottom, top))
                    elif value == 1: # Wall
                        key = 'visible_wall' if visible else 'seen_wall'
                        batches[key].append((left, right, bottom, top))
                    else: # Floor
                        key = 'visible_floor' if visible else 'seen_floor'
                        batches[key].append((left, right, bottom, top))

        # Draw textures
        for val, lists in texture_batches.items():
            tex = self.dungeon_map.textures.get(val)
            if not tex: continue
            
            # Visible
            for cx, cy in lists['visible']:
                left = cx - tile_size / 2
                right = cx + tile_size / 2
                bottom = cy - tile_size / 2
                top = cy + tile_size / 2
                rect = arcade.types.Rect(left, right, bottom, top, tile_size, tile_size, cx, cy)
                arcade.draw_texture_rect(tex, rect)
                
            # Seen (Tinted)
            color = arcade.types.Color(100, 100, 110)
            for cx, cy in lists['seen']:
                left = cx - tile_size / 2
                right = cx + tile_size / 2
                bottom = cy - tile_size / 2
                top = cy + tile_size / 2
                rect = arcade.types.Rect(left, right, bottom, top, tile_size, tile_size, cx, cy)
                arcade.draw_texture_rect(tex, rect, color=color)

        color_batches = {
            arcade.color.DIM_GRAY: batches['visible_wall'],
            arcade.color.LIGHT_GRAY: batches['visible_floor'],
            (180, 60, 40): batches['visible_exit'],
            (110, 110, 120): batches['seen_wall'],
            (140, 140, 160): batches['seen_exit'],
            (100, 100, 110): batches['seen_floor']
        }

        for color, rects in color_batches.items():
            if rects:
                for left, right, bottom, top in rects:
                    arcade.draw_lrbt_rectangle_filled(
                        left, right, bottom, top, color)

        # Fog of war
        if self.visibility_grid:
            for y in range(view_bottom_clamped, view_top_clamped):
                vis_row = self.visibility_grid[y]
                exp_row = self.explored_grid[y] if self.explored_grid else None
                screen_y = y * tile_size
                bottom = screen_y
                top = screen_y + tile_size
                for x in range(view_left_clamped, view_right_clamped):
                    if vis_row[x]:
                        continue
                    explored = exp_row[x] if exp_row else False
                    screen_x = x * tile_size
                    fog_color = (0, 0, 0, 255)
                    arcade.draw_lrbt_rectangle_filled(
                        screen_x, screen_x + tile_size, bottom, top, fog_color)

        # Save point
        if self.save_point_pos:
            save_x, save_y = self.save_point_pos
            if use_grid and self.dungeon_map and 0 <= save_x < self.dungeon_map.map_width and 0 <= save_y < self.dungeon_map.map_height:
                if self.visibility_grid[save_y][save_x] or (self.explored_grid and self.explored_grid[save_y][save_x]):
                    save_screen_x = save_x * tile_size
                    save_screen_y = save_y * tile_size
                    color = arcade.color.CYAN if not self.save_point_used else arcade.color.DARK_GRAY
                    arcade.draw_circle_filled(
                        save_screen_x + tile_size / 2,
                        save_screen_y + tile_size / 2,
                        tile_size * 0.3,
                        color
                    )

        # Player
        if self.player:
            self.player.draw()
            self.draw_player_health_above()

        # Boss visibility check
        if self.dungeon_map and self.player and self.bosses:
            player_room_id = self.dungeon_map.get_room_id(
                self.player.pos[0], self.player.pos[1])
            if player_room_id in self.boss_room_ids:
                for boss in self.bosses:
                    if boss and not boss.visible:
                        rid = self.dungeon_map.get_room_id(
                            boss.pos[0], boss.pos[1])
                        if rid == player_room_id:
                            boss.visible = True
                            self.shake_camera(10.0, 0.5)

        # Draw bosses
        for boss in self.bosses:
            if boss and boss.is_alive() and hasattr(boss, 'visible') and boss.visible:
                boss_grid_x = int(boss.pos[0])
                boss_grid_y = int(boss.pos[1])
                
                is_visible = False
                if self.visibility_grid and 0 <= boss_grid_y < len(self.visibility_grid) and 0 <= boss_grid_x < len(self.visibility_grid[0]):
                    is_visible = self.visibility_grid[boss_grid_y][boss_grid_x]
                elif (boss_grid_x, boss_grid_y) in self.visible_tiles:
                    is_visible = True
                    
                if is_visible:
                    boss.draw()

        # Draw chests in same room
        if self.chest_sprites and self.player and self.dungeon_map:
            player_room_id = self.dungeon_map.get_room_id(
                self.player.pos[0], self.player.pos[1])
            chests_to_draw = arcade.SpriteList()
            for chest in self.chest_sprites:
                chest_grid_x = int(chest.center_x / self.tile_size)
                chest_grid_y = int(chest.center_y / self.tile_size)
                chest_room_id = self.dungeon_map.get_room_id(
                    chest_grid_x, chest_grid_y)
                if chest_room_id == player_room_id:
                    chests_to_draw.append(chest)
            if len(chests_to_draw) > 0:
                chests_to_draw.draw()

        # Draw dropped items in same room
        if self.dropped_item_sprites and self.player and self.dungeon_map:
            player_room_id = self.dungeon_map.get_room_id(
                self.player.pos[0], self.player.pos[1])
            items_to_draw = arcade.SpriteList()
            for item in self.dropped_item_sprites:
                item_grid_x = int(item.center_x / self.tile_size)
                item_grid_y = int(item.center_y / self.tile_size)
                item_room_id = self.dungeon_map.get_room_id(
                    item_grid_x, item_grid_y)
                if item_room_id == player_room_id:
                    items_to_draw.append(item)
            if len(items_to_draw) > 0:
                items_to_draw.draw()

        if self.ambient_sprites:
            self.ambient_sprites.draw()

        self.draw_minimap()
        self.draw_player_health()
        self.draw_death_message()

    def draw_passage_opening_effect(self):
        """Рисует эффект открытия прохода"""
        if not self.passage_opening_effect or not self.passage_opening_effect['active']:
            return

        effect = self.passage_opening_effect
        elapsed = time.time() - effect['start_time']

        if elapsed > effect['duration']:
            effect['active'] = False
            return

        # Создаем новые частицы
        if len(effect['particles']) < 100:
            for _ in range(5):
                pos = random.choice(self.dungeon_map.exit_door_positions)
                x = (pos[0] + 0.5) * self.tile_size
                y = (pos[1] + 0.5) * self.tile_size
                particle = {
                    'x': x,
                    'y': y,
                    'dx': random.uniform(-2, 2),
                    'dy': random.uniform(3, 7),
                    'size': random.uniform(3, 8),
                    'life': 1.0
                }
                effect['particles'].append(particle)

        # Обновляем и рисуем частицы
        for particle in effect['particles'][:]:
            particle['x'] += particle['dx']
            particle['y'] += particle['dy']
            particle['life'] -= 0.02
            particle['dy'] -= 0.2  # Гравитация

            if particle['life'] > 0:
                alpha = int(255 * particle['life'])
                arcade.draw_circle_filled(
                    particle['x'], particle['y'],
                    particle['size'],
                    (*arcade.color.YELLOW[:3], alpha)
                )
            else:
                effect['particles'].remove(particle)

    def draw_player_health(self):
        """Отрисовка полоски здоровья игрока"""
        if not self.player or not self.window:
            return

        # Используем UI камеру, если она есть
        if hasattr(self, 'ui_camera') and self.ui_camera:
            self.ui_camera.use()

        bar_width = 200
        bar_height = 20
        bar_x = 20
        bar_y = self.window.height - 40

        # Фон полоски
        arcade.draw_lrbt_rectangle_filled(
            bar_x, bar_x + bar_width, bar_y, bar_y + bar_height,
            arcade.color.BLACK
        )

        # Полоска здоровья
        health_percent = self.player.health / self.player.max_health
        health_width = bar_width * health_percent
        health_color = arcade.color.RED if health_percent < 0.3 else (
            arcade.color.YELLOW if health_percent < 0.6 else arcade.color.GREEN
        )
        arcade.draw_lrbt_rectangle_filled(
            bar_x, bar_x + health_width, bar_y, bar_y + bar_height,
            health_color
        )

        # Рамка
        arcade.draw_lrbt_rectangle_outline(
            bar_x, bar_x + bar_width, bar_y, bar_y + bar_height,
            arcade.color.WHITE, 2
        )

        # Текст здоровья
        health_text = f"{int(self.player.health)}/{self.player.max_health}"
        arcade.draw_text(
            health_text,
            bar_x + bar_width / 2,
            bar_y + bar_height / 2,
            arcade.color.WHITE,
            14,
            anchor_x="center",
            anchor_y="center",
            bold=True
        )
        self.draw_inventory_bar()

    def draw_inventory_bar(self):
        """Отрисовка панели инвентаря"""
        if not self.window:
            return
        self.ui_camera.use()
        slots = 9
        slot_size = 48
        padding = 8
        total_w = slots * slot_size + (slots - 1) * padding
        x0 = (self.window.width - total_w) // 2
        y0 = 20
        inv_list = arcade.SpriteList()
        for i in range(slots):
            left = x0 + i * (slot_size + padding)
            right = left + slot_size
            bottom = y0
            top = y0 + slot_size
            color = arcade.color.DARK_GRAY if i != self.selected_slot else arcade.color.LIGHT_GRAY
            arcade.draw_lrbt_rectangle_filled(left, right, bottom, top, color)
            arcade.draw_lrbt_rectangle_outline(
                left, right, bottom, top, arcade.color.WHITE, 2)
            if i < len(self.inventory):
                icon_id = self.inventory[i].get("icon_id")
                tex = self.item_textures.get(icon_id)
                if tex:
                    cx = (left + right) / 2
                    cy = (bottom + top) / 2
                    arcade.draw_texture_rectangle(cx, cy, slot_size * 0.8, slot_size * 0.8, tex)

    def draw_player_health_above(self):
        """Отрисовка полоски здоровья игрока над игроком"""
        if not self.player or not self.player.is_alive():
            return

        px, py = self.player.get_pixel_position()
        bar_width = self.tile_size * 0.8
        bar_height = 6
        bar_x = px - bar_width / 2
        bar_y = py + self.tile_size / 2 + 10

        # Фон
        arcade.draw_lrbt_rectangle_filled(
            bar_x, bar_x + bar_width, bar_y, bar_y + bar_height,
            arcade.color.BLACK
        )

        # Здоровье
        health_percent = self.player.health / self.player.max_health
        health_width = bar_width * health_percent
        health_color = arcade.color.RED if health_percent < 0.3 else (
            arcade.color.YELLOW if health_percent < 0.6 else arcade.color.GREEN
        )
        arcade.draw_lrbt_rectangle_filled(
            bar_x, bar_x + health_width, bar_y, bar_y + bar_height,
            health_color
        )

        # Рамка
        arcade.draw_lrbt_rectangle_outline(
            bar_x, bar_x + bar_width, bar_y, bar_y + bar_height,
            arcade.color.WHITE, 1
        )

    def draw_death_message(self):
        """Отрисовка сообщения о смерти игрока"""
        if not self.player_dead_message or self.death_message_timer <= 0:
            return

        if not self.window:
            return

        # Используем UI камеру
        if hasattr(self, 'ui_camera') and self.ui_camera:
            self.ui_camera.use()

        # Полупрозрачный фон
        arcade.draw_lrbt_rectangle_filled(
            0, self.window.width, 0, self.window.height,
            (0, 0, 0, 180)
        )

        # Текст сообщения
        arcade.draw_text(
            self.player_dead_message,
            self.window.width // 2,
            self.window.height // 2,
            arcade.color.RED,
            48,
            anchor_x="center",
            anchor_y="center",
            bold=True
        )

    def draw_minimap(self):
        """Отрисовка миникарты - полная реализация"""
        if not self.dungeon_map or not self.player:
            return

        if self.ui_camera:
            self.ui_camera.use()

        max_dim = max(self.dungeon_map.map_width, self.dungeon_map.map_height)
        minimap_scale = max(2.0, min(5.0, 420 / max(1, max_dim)))
        minimap_width = int(self.dungeon_map.map_width * minimap_scale)
        minimap_height = int(self.dungeon_map.map_height * minimap_scale)
        minimap_x = self.window.width - minimap_width - 15
        minimap_y = self.window.height - 15

        arcade.draw_lrbt_rectangle_filled(minimap_x, minimap_x + minimap_width,
                                          minimap_y - minimap_height, minimap_y,
                                          (0, 0, 0, 180))

        use_grid = self.visibility_grid is not None
        use_explored = self.explored_grid is not None
        for y in range(self.dungeon_map.map_height):
            for x in range(self.dungeon_map.map_width):
                tile_value = self.dungeon_map.get_tile_value(x, y)
                if tile_value is None:
                    continue

                visible = False
                explored = False
                if use_grid:
                    visible = self.visibility_grid[y][x]
                else:
                    visible = (x, y) in self.visible_tiles
                if use_explored:
                    explored = self.explored_grid[y][x]
                else:
                    explored = visible or (x, y) in getattr(
                        self, "explored_tiles", set())

                if not visible and not explored:
                    continue

                mini_x = minimap_x + x * minimap_scale
                mini_y = minimap_y - y * minimap_scale

                if visible:
                    if tile_value == 0:
                        color = arcade.color.LIGHT_GRAY
                    elif tile_value == 1:
                        color = arcade.color.DIM_GRAY
                    elif tile_value == 2:
                        color = arcade.color.LIGHT_BLUE
                    elif tile_value == 3:
                        color = (220, 90, 60)
                    else:
                        color = arcade.color.WHITE
                else:
                    color = (50, 50, 70, 170)

                arcade.draw_lrbt_rectangle_filled(mini_x,
                                                  mini_x + minimap_scale,
                                                  mini_y - minimap_scale,
                                                  mini_y, color)

        player_mini_x = minimap_x + self.player.pos[0] * minimap_scale
        player_mini_y = minimap_y - self.player.pos[1] * minimap_scale
        if self.minimap_player_draw_pos is None:
            self.minimap_player_draw_pos = (
                float(player_mini_x), float(player_mini_y))
        else:
            lerp = 0.25
            cur_x, cur_y = self.minimap_player_draw_pos
            cur_x += (player_mini_x - cur_x) * lerp
            cur_y += (player_mini_y - cur_y) * lerp
            self.minimap_player_draw_pos = (cur_x, cur_y)
            player_mini_x, player_mini_y = cur_x, cur_y
        arcade.draw_circle_filled(
            player_mini_x, player_mini_y, minimap_scale * 0.8, arcade.color.YELLOW)
