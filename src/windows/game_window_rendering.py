"""
Модуль для отрисовки игрового окна
Содержит все методы, связанные с рендерингом
"""
import arcade
import random
import time
from project import ProjectSettings


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

                # Строго только видимые тайлы. Исследованные игнорируем (чернота).
                if not visible:
                    continue

                value = self.dungeon_map.get_tile_value(x, y)
                if value is None:
                    continue

                screen_x = x * tile_size_float
                cx = screen_x + tile_size_float / 2
                
                # Попытка использовать текстуру
                tex = self.dungeon_map.textures.get(value) if hasattr(self.dungeon_map, 'textures') else None
                
                if tex:
                    if value not in texture_batches:
                        texture_batches[value] = {'visible': []}
                    
                    texture_batches[value]['visible'].append((cx, cy))
                else:
                    # Логика отката
                    left = screen_x
                    right = screen_x + tile_size_float
                    
                    if value == 3: # Выход
                        batches['visible_exit'].append((left, right, bottom, top))
                    elif value == 1: # Стена
                        batches['visible_wall'].append((left, right, bottom, top))
                    else: # Пол
                        batches['visible_floor'].append((left, right, bottom, top))

        # Отрисовка текстур
        for val, lists in texture_batches.items():
            tex = self.dungeon_map.textures.get(val)
            if not tex:
                continue
            
            # Видимые
            for cx, cy in lists['visible']:
                left = cx - tile_size / 2
                right = cx + tile_size / 2
                bottom = cy - tile_size / 2
                top = cy + tile_size / 2
                rect = arcade.types.Rect(left, right, bottom, top, tile_size, tile_size, cx, cy)
                arcade.draw_texture_rect(tex, rect)

        color_batches = {
            arcade.color.DIM_GRAY: batches['visible_wall'],
            arcade.color.LIGHT_GRAY: batches['visible_floor'],
            (180, 60, 40): batches['visible_exit'],
            (50, 50, 60): batches['seen_wall'],
            (80, 80, 90): batches['seen_exit'],
            (60, 60, 70): batches['seen_floor']
        }

        for color, rects in color_batches.items():
            if rects:
                for left, right, bottom, top in rects:
                    arcade.draw_lrbt_rectangle_filled(
                        left, right, bottom, top, color)

        # Туман войны
        if self.visibility_grid:
            for y in range(view_bottom_clamped, view_top_clamped):
                vis_row = self.visibility_grid[y]
                screen_y = y * tile_size
                bottom = screen_y
                top = screen_y + tile_size
                for x in range(view_left_clamped, view_right_clamped):
                    if vis_row[x]:
                        continue
                    
                    # Рисуем черные квадраты везде, где не видно
                    screen_x = x * tile_size
                    fog_color = (0, 0, 0, 255)
                    arcade.draw_lrbt_rectangle_filled(
                        screen_x, screen_x + tile_size, bottom, top, fog_color)

        # Точка сохранения
        if self.save_point_pos:
            save_x, save_y = self.save_point_pos
            if use_grid and self.dungeon_map and 0 <= save_x < self.dungeon_map.map_width and 0 <= save_y < self.dungeon_map.map_height:
                if self.visibility_grid[save_y][save_x]:
                    save_screen_x = save_x * tile_size
                    save_screen_y = save_y * tile_size
                    color = arcade.color.CYAN if not self.save_point_used else arcade.color.DARK_GRAY
                    arcade.draw_circle_filled(
                        save_screen_x + tile_size / 2,
                        save_screen_y + tile_size / 2,
                        tile_size * 0.3,
                        color
                    )

        # Игрок
        if self.player:
            self.player.draw()
            # Отрисовка полоски здоровья игрока над игроком
            self.draw_player_health_above()

        # Отрисовка боссов
        for boss in self.bosses:
            if boss and boss.is_alive():
                boss_grid_x = int(boss.pos[0])
                boss_grid_y = int(boss.pos[1])
                
                # Frustum Culling
                bx, by = boss.pos
                boss_screen_x = bx * tile_size
                boss_screen_y = by * tile_size
                if not (cull_left < boss_screen_x < cull_right and cull_bottom < boss_screen_y < cull_top):
                    continue

                # Проверка тумана войны для врагов
                # Скрыть, если не в видимой области (строго visible_tiles)
                is_visible = (boss_grid_x, boss_grid_y) in self.visible_tiles
                
                # Дополнительная жесткая проверка дистанции
                # Если босс дальше радиуса обзора + небольшой запас, он не должен быть виден
                # Это исправляет баг, когда босс виден в темноте
                if is_visible and self.player:
                    dx = boss.pos[0] - self.player.pos[0]
                    dy = boss.pos[1] - self.player.pos[1]
                    dist_sq = dx*dx + dy*dy
                    # Динамический радиус с запасом
                    safe_radius = getattr(self, 'view_radius', 8) + 4
                    if dist_sq > safe_radius * safe_radius:
                        is_visible = False

                # Raycasting check (double check)
                if is_visible:
                     # Check line of sight using the helper method from GameWindow
                     if hasattr(self, '_check_line_of_sight'):
                         is_visible = self._check_line_of_sight((boss_grid_x, boss_grid_y))

                if is_visible:
                    boss.draw()
                    # Отрисовка обводки (с учетом прозрачности)
                    if hasattr(boss, "sprite") and ProjectSettings.DEBUG_MODE:
                        cx = boss.sprite.center_x
                        cy = boss.sprite.center_y
                        r = tile_size * 0.7
                        alpha = boss.sprite.alpha
                        color = (255, 0, 0, alpha)
                        arcade.draw_circle_outline(cx, cy, r, color, 3)

        # Отрисовка сундуков, если видимы (теперь всегда видны в темноте, кроме culling)
        if self.chest_sprites and self.player and self.dungeon_map:
            chests_to_draw = arcade.SpriteList()
            for chest in self.chest_sprites:
                chest_grid_x = int(chest.center_x / self.tile_size)
                chest_grid_y = int(chest.center_y / self.tile_size)
                
                # Frustum Culling
                if not (cull_left < chest.center_x < cull_right and cull_bottom < chest.center_y < cull_top):
                    continue

                # Сундуки видны всегда (по запросу пользователя)
                chests_to_draw.append(chest)
                
            if len(chests_to_draw) > 0:
                chests_to_draw.draw()

        # Define culling bounds
        cull_margin = self.tile_size * 2
        cull_left = cam_x - half_w - cull_margin
        cull_right = cam_x + half_w + cull_margin
        cull_bottom = cam_y - half_h - cull_margin
        cull_top = cam_y + half_h + cull_margin

        # Отрисовка выброшенных предметов, если видимы
        if self.dropped_item_sprites and self.player and self.dungeon_map:
            # Отрисовка предметов с проверкой видимости
            items_to_draw = arcade.SpriteList()
            for item in self.dropped_item_sprites:
                # Frustum Culling
                if not (cull_left < item.center_x < cull_right and cull_bottom < item.center_y < cull_top):
                    continue

                # Visibility Check (Fog of War)
                gx = int(item.center_x / self.tile_size)
                gy = int(item.center_y / self.tile_size)
                
                is_visible = (gx, gy) in self.visible_tiles
                
                # Raycasting for Items
                if is_visible and hasattr(self, '_check_line_of_sight'):
                     is_visible = self._check_line_of_sight((gx, gy))

                if is_visible:
                    items_to_draw.append(item)
            
            if len(items_to_draw) > 0:
                items_to_draw.draw()
            
                # Отрисовка обводки для видимых
                if ProjectSettings.DEBUG_MODE:
                    for item in items_to_draw:
                        if item.alpha > 0:
                            cx = item.center_x
                            cy = item.center_y
                            r = self.tile_size * 0.45
                            color = (144, 238, 144, item.alpha)
                            arcade.draw_circle_outline(cx, cy, r, color, 2)

        if self.ambient_sprites:
            # Frustum Culling и проверка видимости для эмбиента
            visible_ambient = arcade.SpriteList()
            for sprite in self.ambient_sprites:
                if cull_left < sprite.center_x < cull_right and cull_bottom < sprite.center_y < cull_top:
                     # Visibility Check
                    gx = int(sprite.center_x / self.tile_size)
                    gy = int(sprite.center_y / self.tile_size)
                    
                    is_visible = (gx, gy) in self.visible_tiles

                    # Raycasting for Ambient
                    if is_visible and hasattr(self, '_check_line_of_sight'):
                         is_visible = self._check_line_of_sight((gx, gy))
                        
                    if is_visible and sprite.alpha > 0:
                        visible_ambient.append(sprite)
            
            if len(visible_ambient) > 0:
                visible_ambient.draw()

        # Отрисовка Мудреца
        if hasattr(self, 'sage') and self.sage:
            sage_x = int(self.sage.pos[0])
            sage_y = int(self.sage.pos[1])
            
            # Frustum Culling for Sage
            sx, sy = self.sage.pos
            sage_screen_x = sx * self.tile_size
            sage_screen_y = sy * self.tile_size
            if (cull_left < sage_screen_x < cull_right and cull_bottom < sage_screen_y < cull_top):
                is_visible = (sage_x, sage_y) in self.visible_tiles
                
                # Дополнительная жесткая проверка дистанции для Мудреца
                if is_visible and self.player:
                    dx = self.sage.pos[0] - self.player.pos[0]
                    dy = self.sage.pos[1] - self.player.pos[1]
                    dist_sq = dx*dx + dy*dy
                    safe_radius = getattr(self, 'view_radius', 8) + 4
                    if dist_sq > safe_radius * safe_radius:
                        is_visible = False
                
                # Raycasting for Sage
                if is_visible and hasattr(self, '_check_line_of_sight'):
                     is_visible = self._check_line_of_sight((sage_x, sage_y))
                    
                if is_visible:
                    self.sage.draw()
                    if self.player:
                        self.sage.draw_ui(self.player.draw_pos)

        # Отрисовка Магов
        if hasattr(self, 'mages') and self.mages:
            for mage in self.mages:
                mage_x = int(mage.pos[0])
                mage_y = int(mage.pos[1])
                
                # Frustum Culling for Mage
                mx, my = mage.pos
                mage_screen_x = mx * self.tile_size
                mage_screen_y = my * self.tile_size
                if not (cull_left < mage_screen_x < cull_right and cull_bottom < mage_screen_y < cull_top):
                    continue

                is_visible = (mage_x, mage_y) in self.visible_tiles
                
                # Дополнительная жесткая проверка дистанции для магов
                if is_visible and self.player:
                    dx = mage.pos[0] - self.player.pos[0]
                    dy = mage.pos[1] - self.player.pos[1]
                    dist_sq = dx*dx + dy*dy
                    safe_radius = getattr(self, 'view_radius', 8) + 4
                    if dist_sq > safe_radius * safe_radius:
                        is_visible = False
                
                # Raycasting for Mage
                if is_visible and hasattr(self, '_check_line_of_sight'):
                     is_visible = self._check_line_of_sight((mage_x, mage_y))
                    
                if is_visible:
                    mage.draw()
                    # Mage UI (floating text) is now optional, as we have HUD
                    # if self.player:
                    #     mage.draw_ui(self.player.draw_pos)

        # Отрисовка призраков (Пакетом)
        if hasattr(self, 'ghost_manager') and self.ghost_manager:
            if self.visibility_grid:
                visible_ghosts = arcade.SpriteList()
                targets = self.ghost_manager.active_ghosts if self.ghost_manager.active_ghosts else self.ghost_manager.ghosts
                
                for ghost in targets:
                    ghost_x = int(ghost.pos[0])
                    ghost_y = int(ghost.pos[1])
                    
                    # Frustum Culling for Ghost
                    gx, gy = ghost.pos
                    ghost_screen_x = gx * self.tile_size
                    ghost_screen_y = gy * self.tile_size
                    if not (cull_left < ghost_screen_x < cull_right and cull_bottom < ghost_screen_y < cull_top):
                        continue

                    # Strict Visibility Check (Fog of War)
                    is_visible = (ghost_x, ghost_y) in self.visible_tiles
                    
                    # Raycasting check (double check)
                    if is_visible and hasattr(self, '_check_line_of_sight'):
                         is_visible = self._check_line_of_sight((ghost_x, ghost_y))
                    
                    # Дополнительная жесткая проверка дистанции
                    if is_visible and self.player:
                        dx = ghost.pos[0] - self.player.pos[0]
                        dy = ghost.pos[1] - self.player.pos[1]
                        dist_sq = dx*dx + dy*dy
                        safe_radius = getattr(self, 'view_radius', 8) + 2 # Чуть меньше запас для призраков
                        if dist_sq > safe_radius * safe_radius:
                            is_visible = False

                    if is_visible and ghost.sprite:
                        visible_ghosts.append(ghost.sprite)
                
                visible_ghosts.draw()

        # Отрисовка Торговца
        if hasattr(self, 'merchant') and self.merchant:
            merchant_grid_x = int(self.merchant.pos[0])
            merchant_grid_y = int(self.merchant.pos[1])
            
            # Frustum Culling for Merchant
            merch_x, merch_y = self.merchant.pos
            merch_screen_x = merch_x * self.tile_size
            merch_screen_y = merch_y * self.tile_size
            if (cull_left < merch_screen_x < cull_right and cull_bottom < merch_screen_y < cull_top):
                is_visible = (merchant_grid_x, merchant_grid_y) in self.visible_tiles
                
                # Raycasting for Merchant
                if is_visible and hasattr(self, '_check_line_of_sight'):
                     is_visible = self._check_line_of_sight((merchant_grid_x, merchant_grid_y))

                if is_visible:
                    self.merchant.draw()
                    if self.player:
                        self.merchant.draw_ui(self.player.draw_pos)

        self.draw_passage_opening_effect()

        # UI elements should be drawn in on_draw to ensure correct camera usage and layering
        # self.draw_minimap()
        # self.draw_player_health()
        # self.draw_death_message()

    def draw_passage_opening_effect(self):
        """Рисует эффект открытия прохода"""
        return # Отключено по запросу: убрать все партиклы
        if not self.passage_opening_effect or not self.passage_opening_effect['active']:
            return

        effect = self.passage_opening_effect
        elapsed = time.time() - effect['start_time']

        if elapsed > effect['duration']:
            effect['active'] = False
            return

        # Создаем новые частицы
        if len(effect['particles']) < 100:
            positions = []
            if hasattr(self.dungeon_map, 'exit_door_positions') and self.dungeon_map.exit_door_positions:
                 positions = self.dungeon_map.exit_door_positions
            elif hasattr(self.dungeon_map, 'exit_pos') and self.dungeon_map.exit_pos:
                 positions = [self.dungeon_map.exit_pos]

            for pos in positions:
                if random.random() < 0.3:
                     # Add particles
                     px = (pos[0] + random.random()) * self.tile_size
                     py = (pos[1] + random.random()) * self.tile_size
                     effect['particles'].append({
                         'x': px, 'y': py,
                         'vx': random.uniform(-1, 1), 'vy': random.uniform(1, 3),
                         'life': 1.0,
                         'size': random.uniform(2, 5)
                     })

        # Обновляем и рисуем частицы
        for particle in effect['particles']:
            particle['x'] += particle['vx']
            particle['y'] += particle['vy']
            particle['life'] -= 0.02
            
            if particle['life'] > 0:
                # Visibility check
                gx = int(particle['x'] / self.tile_size)
                gy = int(particle['y'] / self.tile_size)
                is_visible = (gx, gy) in self.visible_tiles
                
                # Raycasting check
                if is_visible:
                    is_visible = self._check_line_of_sight((gx, gy))

                if is_visible:
                    alpha = int(255 * particle['life'])
                    arcade.draw_circle_filled(
                        particle['x'], particle['y'],
                        particle['size'],
                        (*arcade.color.YELLOW[:3], alpha)
                    )

        # Удаляем мертвые частицы
        effect['particles'] = [p for p in effect['particles'] if p['life'] > 0]

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
        health_value = getattr(self.player, "display_health", self.player.health)
        health_percent = max(0.0, min(1.0, health_value / self.player.max_health))
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
        health_text = f"{int(health_value)}/{self.player.max_health}"
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

    def draw_inventory_bar(self):
        if not self.window:
            return
        if hasattr(self, 'ui_camera') and self.ui_camera:
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
                    sp = arcade.Sprite()
                    sp.texture = tex
                    sp.center_x = cx
                    sp.center_y = cy
                    if getattr(tex, "width", 0):
                        sp.scale = slot_size / tex.width
                    inv_list.append(sp)
        inv_list.draw()
        if 0 <= self.selected_slot < len(self.inventory):
            icon_id = self.inventory[self.selected_slot].get("icon_id")
            desc = self.get_item_description(icon_id)
            if desc:
                tx = self.window.width // 2
                ty = y0 + slot_size + 18
                arcade.draw_text(desc, tx, ty, arcade.color.WHITE,
                                 14, anchor_x="center", anchor_y="bottom")

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
                # explored = False # Ignored per user request
                if use_grid:
                    visible = self.visibility_grid[y][x]
                else:
                    visible = (x, y) in self.visible_tiles
                
                # Strict visibility check - ignore explored status (User: "оставь только черноту")
                if not visible:
                    continue

                mx = minimap_x + x * minimap_scale
                my = minimap_y - (self.dungeon_map.map_height - y) * minimap_scale
                
                color = arcade.color.LIGHT_GRAY
                if tile_value == 1:
                    color = arcade.color.DIM_GRAY
                elif tile_value == 3:
                    color = arcade.color.RED
                
                arcade.draw_lrbt_rectangle_filled(
                    mx, mx + minimap_scale,
                    my, my + minimap_scale,
                    color
                )
                
        # Player on minimap
        px = int(self.player.pos[0])
        py = int(self.player.pos[1])
        mx = minimap_x + px * minimap_scale
        my = minimap_y - (self.dungeon_map.map_height - py) * minimap_scale
        arcade.draw_lrbt_rectangle_filled(
            mx, mx + minimap_scale,
            my, my + minimap_scale,
            arcade.color.GREEN
        )

    def draw_mage_hud(self):
        """Отрисовка HUD мага (портрет и текст)"""
        if not hasattr(self, 'mages') or not self.mages:
            return
        
        # Берем первого мага (спутника)
        mage = self.mages[0]
        if not mage:
            return

        if hasattr(self, 'ui_camera') and self.ui_camera:
            self.ui_camera.use()

        # Настройки позиционирования (Левый нижний угол, над инвентарем)
        # Инвентарь y=20..68 (примерно).
        icon_size = 64
        padding = 10
        x = padding + 20
        y = 100 
        
        # Фон портрета
        arcade.draw_lrbt_rectangle_filled(x, x + icon_size, y, y + icon_size, (0, 0, 0, 180))
        arcade.draw_lrbt_rectangle_outline(x, x + icon_size, y, y + icon_size, arcade.color.AMETHYST, 2)
        
        # Портрет (используем текстуру мага)
        tex = None
        if hasattr(mage, 'sprite') and mage.sprite and mage.sprite.texture:
            tex = mage.sprite.texture
        elif hasattr(mage, 'texture') and mage.texture:
            tex = mage.texture
            
        if tex:
            # Используем draw_texture_rect с Rect, как это делается в draw_map
            rect = arcade.types.Rect(x, x + icon_size, y, y + icon_size, icon_size, icon_size, x + icon_size/2, y + icon_size/2)
            arcade.draw_texture_rect(tex, rect)
            
        # Индикатор взаимодействия (Нажмите E)
        if self.player and hasattr(mage, "sprite") and mage.sprite:
            p_x, p_y = self.player.draw_pos
            m_x, m_y = mage.sprite.center_x, mage.sprite.center_y
            
            dist_sq = (p_x - m_x)**2 + (p_y - m_y)**2
            interact_dist_sq = (self.tile_size * 3)**2
            
            if dist_sq < interact_dist_sq:
                 arcade.draw_text(
                    "Нажмите [E] чтобы поговорить",
                    x, 
                    y - 5, 
                    arcade.color.WHITE,
                    12,
                    anchor_x="left",
                    anchor_y="top"
                )
            
        # Текст (если есть)
        if hasattr(mage, 'current_response') and mage.current_response:
            text = mage.current_response
            
            # Параметры пузыря с текстом
            bubble_x = x + icon_size + padding
            bubble_y = y
            bubble_w = 400
            bubble_h = icon_size
            
            # Фон текста
            arcade.draw_lrbt_rectangle_filled(bubble_x, bubble_x + bubble_w, bubble_y, bubble_y + bubble_h, (0, 0, 0, 150))
            arcade.draw_lrbt_rectangle_outline(bubble_x, bubble_x + bubble_w, bubble_y, bubble_y + bubble_h, arcade.color.AMETHYST, 1)
            
            # Сам текст
            arcade.draw_text(
                text,
                bubble_x + 10,
                bubble_y + bubble_h - 10,
                arcade.color.WHITE,
                12,
                width=bubble_w - 20,
                multiline=True,
                anchor_x="left",
                anchor_y="top"
            )
