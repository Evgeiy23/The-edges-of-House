
import arcade
import os
import threading
from groq import Groq
from .base import BaseVendor

class SageNPC(BaseVendor):
    def __init__(self, tile_size, pos=(0, 0)):
        super().__init__(tile_size, pos)
        
        # Клиент API
        self.api_key = os.getenv("GROQ_API_KEY") or None
        self.current_response = ""
        self.is_loading = False
        
        # Анимация
        self.spawn_anim_active = False
        self.spawn_anim_t = 0.0
        self.spawn_anim_duration = 0.35
        self.start_draw_pos = list(self.draw_pos)
        self.target_draw_pos = list(self.draw_pos)

    def _load_resources(self):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
        # Использование известного пути из исходного файла
        rel_sage_path = os.path.join("resources", "npcs", "Sage", "PNG", "PNG Sequences", "Chagrin", "0_Sage_Chagrin_008.png")
        abs_sage_path = os.path.join(base_dir, rel_sage_path)
        
        texture = self._load_texture_from_path(abs_sage_path)
        if not texture:
             # Попытка использовать относительный путь к текущему рабочему каталогу, если абсолютный путь не сработал
             texture = self._load_texture_from_path(rel_sage_path)

        if texture:
            self.sprite = arcade.Sprite()
            self.sprite.texture = texture
            if texture.width:
                self.sprite.scale = (self.tile_size / texture.width) * 0.9
            self.sprite.center_x = self.draw_pos[0]
            self.sprite.center_y = self.draw_pos[1]
            self.sprite_list.append(self.sprite)
        else:
            # print("[SageNPC] Using fallback sprite")
            self.sprite = arcade.SpriteSolidColor(self.tile_size, self.tile_size, arcade.color.BLUE)
            self.sprite.center_x = self.draw_pos[0]
            self.sprite.center_y = self.draw_pos[1]
            self.sprite_list.append(self.sprite)

        # Всплывающее окно
        rel_popup_path = os.path.join("resources", "npcs", "Warlord", "popup", "PNG", "popup_1.png")
        abs_popup_path = os.path.join(base_dir, rel_popup_path)
        self.popup_texture = self._load_texture_from_path(abs_popup_path) or self._load_texture_from_path(rel_popup_path)

    def update(self, delta_time):
        if self.spawn_anim_active:
            self.spawn_anim_t += delta_time
            t = max(0.0, min(1.0, self.spawn_anim_t / max(0.0001, self.spawn_anim_duration)))
            nx = self.start_draw_pos[0] + (self.target_draw_pos[0] - self.start_draw_pos[0]) * t
            ny = self.start_draw_pos[1] + (self.target_draw_pos[1] - self.start_draw_pos[1]) * t
            self.draw_pos[0] = nx
            self.draw_pos[1] = ny
            if self.sprite:
                self.sprite.center_x = nx
                self.sprite.center_y = ny
                self.sprite.alpha = int(255 * t)
            if t >= 1.0:
                self.spawn_anim_active = False

    def get_display_text(self):
        if self.is_loading:
            return "Мудрец размышляет..."
        return self.current_response

    def interact(self):
        if self.show_popup:
             if not self.is_loading:
                self.start_api_call()
        else:
            self.show_popup = True
            if not self.current_response:
                self.start_api_call()

    def start_api_call(self):
        if not self.api_key:
            self.current_response = "Духи молчат... (Ключ API не настроен)"
            self.is_loading = False
            return
        self.is_loading = True
        self.current_response = ""
        thread = threading.Thread(target=self._fetch_text_thread, daemon=True)
        thread.start()

    def _fetch_text_thread(self):
        try:
            if self.api_key:
                os.environ["GROQ_API_KEY"] = self.api_key
            client = Groq()
            prompt = "Ты мудрый старец в подземелье. Дай короткий совет герою (максимум 2 предложения)."
            
            completion = client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[{"role": "user", "content": prompt}],
                temperature=1,
                max_completion_tokens=100,
                top_p=1,
                stream=True,
                stop=None
            )
            
            full_text = ""
            for chunk in completion:
                content = chunk.choices[0].delta.content or ""
                full_text += content
            
            self.current_response = full_text
            
        except Exception as e:
            print(f"Ошибка API: {e}")
            self.current_response = "Духи молчат... (Ошибка связи)"
        finally:
            self.is_loading = False
