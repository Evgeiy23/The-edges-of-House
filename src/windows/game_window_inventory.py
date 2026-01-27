"""
Модуль для управления инвентарем и предметами
"""
import arcade
import time
from game.items.effects import ITEM_EFFECTS


class GameWindowInventory:
    """Класс-миксин для методов управления инвентарем"""
    
    def spawn_dropped_item(self, icon_id, px, py, ignore_player_duration=0.0, velocity=(0, 0)):
        """Создает предмет на земле"""
        tex = self.item_textures.get(icon_id)
        if not tex:
            return
        sp = arcade.Sprite()
        sp.texture = tex
        if tex.width:
            sp.scale = (self.tile_size / tex.width) * 0.7
        sp.center_x = px
        sp.center_y = py
        
        # Physics properties
        sp.change_x = velocity[0]
        sp.change_y = velocity[1]
        
        props = {"icon_id": icon_id}
        if ignore_player_duration > 0:
            props["ignore_until"] = time.time() + ignore_player_duration
        sp.properties = props
        self.dropped_item_sprites.append(sp)

    def apply_inventory_effects(self):
        """Применяет эффекты предметов из инвентаря к игроку"""
        if not self.player:
            return

        # Reset to base stats
        self.player.move_speed = self.player.base_move_speed
        self.player.attack_duration = self.player.base_attack_duration
        self.player.health_regen_amount = self.player.base_health_regen_amount
        self.player.max_health = self.player.base_max_health
        self.player.has_double_strike = False
        self.player.bonus_damage_percent = 0.0
        self.player.bonus_damage_flat = 0
        self.player.dodge_chance = 0.0
        
        # Accumulators
        move_mult = 1.0
        atk_speed_mult = 1.0
        regen_mult = 1.0
        
        for item in self.inventory:
            iid = item.get("icon_id")
            effect = ITEM_EFFECTS.get(iid)
            if not effect:
                continue
            
            self.player.bonus_damage_percent += effect.get("dmg_pct", 0)
            self.player.bonus_damage_flat += effect.get("dmg_flat", 0)
            move_mult += effect.get("move_pct", 0)
            atk_speed_mult += effect.get("atk_speed_pct", 0)
            regen_mult += effect.get("regen_pct", 0)
            self.player.dodge_chance += effect.get("dodge", 0)
            
            if effect.get("special") == "double_strike":
                self.player.has_double_strike = True

        # Finalize
        self.player.move_speed *= max(0.1, move_mult)
        # Attack speed increases means duration decreases.
        self.player.attack_duration = self.player.base_attack_duration / max(0.1, 1.0 + atk_speed_mult)
        
        self.player.health_regen_amount = int(self.player.base_health_regen_amount * max(1.0, 1.0 + regen_mult))

    def get_item_description(self, icon_id):
        """Возвращает описание предмета"""
        # Check if it has an effect description first
        if icon_id in ITEM_EFFECTS and "desc" in ITEM_EFFECTS[icon_id]:
            return ITEM_EFFECTS[icon_id]["desc"]
        return f"Предмет #{icon_id}"
