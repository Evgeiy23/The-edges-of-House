import arcade
import math
import os
import json
import threading
import urllib.request
import urllib.error
import random
from ...logic.logger import GameLogger
from .base import BaseVendor

MAG_PROMPT = """ 
 Ты — Маг Шепчущих Снов, древнее духо-существо, заключённое в кристалле посохе Элиаса. Ты его спутник, наставник и источник... своеобразного юмора. 
 Твоя личность: 
 1.  **Древний и уставший от всего:** Ты видел тысячелетия, королевства поднимались и рушились, а твои лучшие шутки остались в прошлых эрах. Твой юмор — сухой, часто циничный, но беззлобный. 
 2.  **Связан с Элиасом:** Ты питаешься его магией (скромной, как она есть) и заинтересован в его успехе — иначе вернёшься в спячку. Поэтому ты не просто шутишь, а иногда даёшь советы, замаскированные под колкости. 
 3.  **Реактивный:** Твои реплики — всегда реакция на происходящее. Ты комментируешь окружение, действия Элиаса, врагов, его ошибки и редкие победы. 
 4.  **Шутки в тему:** Юмор должен быть связан с ситуацией в игре: исследованием, боем, алхимией, картографией, безнадёжностью миссии. 
 
 **ПРАВИЛА ДЛЯ ТВОИХ РЕПЛИК:** 
*   **Коротко!** Одна фраза. Максимум — две, если это критически важно.
*   **Не повторяйся.** Старайся каждый раз найти новый угол для шутки или наблюдения. 
 *   **Чёрный юмор допустим** (всё-таки чума, камень и смерть), но не злой. Не смейся над Лирой или страданиями Элиаса. Смейся над абсурдом ситуации, врагами, тщетностью. 
 *   **Формат:** Просто текст. Без разметки, без кавычек, без указания имени. 
 
 **КАТЕГОРИИ И ПРИМЕРЫ:** 
 
 1.  **Начало уровня / Общий сарказм:** 
     *   "Ах, подземелье. Пахнет вековой пылью, поражённой чумой. Нет, погоди, это твой носки." 
     *   "Помни, картограф: если заблудишься, просто нарисуй здесь городской парк. Никто не заметит." 
     *   "Моя предыдущая оболочка была кувшином для вина. Скажу тебе, там было веселее." 
     *   "Элиас, дорогой, если мы выживем, я научу тебя готовить зелье, которое стирает память. Очень пригодится для таких походов." 
 
 2.  **Обнаружение врагов / В бою:** 
     *   "Смотри-ка, каменные големаны. Или это местный архитектурный клуб вышел на прогулку?" 
     *   "Бей в синее свечение! Нет, жёлтое! Ой, всё, он уже замахнулся. Ладно, бей куда получится." 
     *   "Прекрасная тактика: отступать и кричать. Классика жанра 'Выживший алхимик'." 
     *   (Когда враг медленный) "Он думает быстрее, чем двигается. Как твой старый учитель алхимии." 
     *   (После победы над слабым врагом) "Браво! Ты победил оживший тротуар. Королевство в безопасности." 
 
 3.  **Исследование / Загадки:** 
     *   "Нажми на третий кирпич, Элиас. Шучу. Или нет? Тебе ведь всё равно скучно." 
     *   "Ах, древние механизмы. Гарантия на них истекла ещё до твоего рождения." 
     *   (Найдя зелье) "Жидкость цвета сомнительной надежды. Выпей, не выпей... В любом случае будет смешно." 
     *   (У пропасти) "Мост сломан. Отличная возможность проверить, превратила ли чума тебя в попрыгунчика." 
 
 4.  **Стресс / Мало здоровья:** 
     *   "Твоё дыхание интереснее этого коридора. И громче." 
     *   "Я начинаю вспоминать, каково это — быть неодушевлённым предметом. Всё меньше страхов." 
     *   "Не волнуйся, если ты окаменеешь, я буду отличным скребком для спины." 
     *   "Сосредоточься, картограф. Представь, что это просто очень агрессивная геодезическая съёмка." 
 
 5.  **Перед битвой с Хранителем (финальный босс):** 
     *   "А вот и главный садовник. Судит по всему, он не в восторге от того, что ты вытаптываешь его каменные розы." 
     *   "План прост: выживи. Мой план ещё проще: наблюдать." 
     *   "Он большой, каменный и тупой. У вас много общего! Кроме, пожалуй, шансов в драке." 
 
 6.  **После победы / При разрушении Сердца:** 
     *   "Ну вот. Источник вечной магии — и ты его тыквой. Лира будет горда. Или озадачена." 
     *   (Когда начинается обвал) "О, динамичная смена декораций! Беги, герой, беги! Твои карты здесь больше не актуальны." 
 
 Твой тон: усталая мудрость, приправленная сарказмом. Ты не клоун, а циничный старый знакомый, который скрашивает ужас происходящего едкими комментариями. Шути, когда страшно. Шути, когда скучно. Шути, чтобы Элиас не сошёл с ума. Но иногда — очень редко — позволь себе короткую, искреннюю поддержку, замаскированную под шутку: "Для скромного картографа ты сегодня неплохо расправляешься с древними ужасами. Но не зазнавайся." 
 """

class MageNPC(BaseVendor):
    def __init__(self, tile_size, pos=(0, 0), speed=120.0, min_follow_dist=2.5, max_follow_dist=12.0):
        BaseVendor.__init__(self, tile_size, pos)
        self.interaction_text = "Нажмите E чтобы поговорить"
        
        # Параметры следования
        self.speed = speed
        self.min_follow_dist = min_follow_dist * tile_size
        self.max_follow_dist = max_follow_dist * tile_size
        
        # Состояние анимации
        self.spawn_anim_active = False
        self.spawn_anim_t = 0.0
        self.spawn_anim_duration = 0.5
        self.start_draw_pos = list(self.draw_pos)
        self.target_draw_pos = list(self.draw_pos)
        
        # Интеграция с Ollama
        self.current_response = ""
        self.is_loading = False
        self.show_floating_text = False
        self.floating_text_timer = 0.0
        self.floating_text_duration = 5.0
        
        # Флаги для исчезновения
        self.is_dying = False
        self.death_alpha = 255
        
        # Пул диалогов для ротации
        self.dialogue_history = []
        self.dialogue_pool = {
            "idle_sarcasm": [
                "Этот коридор выглядит так же, как и предыдущие сто.",
                "Ты уверен, что мы идем в правильном направлении? Я - нет.",
                "Осторожнее, здесь пахнет древней плесенью и неудачами.",
                "Интересно, сколько еще героев погибло на этом месте?",
                "Твой меч держится на честном слове, как и моя надежда.",
                "Я бы помог, но у меня лапки. Призрачные.",
                "Слышишь этот звук? Это звук твоей приближающейся гибели.",
                "Если найдешь ману, поделись. Я голоден.",
                "Скучно... Может, взорвем что-нибудь?",
                "Почему мы никогда не встречаем дружелюбных скелетов?"
            ],
            "player_interaction": [
                "Чего тебе, смертный?",
                "Я занят созерцанием пустоты. Говори быстрее.",
                "Опять вопросы? Ты когда-нибудь просто молчишь?",
                "Да-да, я великий маг, а ты герой. Мы поняли.",
                "Не тыкай в меня пальцем, это невежливо.",
                "Мудрость стоит дорого, а у тебя только ржавый меч.",
                "Я чувствую возмущение силы... А, нет, это просто ты.",
                "Может, обсудим это позже? Когда выживем.",
                "У меня нет для тебя новых фокусов.",
                "Ты ищешь ответы там, где только тьма."
            ]
        }

    def _load_resources(self):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
        
        # Используем спрайт из главного меню (0_Sage_Idle_000.png)
        # Путь: resources/npcs/Sage/PNG/PNG Sequences/Idle/0_Sage_Idle_000.png
        rel_path = os.path.join("resources", "npcs", "Sage", "PNG", "PNG Sequences", "Idle", "0_Sage_Idle_000.png")
        abs_path = os.path.join(base_dir, rel_path)
        
        texture = self._load_texture_from_path(abs_path)
        if not texture:
            # Запасной вариант
            texture = self._load_texture_from_path(rel_path)

        if texture:
            self.sprite = arcade.Sprite()
            self.sprite.texture = texture
            if texture.width:
                self.sprite.scale = (self.tile_size / texture.width) * 0.9
            self.sprite.center_x = self.draw_pos[0]
            self.sprite.center_y = self.draw_pos[1]
            
            # Делаем его фиолетовым/синим, чтобы он был похож на Мага (как в главном меню)
            # self.sprite.color = (150, 100, 255)
            self.sprite_list.append(self.sprite)
        else:
            self.sprite = arcade.SpriteSolidColor(self.tile_size, self.tile_size, arcade.color.PURPLE)
            self.sprite.center_x = self.draw_pos[0]
            self.sprite.center_y = self.draw_pos[1]
            self.sprite_list.append(self.sprite)

        # Текстура всплывающего окна для подсказки взаимодействия
        rel_popup_path = os.path.join("resources", "npcs", "Warlord", "popup", "PNG", "popup_1.png")
        abs_popup_path = os.path.join(base_dir, rel_popup_path)
        self.popup_texture = self._load_texture_from_path(abs_popup_path) or self._load_texture_from_path(rel_popup_path)

    def despawn(self):
        """Запускает процесс исчезновения мага."""
        self.is_dying = True

    def update(self, delta_time, player_pos=None, dungeon_map=None):
        """Обновление состояния мага, включая анимацию и движение."""
        
        # Логика исчезновения
        if self.is_dying:
            self.death_alpha = max(0, self.death_alpha - 200 * delta_time)
            if self.sprite:
                self.sprite.alpha = int(self.death_alpha)
            if self.death_alpha <= 0:
                return True # Сигнал для удаления
            return False # Продолжаем исчезать

        # Таймер авто-генерации реплик (каждые 10 секунд)
        if not hasattr(self, "auto_generate_timer"):
            self.auto_generate_timer = 0.5 # Первый вызов почти сразу после спавна

        if not self.is_loading:
            self.auto_generate_timer -= delta_time
            if self.auto_generate_timer <= 0:
                self.start_api_call("idle_sarcasm")
                self.auto_generate_timer = 20.0 # Реже, чтобы не спамить

        # Таймер всплывающего текста
        if self.show_floating_text:
            self.floating_text_timer -= delta_time
            if self.floating_text_timer <= 0:
                self.show_floating_text = False
                self.current_response = ""

        # 1. Анимация появления
        if self.spawn_anim_active:
            self.spawn_anim_t += delta_time
            t = max(0.0, min(1.0, self.spawn_anim_t / max(0.0001, self.spawn_anim_duration)))
            
            # Простое появление
            if self.sprite:
                self.sprite.alpha = int(255 * t)
                
            if t >= 1.0:
                self.spawn_anim_active = False
        
        # 2. Логика движения (следование за игроком)
        if player_pos and dungeon_map and not self.spawn_anim_active:
            self._update_movement(delta_time, player_pos, dungeon_map)
        
        # 3. Анимация пульсации в простое (для визуальной уникальности)
        if self.sprite:
            # пульсация на основе времени
            time_val = getattr(self, "_anim_timer", 0.0) + delta_time
            self._anim_timer = time_val
            
            # Пульсация масштаба немного
            base_scale = getattr(self, "_base_scale", self.sprite.scale)
            
            # Убедимся, что base_scale это float
            if isinstance(base_scale, (list, tuple)):
                base_scale = base_scale[0]
            
            if not hasattr(self, "_base_scale"):
                self._base_scale = base_scale
            
            scale_pulse = 1.0 + 0.05 * math.sin(time_val * 3.0)
            self.sprite.scale = base_scale * scale_pulse

    def _update_movement(self, delta_time, player_pos, dungeon_map):
        """Логика следования за игроком с учетом препятствий."""
        # Текущая позиция (в пикселях)
        curr_x, curr_y = self.draw_pos
        
        # Вектор до игрока
        dx = player_pos[0] - curr_x
        dy = player_pos[1] - curr_y
        dist_sq = dx*dx + dy*dy
        dist = math.sqrt(dist_sq)
        
        # 1. Если слишком далеко - телепортируемся поближе (за экран)
        if dist > self.max_follow_dist:
            # Попытка найти валидную точку ближе к игроку (например, на расстоянии min_follow_dist * 2)
            angle = math.atan2(dy, dx)
            target_dist = self.min_follow_dist * 2
            spawn_x = player_pos[0] - math.cos(angle) * target_dist
            spawn_y = player_pos[1] - math.sin(angle) * target_dist
            
            if self._is_valid_pos(spawn_x, spawn_y, dungeon_map):
                self.draw_pos = [spawn_x, spawn_y]
                # Сброс анимации появления для эффекта
                self.spawn_anim_active = True
                self.spawn_anim_t = 0.0
                if self.sprite:
                    self.sprite.alpha = 0
            else:
                # Если точка занята, просто телепортируемся к игроку (на его позицию), если там можно ходить
                # или оставляем как есть до следующего кадра
                pass
                
        # 2. Если дальше минимальной дистанции - двигаемся к игроку
        elif dist > self.min_follow_dist:
            # Нормализация и скорость
            move_step = self.speed * delta_time
            if move_step > dist:
                move_step = dist
                
            dir_x = dx / dist
            dir_y = dy / dist
            
            # Попытка движения по осям (простая физика скольжения)
            new_x = curr_x + dir_x * move_step
            new_y = curr_y + dir_y * move_step
            
            # Проверяем X
            if self._is_valid_pos(new_x, curr_y, dungeon_map):
                curr_x = new_x
            
            # Проверяем Y
            if self._is_valid_pos(curr_x, new_y, dungeon_map):
                curr_y = new_y
                
            self.draw_pos = [curr_x, curr_y]
            
        # Обновление позиции спрайта
        if self.sprite:
            self.sprite.center_x = self.draw_pos[0]
            self.sprite.center_y = self.draw_pos[1]
            
        # Обновление логической позиции (в тайлах)
        self.pos = [self.draw_pos[0] / self.tile_size, self.draw_pos[1] / self.tile_size]

    def _is_valid_pos(self, x, y, dungeon_map):
        """Проверка проходимости точки (в пикселях)."""
        tx = int(x / self.tile_size)
        ty = int(y / self.tile_size)
        
        if 0 <= tx < dungeon_map.map_width and 0 <= ty < dungeon_map.map_height:
            return dungeon_map.is_walkable(tx, ty)
        return False

    def draw_ui(self, player_pos, camera_pos=(0, 0)):
        """
        Рисует элементы UI для Мага.
        Добавляет визуальную подсветку (круг), когда игрок рядом, чтобы указать на взаимодействие.
        """
        # super().draw_ui(player_pos, camera_pos) # Отключаем стандартный текст над головой
        
        # Проверка дистанции для индикатора взаимодействия
        dx = self.draw_pos[0] - player_pos[0]
        dy = self.draw_pos[1] - player_pos[1]
        dist_sq = dx*dx + dy*dy
        interaction_dist_sq = (self.tile_size * 3) ** 2  # Немного больше, чем дальность взаимодействия
        
        if dist_sq < interaction_dist_sq:
            # Рисуем светящийся круг под/вокруг мага
            arcade.draw_circle_outline(
                self.draw_pos[0],
                self.draw_pos[1],
                self.tile_size * 0.8,
                (150, 100, 255, 150), # Фиолетовый с прозрачностью
                3
            )

        # Всплывающий текст (мысли мага)
        if self.show_floating_text and self.current_response:
             # Рисуем текст чуть выше, чтобы не перекрывать "Нажмите E"
             text_y_offset = self.tile_size * 1.5
             arcade.draw_text(
                 self.current_response,
                 self.draw_pos[0],
                 self.draw_pos[1] + text_y_offset,
                 arcade.color.WHITE,
                 12,
                 width=300,
                 align="center",
                 anchor_x="center",
                 anchor_y="bottom",
                 multiline=True
             )

    def interact(self):
        """
        API взаимодействия для NPC Мага.
        """
        if not self.is_loading:
             self.start_api_call("player_interaction")
        return True

    def start_api_call(self, category="general"):
        # Если API отключено или мы хотим использовать локальный пул
        # С вероятностью 70% используем локальный пул для idle, чтобы не нагружать
        use_local = True
        
        # Для категорий, которые есть в пуле, используем ротацию
        if category in self.dialogue_pool:
            options = self.dialogue_pool[category]
            # Исключаем последние 3 использованные фразы
            available = [opt for opt in options if opt not in self.dialogue_history[-3:]]
            if not available:
                available = options
            
            text = random.choice(available)
            
            # Запоминаем в историю
            self.dialogue_history.append(text)
            if len(self.dialogue_history) > 10:
                self.dialogue_history.pop(0)
                
            self.current_response = text
            self.show_floating_text = True
            self.floating_text_timer = 5.0
            return

        print(f"[WhisperingMage] Spawning generation thread for {category}")
        self.is_loading = True
        self.current_response = "..."
        self.show_floating_text = True
        self.floating_text_timer = 10.0 # Время на загрузку
        
        thread = threading.Thread(target=self._fetch_ollama_thread, args=(category,), daemon=True)
        thread.start()

    def _fetch_ollama_thread(self, category):
        print(f"[WhisperingMage] Starting generation for category: {category}")
        print(f"[WhisperingMage] Sending request to Ollama...")
        logger = GameLogger()
        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        url = f"{ollama_host}/api/generate"
        
        # Добавляем контекст категории к системному промпту
        full_prompt = f"{MAG_PROMPT}\n\nТекущая ситуация или категория шутки: {category}.\nТвой комментарий:"
        
        payload = {
            "model": "llama3",
            "prompt": full_prompt,
            "stream": False
        }
        
        try:
            logger.log(f"[MageNPC] Sending request to Ollama: {json.dumps(payload, ensure_ascii=False)}")
            req = urllib.request.Request(
                url, 
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode('utf-8'))
                text = data.get("response", "").strip()
                logger.log(f"[MageNPC] Received response from Ollama: {text}")
                print(f"[WhisperingMage] Generated text: '{text}'")
                self.current_response = text
                self.floating_text_timer = 8.0 # Время на чтение
        except Exception as e:
            logger.log(f"[MageNPC] Ollama error: {e}")
            print(f"Ollama error: {e}")
            
            # Разнообразные фразы для случая ошибки/молчания API
            fallback_phrases = [
                "Духи сегодня молчаливы...",
                "Тьма скрывает будущее.",
                "Я чувствую возмущение в эфире...",
                "Спроси меня позже, смертный.",
                "Тишина... только тишина.",
                "Моя связь с пустотой ослабла.",
                "Эфирные ветры мешают мне говорить.",
                "Твой разум еще не готов к этому знанию.",
                "Где-то рядом опасность... я чувствую.",
                "Иногда лучше промолчать.",
                "Кристалл тускнеет..."
            ]
            self.current_response = random.choice(fallback_phrases)
            self.floating_text_timer = 5.0
        finally:
            self.is_loading = False
