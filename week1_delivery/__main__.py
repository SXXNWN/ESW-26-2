from __future__ import annotations

import argparse
import json
import struct
import time
from pathlib import Path

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
WIDTH = HEIGHT = 240
GROUND_Y = 184
WORLD_WIDTH = 1120
SPEED = 112.0
GRAVITY = 650.0
JUMP_SPEED = -250.0


class Game:
    def __init__(self) -> None:
        self.state = "title"
        self.x = 32.0
        self.y = GROUND_Y - 32.0
        self.vy = 0.0
        self.on_ground = True
        self.facing = 1
        self.camera_x = 0.0

    def update(self, pressed: dict[str, bool], dt: float) -> None:
        if self.state == "title":
            if pressed["center"]:
                self.__init__()
                self.state = "playing"
            return
        if self.state == "game_over":
            if pressed["center"]:
                self.state = "title"
            return
        if pressed["b"]:
            self.state = "game_over"
            return

        direction = int(pressed["right"]) - int(pressed["left"])
        if direction:
            self.facing = direction
        if pressed["up"] and self.on_ground:
            self.vy = JUMP_SPEED
            self.on_ground = False

        dt = min(max(dt, 0.0), 0.05)
        self.x = min(max(self.x + direction * SPEED * dt, 0.0), WORLD_WIDTH - 32.0)
        self.vy += GRAVITY * dt
        self.y += self.vy * dt
        if self.y + 32 >= GROUND_Y:
            self.y = GROUND_Y - 32.0
            self.vy = 0.0
            self.on_ground = True
        self.camera_x = min(max(self.x + 16 - WIDTH / 2, 0.0), WORLD_WIDTH - WIDTH)


class Renderer:
    def __init__(self) -> None:
        self.sprites = {
            name: Image.open(ROOT / "assets" / name).convert("RGBA")
            for name in (
                "ui/title_screen_240x240.png",
                "ui/game_over_screen_240x240.png",
                "player/santa_idle.png",
                "player/santa_jump_02.png",
                "player/santa_jump_03.png",
                "tiles/roof_snow.png",
                "tiles/roof_brick.png",
            )
        }

    def render(self, game: Game) -> Image.Image:
        if game.state != "playing":
            name = "ui/title_screen_240x240.png" if game.state == "title" else "ui/game_over_screen_240x240.png"
            return self.sprites[name].convert("RGB")

        frame = Image.new("RGB", (WIDTH, HEIGHT), (10, 18, 38))
        first_x = int(game.camera_x // 16) * 16
        for x in range(first_x, int(game.camera_x) + WIDTH + 16, 16):
            screen_x = round(x - game.camera_x)
            for y in range(GROUND_Y, HEIGHT, 16):
                name = "tiles/roof_snow.png" if y == GROUND_Y else "tiles/roof_brick.png"
                tile = self.sprites[name]
                frame.paste(tile, (screen_x, y), tile)
        if not game.on_ground:
            name = "player/santa_jump_02.png" if game.vy < 0 else "player/santa_jump_03.png"
        else:
            name = "player/santa_idle.png"
        sprite = self.sprites[name]
        if game.facing < 0:
            sprite = ImageOps.mirror(sprite)
        frame.paste(sprite, (round(game.x - game.camera_x), round(game.y)), sprite)
        return frame


class PiIO:
    def __init__(self, config: dict) -> None:
        import lgpio
        import spidev

        self.gpio_lib = lgpio
        self.gpio = lgpio.gpiochip_open(0)
        joystick, buttons, lcd = config["joystick"], config["buttons"], config["lcd"]
        self.input_pins = {
            "left": joystick["pin_left"],
            "right": joystick["pin_right"],
            "up": joystick["pin_up"],
            "center": joystick["pin_center"],
            "b": buttons["pin_b"],
        }
        for pin in self.input_pins.values():
            lgpio.gpio_claim_input(self.gpio, pin, lgpio.SET_PULL_UP)
        self.output_pins = (lcd["pin_cs"], lcd["pin_dc"], lcd["pin_reset"], lcd["pin_backlight"])
        for pin in self.output_pins:
            lgpio.gpio_claim_output(self.gpio, pin, 0)
        self.cs, self.dc, self.reset, self.backlight = self.output_pins
        self.y_offset = lcd["y_offset"]
        self.rotation = lcd["rotation_degrees"]
        self.write_pin(self.cs, 1)

        self.spi = spidev.SpiDev()
        self.spi.open(lcd["spi_bus"], lcd["spi_device"])
        self.spi.max_speed_hz = lcd["baudrate"]
        self.spi.mode = 0
        self.spi.no_cs = True
        self.write_pin(self.reset, 0)
        time.sleep(0.05)
        self.write_pin(self.reset, 1)
        time.sleep(0.05)
        for command, data, delay in (
            (0x01, b"", 0.15), (0x11, b"", 0.50), (0x3A, b"\x55", 0.01),
            (0x36, b"\x08", 0), (0x21, b"", 0), (0x13, b"", 0),
            (0x29, b"", 0.10), (0x36, b"\xC0", 0),
        ):
            self.command(command, data)
            if delay:
                time.sleep(delay)
        self.write_pin(self.backlight, 1)

    def write_pin(self, pin: int, value: int) -> None:
        self.gpio_lib.gpio_write(self.gpio, pin, value)

    def command(self, code: int, data: bytes = b"") -> None:
        self.write_pin(self.cs, 0)
        self.write_pin(self.dc, 0)
        self.spi.writebytes2(bytes((code,)))
        if data:
            self.write_pin(self.dc, 1)
            self.spi.writebytes2(data)
        self.write_pin(self.cs, 1)

    def poll(self) -> dict[str, bool]:
        return {name: self.gpio_lib.gpio_read(self.gpio, pin) == 0 for name, pin in self.input_pins.items()}

    def present(self, image: Image.Image) -> None:
        import numpy

        if self.rotation == 180:
            image = image.transpose(Image.Transpose.ROTATE_180)
        pixels = numpy.asarray(image, dtype=numpy.uint16)
        rgb565 = ((pixels[:, :, 0] & 0xF8) << 8) | ((pixels[:, :, 1] & 0xFC) << 3) | (pixels[:, :, 2] >> 3)
        self.command(0x2A, struct.pack(">HH", 0, WIDTH - 1))
        self.command(0x2B, struct.pack(">HH", self.y_offset, self.y_offset + HEIGHT - 1))
        self.command(0x2C, rgb565.astype(">u2", copy=False).tobytes())

    def close(self) -> None:
        self.write_pin(self.backlight, 0)
        self.spi.close()
        for pin in (*self.input_pins.values(), *self.output_pins):
            self.gpio_lib.gpio_free(self.gpio, pin)
        self.gpio_lib.gpiochip_close(self.gpio)


def main() -> None:
    parser = argparse.ArgumentParser(description="산타의 선물 배달: 1주차 기본 구현")
    parser.add_argument("--headless", action="store_true", help="LCD 없이 화면 생성 확인")
    parser.add_argument("--frames", type=int, default=0, help=argparse.SUPPRESS)
    args = parser.parse_args()
    game, renderer = Game(), Renderer()
    if args.headless:
        assert renderer.render(game).size == (WIDTH, HEIGHT)
        return
    config = json.loads((ROOT / "config/hardware.adafruit-tft-bonnet.json").read_text(encoding="utf-8"))
    device = PiIO(config)
    previous = {name: False for name in device.input_pins}
    last_update = time.perf_counter()
    frames = 0
    try:
        while True:
            started = time.perf_counter()
            held = device.poll()
            pressed = {name: held[name] and not previous[name] if name in ("up", "center", "b") else held[name] for name in held}
            previous = held
            game.update(pressed, started - last_update)
            last_update = started
            device.present(renderer.render(game))
            frames += 1
            if args.frames and frames >= args.frames:
                break
            time.sleep(max(0.0, 1 / 30 - (time.perf_counter() - started)))
    except KeyboardInterrupt:
        pass
    finally:
        device.close()


if __name__ == "__main__":
    main()
