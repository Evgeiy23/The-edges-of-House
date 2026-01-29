import os
import datetime

class GameLogger:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GameLogger, cls).__new__(cls)
            cls._instance.log_file = "game_events.log"
            # Создать/очистить файл журнала при запуске, если нужно, или добавить
            # Пока что давайте добавим
        return cls._instance

    def log(self, message):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        print(formatted_message)
        
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(formatted_message + "\n")
        except Exception as e:
            print(f"Failed to write to log: {e}")

    def log_dungeon_generation(self, seed, rooms_count, corridors_count, player_pos, mage_pos, unique_id=None):
        self.log(f"--- Dungeon Generated ---")
        if unique_id:
            self.log(f"Unique ID: {unique_id}")
        self.log(f"Seed: {seed}")
        self.log(f"Rooms: {rooms_count}, Corridors: {corridors_count}")
        self.log(f"Player Spawn: {player_pos}")
        self.log(f"Mage Spawn: {mage_pos}")

    def log_boss_death(self, boss_type, level):
        self.log(f"Boss {boss_type} defeated at Level {level}. Exit opened.")

    def log_level_transition(self, from_level, to_level):
        self.log(f"Transitioning from Level {from_level} to {to_level}.")
