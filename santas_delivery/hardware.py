import json
from pathlib import Path
from typing import Any

from PIL import Image

from .input import InputFrame, InputTracker


class HardwareConfigurationError(RuntimeError):
    pass


def validate_hardware_config(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        lcd, joystick, buttons = data["lcd"], data["joystick"], data["buttons"]
        pins = [lcd[name] for name in ("spi_bus", "spi_device", "pin_cs", "pin_dc", "pin_reset", "pin_backlight")]
        pins += [joystick[name] for name in ("pin_up", "pin_down", "pin_left", "pin_right", "pin_center")]
        pins += [buttons[name] for name in ("pin_a", "pin_b")]
        valid = (
            lcd["controller"] == "ST7789V"
            and lcd["interface"] == "spi"
            and lcd["resolution"] == [240, 240]
            and joystick["type"] == "digital_gpio_4way"
            and None not in pins
        )
    except (OSError, ValueError, KeyError, TypeError):
        valid = False
    if not valid:
        raise HardwareConfigurationError("확인되지 않았거나 누락된 하드웨어 설정입니다")
    return data


class RaspberryPiInput:
    def __init__(self, config: dict[str, Any]) -> None:
        try:
            import lgpio
        except ImportError as exc:
            raise HardwareConfigurationError(
                "라즈베리파이 GPIO 라이브러리 lgpio가 없습니다. OS의 python3-lgpio 패키지를 설치하세요."
            ) from exc
        self._lgpio = lgpio
        self._gpio = lgpio.gpiochip_open(0)
        joystick = config["joystick"]
        buttons = config["buttons"]
        self._pins: dict[str, int] = {
            "left": int(joystick["pin_left"]),
            "right": int(joystick["pin_right"]),
            "up": int(joystick["pin_up"]),
            "down": int(joystick["pin_down"]),
            "start": int(joystick["pin_center"]),
            "action_a": int(buttons["pin_a"]),
            "action_b": int(buttons["pin_b"]),
        }
        for pin in self._pins.values():
            lgpio.gpio_claim_input(self._gpio, pin, lgpio.SET_PULL_UP)
        self._tracker = InputTracker()

    def poll(self) -> InputFrame:
        def pressed(name: str) -> bool:
            return self._lgpio.gpio_read(self._gpio, self._pins[name]) == 0

        return self._tracker.frame(
            left=pressed("left"),
            right=pressed("right"),
            up=pressed("up"),
            down=pressed("down"),
            action_a=pressed("action_a"),
            action_b=pressed("action_b"),
            start=pressed("start"),
        )

    def close(self) -> None:
        for pin in self._pins.values():
            try:
                self._lgpio.gpio_free(self._gpio, pin)
            except Exception:
                pass
        self._lgpio.gpiochip_close(self._gpio)


class RaspberryPiDisplay:
    def __init__(self, config: dict[str, Any]) -> None:
        lcd = config["lcd"]
        try:
            from .st7789_native import ST7789Native

            self._display = ST7789Native(
                spi_bus=int(lcd["spi_bus"]),
                spi_device=int(lcd["spi_device"]),
                cs_pin=int(lcd["pin_cs"]),
                dc_pin=int(lcd["pin_dc"]),
                reset_pin=int(lcd["pin_reset"]),
                backlight_pin=int(lcd["pin_backlight"]),
                y_offset=int(lcd.get("y_offset", 80)),
                baudrate=int(lcd.get("baudrate", 24_000_000)),
            )
        except (ImportError, RuntimeError) as exc:
            raise HardwareConfigurationError(
                "ST7789V에는 OS 패키지 python3-spidev, python3-lgpio, python3-numpy가 필요합니다."
            ) from exc

    def present(self, frame: Image.Image) -> None:
        if frame.size != (240, 240):
            raise ValueError("LCD 화면 크기는 정확히 240×240이어야 합니다")
        self._display.image(frame)

    def close(self) -> None:
        self._display.close()
