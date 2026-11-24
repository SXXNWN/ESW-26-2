from pathlib import Path

from PIL import Image


class AssetManager:
    def __init__(self, assets_dir: Path) -> None:
        self.root = assets_dir
        self._cache: dict[str, Image.Image] = {}

    def get(self, relative_path: str) -> Image.Image:
        if relative_path not in self._cache:
            path = self.root / relative_path
            with Image.open(path) as source:
                mode = "RGB" if source.mode == "RGB" else "RGBA"
                self._cache[relative_path] = source.convert(mode).copy()
        return self._cache[relative_path]
