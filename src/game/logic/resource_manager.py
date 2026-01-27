import arcade
import os

class ResourceManager:
    _instance = None
    _textures = {}
    _sprites = {}
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = ResourceManager()
        return cls._instance
    
    def get_texture(self, file_path):
        """
        Returns a cached texture. If not cached, loads it.
        """
        if file_path in self._textures:
            return self._textures[file_path]
        
        if os.path.exists(file_path):
            try:
                texture = arcade.load_texture(file_path)
                self._textures[file_path] = texture
                return texture
            except Exception as e:
                print(f"Failed to load texture {file_path}: {e}")
                return None
        return None

    def clear_cache(self):
        self._textures.clear()
        self._sprites.clear()
