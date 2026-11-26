"""Палитра и размеры интерфейса.

Никаких растровых картинок и шрифтов в комплекте: всё рисуется векторно
(canvas Kivy) или стандартным шрифтом Roboto. Это экономит и оперативную
память, и размер APK.
"""
from __future__ import annotations

from kivy.metrics import dp, sp
from kivy.utils import get_color_from_hex


def rgba(hex_color: str, alpha: float = 1.0) -> list[float]:
    red, green, blue, _ = get_color_from_hex(hex_color)
    return [red, green, blue, alpha]


def darken(color: list[float], factor: float = 0.86) -> list[float]:
    return [color[0] * factor, color[1] * factor, color[2] * factor, color[3]]


# --------------------------------------------------------------------- палитра
BG = rgba("#F3F5FA")
CARD = rgba("#FFFFFF")
CARD_PRESSED = rgba("#EDF2FF")
TEXT = rgba("#101828")
TEXT_MUTED = rgba("#667085")
TEXT_ON_PRIMARY = rgba("#FFFFFF")
BORDER = rgba("#E4E7EC")

PRIMARY = rgba("#2563EB")
PRIMARY_PRESSED = rgba("#1D4ED8")
PRIMARY_SOFT = rgba("#DBEAFE")

SUCCESS = rgba("#067647")
SUCCESS_BG = rgba("#DCFAE6")
DANGER = rgba("#B42318")
DANGER_BG = rgba("#FEE4E2")
WARNING = rgba("#B54708")

DIAGRAM = rgba("#344054")
WHITE = rgba("#FFFFFF")
TRANSPARENT = [0.0, 0.0, 0.0, 0.0]

# ----------------------------------------------------------------------- шрифты
H1 = sp(25)
H2 = sp(19)
H3 = sp(16)
BODY = sp(15)
FORMULA = sp(17)
SMALL = sp(13)
TINY = sp(11)
BUTTON = sp(16)

# ---------------------------------------------------------------------- отступы
PAGE_X = dp(16)
CARD_PADDING = [dp(14), dp(12), dp(14), dp(12)]
CARD_RADIUS = dp(18)
CARD_SPACING = dp(12)
ROW_HEIGHT = dp(84)
