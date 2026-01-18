# Рефакторинг кода - Разбиение больших файлов на модули

## Структура модулей для game_window.py

Файл `game_window.py` был разбит на следующие модули:

### 1. `game_window_rendering.py`
Содержит все методы отрисовки:
- `draw_map()` - отрисовка карты, игрока, боссов
- `draw_player_health()` - полоска здоровья игрока
- `draw_inventory_bar()` - панель инвентаря
- `draw_minimap()` - миникарта
- `draw_passage_opening_effect()` - эффект открытия прохода
- `draw_death_message()` - сообщение о смерти
- `draw_player_health_above()` - здоровье над игроком

### 2. `game_window_inventory.py`
Содержит методы управления инвентарем:
- `spawn_dropped_item()` - создание предмета на земле
- `apply_inventory_effects()` - применение эффектов предметов
- `get_item_description()` - описание предмета

### 3. `game_window_story.py`
Содержит методы управления историей:
- `draw_story_text()` - отрисовка текста истории
- `setup_story_ui()` - настройка UI истории
- `on_next_click()` - обработка кнопки "Далее"
- `toggle_story_ui()` - переключение UI истории
- `display_story_text()` - инициализация текста истории

### 4. `game_window_music.py`
Содержит методы управления музыкой:
- `find_music_file()` - поиск музыкального файла
- `play_game_music()` - воспроизведение игровой музыки
- `stop_game_music()` - остановка музыки
- `play_suspense_music()` - музыка в комнате с боссом
- `stop_suspense_music()` - остановка музыки босса

## Использование

Основной класс `GameWindow` теперь наследуется от всех миксинов:

```python
class GameWindow(arcade.View, GameWindowRendering, GameWindowInventory, 
                 GameWindowStory, GameWindowMusic):
```

Все методы из модулей автоматически доступны в основном классе.

## Структура модулей для start_window.py

Файл `start_window.py` также был разбит на модули:

### 1. `start_window_music.py`
Содержит методы управления музыкой:
- `find_music_file()` - поиск музыкального файла
- `play_main_music()` - воспроизведение основной музыки
- `pause_main_music()` - приостановка музыки
- `resume_main_music()` - возобновление музыки
- `play_settings_music()` - музыка в настройках
- `stop_settings_music()` - остановка музыки настроек

### 2. `start_window_background.py`
Содержит методы управления фоном:
- `_initialize_background_list()` - инициализация списка фонов
- `_ensure_background_sprite()` - обеспечение загрузки фона
- `update_background_scale()` - обновление масштаба фона

### 3. `start_window_settings.py`
Содержит методы управления настройками:
- `load_settings()` - загрузка настроек
- `save_settings()` - сохранение настроек
- `get_window_mode_string()` - получение режима окна
- `apply_display_settings()` - применение настроек отображения
- `get_native_resolution()` - получение нативного разрешения
- `get_available_resolutions()` - список доступных разрешений

## Использование

Основной класс `StartWindow` теперь наследуется от всех миксинов:

```python
class StartWindow(arcade.View, StartWindowMusic, StartWindowBackground, StartWindowSettings):
```

## Следующие шаги для полного рефакторинга

1. ✅ Разбить `game_window.py` на модули - ВЫПОЛНЕНО
2. ✅ Разбить `start_window.py` на модули - ВЫПОЛНЕНО
3. Опционально: Создать модули для обработки ввода (`game_window_input.py`)
4. Опционально: Создать модули для игровой логики (`game_window_logic.py`)
5. Опционально: Удалить дублирующиеся методы из основных файлов (они теперь в модулях, но оставлены для обратной совместимости)

## Преимущества

- ✅ Улучшенная читаемость кода
- ✅ Легче найти нужный функционал
- ✅ Проще тестировать отдельные компоненты
- ✅ Упрощенная поддержка и расширение
