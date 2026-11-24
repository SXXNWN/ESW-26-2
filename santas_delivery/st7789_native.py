
import struct
import time
from PIL import Image


class ST7789Native:
    WIDTH = 240
    HEIGHT = 240

    def __init__(
        self,
        *,
        spi_bus: int,
        spi_device: int,
        cs_pin: int,
        dc_pin: int,
        reset_pin: int,
        backlight_pin: int,
        y_offset: int = 80,
        baudrate: int = 24_000_000,
    ) -> None:
        try:
            import lgpio
            import spidev
        except ImportError as exc:
            raise RuntimeError("라즈베리파이 패키지 lgpio와 spidev가 필요합니다") from exc
        self._lgpio = lgpio
        self._gpio = lgpio.gpiochip_open(0)
        self._cs_pin = cs_pin
        self._dc_pin = dc_pin
        self._reset_pin = reset_pin
        self._backlight_pin = backlight_pin
        for pin in (cs_pin, dc_pin, reset_pin, backlight_pin):
            lgpio.gpio_claim_output(self._gpio, pin, 0)
        lgpio.gpio_write(self._gpio, cs_pin, 1)

        self._spi = spidev.SpiDev()
        self._spi.open(spi_bus, spi_device)
        self._spi.max_speed_hz = baudrate
        self._spi.mode = 0
        self._spi.bits_per_word = 8
        self._spi.no_cs = True
        self.y_offset = y_offset
        self._reset()
        self._initialize()
        lgpio.gpio_write(self._gpio, self._backlight_pin, 1)

    def _gpio_write(self, pin: int, value: int) -> None:
        self._lgpio.gpio_write(self._gpio, pin, value)

    def _reset(self) -> None:
        self._gpio_write(self._reset_pin, 0)
        time.sleep(0.05)
        self._gpio_write(self._reset_pin, 1)
        time.sleep(0.05)

    def _write(self, command: int, data: bytes | None = None) -> None:
        self._gpio_write(self._cs_pin, 0)
        self._gpio_write(self._dc_pin, 0)
        self._spi.writebytes2(bytes((command,)))
        if data:
            self._gpio_write(self._dc_pin, 1)
            self._spi.writebytes2(data)
        self._gpio_write(self._cs_pin, 1)

    def _initialize(self) -> None:
        self._write(0x01)
        time.sleep(0.15)
        self._write(0x11)
        time.sleep(0.50)
        self._write(0x3A, b"\x55")
        time.sleep(0.01)
        self._write(0x36, b"\x08")
        self._set_window()
        self._write(0x21)
        self._write(0x13)
        self._write(0x29)
        time.sleep(0.10)
        self._write(0x36, b"\xC0")

    def _set_window(self) -> None:
        self._write(0x2A, struct.pack(">HH", 0, self.WIDTH - 1))
        self._write(0x2B, struct.pack(">HH", self.y_offset, self.y_offset + self.HEIGHT - 1))

    @staticmethod
    def _rgb565_bytes(image: Image.Image) -> bytes:
        import numpy

        rgb = image if image.mode == "RGB" else image.convert("RGB")
        data = numpy.asarray(rgb, dtype=numpy.uint16)
        color = ((data[:, :, 0] & 0xF8) << 8) | ((data[:, :, 1] & 0xFC) << 3) | (data[:, :, 2] >> 3)
        return color.astype(">u2", copy=False).tobytes()

    def image(self, image: Image.Image) -> None:
        if image.size != (self.WIDTH, self.HEIGHT):
            raise ValueError("ST7789V 이미지는 정확히 240×240이어야 합니다")
        image = image.transpose(Image.Transpose.ROTATE_180)
        self._set_window()
        self._write(0x2C, self._rgb565_bytes(image))

    def close(self, *, blank: bool = True) -> None:
        if blank:
            self.image(Image.new("RGB", (self.WIDTH, self.HEIGHT), "black"))
        self._gpio_write(self._backlight_pin, 0)
        self._spi.close()
        for pin in (self._backlight_pin, self._reset_pin, self._dc_pin, self._cs_pin):
            try:
                self._lgpio.gpio_free(self._gpio, pin)
            except Exception:
                pass
        self._lgpio.gpiochip_close(self._gpio)
