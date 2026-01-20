import arcade
import os
import threading
from groq import Groq
import math
from PIL import Image

class SageNPC:
    def __init__(self, tile_size, pos=(0, 0)):
        self.tile_size = tile_size
        self.pos = list(pos)
        self.draw_pos = [pos[0] * tile_size + tile_size // 2,
                         pos[1] * tile_size + tile_size // 2]
        
        self.sprite = None
        self.sprite_list = arcade.SpriteList()
        self.popup_texture = None
        self.alpha = 255
        self.spawn_anim_active = False
        self.spawn_anim_t = 0.0
        self.spawn_anim_duration = 0.35
        self.start_draw_pos = list(self.draw_pos)
        self.target_draw_pos = list(self.draw_pos)
        self.orientation = "front"
        
        # Состояние взаимодействия
        self.is_interacting = False
        self.interaction_text = "Нажмите E чтобы поговорить"
        self.current_response = ""
        self.is_loading = False
        self.show_popup = False
        
        # API Клиент
        self.api_key = os.getenv("GROQ_API_KEY") or None
        
        # Text objects optimization
        self.text_object = None
        self.last_text_content = ""
        self.interaction_text_object = None
        
        self._load_resources()
        
    def _load_resources(self):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        rel_sage_path = os.path.join("resources", "торговец + маг", "Sage", "PNG", "PNG Sequences", "Chagrin", "0_Sage_Chagrin_008.png")
        abs_sage_path = os.path.join(base_dir, rel_sage_path)
        candidates = [abs_sage_path, rel_sage_path]
        loaded = False
        for p in candidates:
            exists = os.path.exists(p)
            readable = os.access(p, os.R_OK)
            size = None
            try:
                size = os.path.getsize(p) if exists else None
            except Exception:
                size = None
            print(f"[SageTexture] path='{p}' exists={exists} readable={readable} size={size}")
            if not exists or not readable:
                continue
            texture = None
            try:
                texture = arcade.load_texture(p)
            except Exception as e:
                print(f"[SageTexture] arcade.load_texture failed: {e}")
                try:
                    img = Image.open(p).convert("RGBA")
                    texture = arcade.Texture(os.path.basename(p), img)
                except Exception as e2:
                    print(f"[SageTexture] PIL fallback failed: {e2}")
                    texture = None
            if texture:
                try:
                    sprite = arcade.Sprite()
                    sprite.texture = texture
                    if texture.width:
                        sprite.scale = (self.tile_size / texture.width) * 0.9
                    sprite.center_x = self.draw_pos[0]
                    sprite.center_y = self.draw_pos[1]
                    sprite.alpha = self.alpha
                    self.sprite = sprite
                    self.sprite_list.append(self.sprite)
                    print(f"[SageTexture] loaded width={texture.width} height={texture.height} scale={getattr(sprite, 'scale', None)}")
                    loaded = True
                    break
                except Exception as e:
                    print(f"[SageTexture] sprite init failed: {e}")
                    self.sprite = None
        if not loaded:
            print(f"[SageTexture] failed to load, using fallback")
            self.sprite = arcade.SpriteSolidColor(self.tile_size, self.tile_size, arcade.color.BLUE)
            self.sprite.center_x = self.draw_pos[0]
            self.sprite.center_y = self.draw_pos[1]
            self.sprite.alpha = self.alpha
            self.sprite_list.append(self.sprite)

        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        rel_popup_path = os.path.join("resources", "торговец + маг", "Warlord", "popup", "PNG", "popup_1.png")
        abs_popup_path = os.path.join(base_dir, rel_popup_path)
        popup_candidates = [abs_popup_path, rel_popup_path]
        self.popup_texture = None
        for p in popup_candidates:
            exists = os.path.exists(p)
            readable = os.access(p, os.R_OK)
            print(f"[SagePopup] path='{p}' exists={exists} readable={readable}")
            if not exists or not readable:
                continue
            try:
                self.popup_texture = arcade.load_texture(p)
                print(f"[SagePopup] loaded")
                break
            except Exception as e:
                print(f"[SagePopup] load failed: {e}")

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

    def draw(self):
        if self.sprite_list:
            self.sprite_list.draw()

    def draw_ui(self, player_pos, camera_pos=(0,0)):
        # Проверка дистанции до игрока
        dx = self.draw_pos[0] - player_pos[0]
        dy = self.draw_pos[1] - player_pos[1]
        dist = math.sqrt(dx*dx + dy*dy)
        
        interaction_dist = self.tile_size * 2
        
        if dist < interaction_dist:
            # Рисуем подсказку "Нажмите E" над Мудрецом
            if not self.show_popup:
                if not self.interaction_text_object:
                    self.interaction_text_object = arcade.Text(
                        self.interaction_text,
                        self.draw_pos[0],
                        self.draw_pos[1] + self.tile_size,
                        arcade.color.WHITE,
                        14,
                        anchor_x="center",
                        anchor_y="bottom"
                    )
                self.interaction_text_object.draw()
        else:
            self.show_popup = False # Закрываем окно, если игрок отошел

        if self.show_popup and self.popup_texture:
            # Рисуем окно диалога в координатах мира (или экрана, если нужно)
            # В идеале UI рисуется отдельным проходом с камерой без смещения.
            # Но здесь мы рисуем рядом с NPC для простоты.
            
            popup_width = 400
            popup_height = 200
            popup_x = self.draw_pos[0]
            popup_y = self.draw_pos[1] + self.tile_size * 2.5
            
            # Рисуем текстуру
            arcade.draw_texture_rectangle(
                popup_x, popup_y,
                popup_width, popup_height,
                self.popup_texture
            )
            
            # Рисуем текст внутри окна
            text_content = self.current_response if not self.is_loading else "Мудрец размышляет..."
            
            if text_content != self.last_text_content or not self.text_object:
                self.last_text_content = text_content
                self.text_object = arcade.Text(
                    text_content,
                    popup_x - popup_width * 0.4,
                    popup_y + popup_height * 0.3,
                    arcade.color.BLACK,
                    12,
                    width=int(popup_width * 0.8),
                    multiline=True,
                    anchor_x="left",
                    anchor_y="top"
                )
            
            if self.text_object:
                self.text_object.draw()

    def interact(self):
        if self.show_popup:
            # Если окно уже открыто, можно обновить текст
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
            
            # Используем контекст игры для промпта
            prompt = "Ты мудрый старец в подземелье. Дай короткий совет герою (максимум 2 предложения)."
            
            completion = client.chat.completions.create(
                model="llama3-8b-8192", # Используем стабильную модель Groq
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
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
            self.current_response = f"Духи молчат... (Ошибка связи)"
        finally:
            self.is_loading = False
