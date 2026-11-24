import sys
import time
from pathlib import Path

from .assets import AssetManager
from .game import Game
from .hardware import HardwareConfigurationError, RaspberryPiDisplay, RaspberryPiInput, validate_hardware_config
from .renderer import Renderer

FRAME_TIME = 1 / 30


def run() -> int:
    root = Path(__file__).resolve().parents[1]
    try:
        config = validate_hardware_config(root / "config/hardware.adafruit-tft-bonnet.json")
        controls = RaspberryPiInput(config)
        display = RaspberryPiDisplay(config)
    except HardwareConfigurationError as exc:
        print(f"하드웨어 설정 오류: {exc}", file=sys.stderr)
        return 2

    game = Game(root)
    renderer = Renderer(AssetManager(root / "assets"))
    last_update = time.perf_counter()
    try:
        while True:
            started = time.perf_counter()
            game.update(controls.poll(), min(started - last_update, 0.05))
            last_update = started
            display.present(renderer.render(game))
            delay = FRAME_TIME - (time.perf_counter() - started)
            if delay > 0:
                time.sleep(delay)
    except KeyboardInterrupt:
        pass
    finally:
        display.close()
        controls.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
