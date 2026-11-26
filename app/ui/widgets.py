"""Виджеты интерфейса: карточки, кнопки, прогресс, схемы.

Все фоны рисуются на canvas (RoundedRectangle/Line/Ellipse), а не картинками:
Kivy не создаёт текстуры для изображений, поэтому даже на слабом телефоне
интерфейс не съедает лишнюю память под растр.
"""
from __future__ import annotations

from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Line, Rectangle, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.properties import (
    BooleanProperty,
    ListProperty,
    NumericProperty,
    ObjectProperty,
    StringProperty,
)
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.widget import Widget

from ..config import PASS_PERCENT
from . import theme as T


def bind_text_size(label: Label) -> None:
    """Включает перенос строк по ширине виджета и авто-высоту."""

    def update_text_size(*_args):
        label.text_size = (max(1.0, label.width), None)

    def update_height(*_args):
        label.height = label.texture_size[1]

    label.bind(width=update_text_size, texture_size=update_height)
    update_text_size()


class WrapLabel(Label):
    """Метка с переносом строк и высотой по содержимому."""

    def __init__(self, **kwargs):
        kwargs.setdefault("markup", True)
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("halign", "left")
        kwargs.setdefault("valign", "top")
        kwargs.setdefault("color", T.TEXT)
        super().__init__(**kwargs)
        bind_text_size(self)


class RoundedCard(BoxLayout):
    """Белая карточка со скруглёнными углами."""

    bg_color = ListProperty(T.CARD)
    radius = NumericProperty(T.CARD_RADIUS)

    def __init__(self, **kwargs):
        kwargs.setdefault("orientation", "vertical")
        super().__init__(**kwargs)
        if "padding" not in kwargs:
            self.padding = list(T.CARD_PADDING)
        with self.canvas.before:
            self._bg_color = Color(rgba=self.bg_color)
            self._bg_shape = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[self.radius]
            )
        self.bind(
            pos=self._sync_shape,
            size=self._sync_shape,
            bg_color=self._sync_color,
        )

    def _sync_shape(self, *_args):
        self._bg_shape.pos = self.pos
        self._bg_shape.size = self.size
        self._bg_shape.radius = [self.radius]

    def _sync_color(self, *_args):
        self._bg_color.rgba = self.bg_color


class RoundedButton(Button):
    """Кнопка с векторным фоном; корректно выглядит на любом DPI."""

    bg_color = ListProperty(T.PRIMARY)
    text_color = ListProperty(T.TEXT_ON_PRIMARY)
    radius = NumericProperty(dp(14))

    def __init__(self, **kwargs):
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_down", "")
        kwargs.setdefault("background_color", (0, 0, 0, 0))
        kwargs.setdefault("markup", True)
        kwargs.setdefault("font_size", T.BUTTON)
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(48))
        kwargs.setdefault("disabled_color", T.TEXT_MUTED)
        super().__init__(**kwargs)
        with self.canvas.before:
            self._bg_color = Color(rgba=self.bg_color)
            self._bg_shape = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[self.radius]
            )
        self.bind(
            pos=self._sync_shape,
            size=self._sync_shape,
            state=self._sync_colors,
            disabled=self._sync_colors,
            bg_color=self._sync_colors,
            text_color=self._sync_colors,
        )
        self._sync_colors()

    def _sync_shape(self, *_args):
        self._bg_shape.pos = self.pos
        self._bg_shape.size = self.size
        self._bg_shape.radius = [self.radius]

    def _sync_colors(self, *_args):
        if self.disabled:
            color = T.BORDER
            text = T.TEXT_MUTED
        else:
            color = T.darken(self.bg_color) if self.state == "down" else self.bg_color
            text = self.text_color
        self._bg_color.rgba = color
        self.color = text


class TextButton(RoundedButton):
    """Кнопка-ссылка без заливки."""

    def __init__(self, **kwargs):
        kwargs.setdefault("bg_color", T.TRANSPARENT)
        kwargs.setdefault("text_color", T.PRIMARY)
        kwargs.setdefault("height", dp(40))
        kwargs.setdefault("font_size", T.SMALL)
        super().__init__(**kwargs)


class LinearProgress(Widget):
    """Тонкая полоса прогресса."""

    value = NumericProperty(0.0)
    track_color = ListProperty(T.rgba("#E4E7EC"))
    fill_color = ListProperty(T.PRIMARY)

    def __init__(self, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(8))
        super().__init__(**kwargs)
        with self.canvas:
            self._track_color = Color(rgba=self.track_color)
            self._track = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(4)])
            self._fill_color = Color(rgba=self.fill_color)
            self._fill = RoundedRectangle(pos=self.pos, size=(0, 0), radius=[dp(4)])
        self.bind(
            pos=self._sync,
            size=self._sync,
            value=self._sync,
            track_color=self._sync_colors,
            fill_color=self._sync_colors,
        )
        self._sync()

    def _sync_colors(self, *_args):
        self._track_color.rgba = self.track_color
        self._fill_color.rgba = self.fill_color

    def _sync(self, *_args):
        ratio = min(1.0, max(0.0, float(self.value)))
        self._track.pos = self.pos
        self._track.size = self.size
        self._fill.pos = self.pos
        self._fill.size = (self.width * ratio, self.height)


class Badge(Label):
    """Кружок с номером темы; зелёный, если тема пройдена."""

    done = BooleanProperty(False)

    def __init__(self, **kwargs):
        kwargs.setdefault("size_hint", (None, None))
        kwargs.setdefault("size", (dp(40), dp(40)))
        kwargs.setdefault("bold", True)
        kwargs.setdefault("font_size", T.H3)
        kwargs.setdefault("halign", "center")
        kwargs.setdefault("valign", "middle")
        super().__init__(**kwargs)
        self.text_size = self.size
        with self.canvas.before:
            self._fill_color = Color(rgba=T.PRIMARY_SOFT)
            self._circle = Ellipse(pos=self.pos, size=self.size)
        self.bind(pos=self._sync, size=self._sync, done=self._sync)
        self._sync()

    def _sync(self, *_args):
        self._circle.pos = self.pos
        self._circle.size = self.size
        self.text_size = self.size
        if self.done:
            self._fill_color.rgba = T.SUCCESS_BG
            self.color = T.SUCCESS
        else:
            self._fill_color.rgba = T.PRIMARY_SOFT
            self.color = T.PRIMARY


class TopicRow(ButtonBehavior, RoundedCard):
    """Строка темы на главном экране."""

    meta = ObjectProperty(None, allownone=True)
    best = NumericProperty(0)
    number = NumericProperty(0)
    open_callback = ObjectProperty(None, allownone=True)

    def __init__(self, **kwargs):
        kwargs.setdefault("orientation", "horizontal")
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", T.ROW_HEIGHT)
        kwargs.setdefault("padding", [dp(12), dp(10), dp(12), dp(10)])
        kwargs.setdefault("spacing", dp(12))
        super().__init__(**kwargs)

        self._badge = Badge()
        self.add_widget(self._badge)

        middle = BoxLayout(orientation="vertical", spacing=dp(2), size_hint_x=1)
        self._title = Label(
            text="",
            markup=False,
            font_size=T.H3,
            bold=True,
            color=T.TEXT,
            halign="left",
            valign="middle",
            size_hint_y=None,
            height=dp(24),
            shorten=True,
            shorten_from="right",
        )
        self._subtitle = Label(
            text="",
            markup=False,
            font_size=T.SMALL,
            color=T.TEXT_MUTED,
            halign="left",
            valign="middle",
            size_hint_y=None,
            height=dp(20),
            shorten=True,
            shorten_from="right",
        )
        bind_text_size(self._title)
        bind_text_size(self._subtitle)
        self._title.height = dp(24)
        self._subtitle.height = dp(20)
        middle.add_widget(self._title)
        middle.add_widget(self._subtitle)
        self.add_widget(middle)

        self._right = Label(
            text="›",
            font_size=sp(22),
            color=T.TEXT_MUTED,
            size_hint=(None, 1),
            width=dp(48),
            halign="center",
            valign="middle",
        )
        self.add_widget(self._right)

        self.bind(meta=self._refresh, best=self._refresh, number=self._refresh)
        self.bind(state=self._refresh_bg, disabled=self._refresh_bg)
        self._refresh()

    def _refresh_bg(self, *_args):
        if self.disabled:
            self.bg_color = T.BG
        else:
            self.bg_color = T.CARD_PRESSED if self.state == "down" else T.CARD

    def _refresh(self, *_args):
        meta = self.meta
        self._badge.text = str(self.number)
        self._badge.done = self.best >= PASS_PERCENT
        if meta is None:
            self._title.text = ""
            self._subtitle.text = ""
            self._right.text = "›"
            return
        self._title.text = meta.title
        self._subtitle.text = meta.subtitle
        if self.best > 0:
            self._right.text = f"{self.best}%"
            self._right.color = T.SUCCESS if self.best >= PASS_PERCENT else T.WARNING
            self._right.font_size = T.SMALL
        else:
            self._right.text = "›"
            self._right.color = T.TEXT_MUTED
            self._right.font_size = sp(22)

    def on_release(self):
        if self.open_callback is not None and self.meta is not None:
            self.open_callback(self.meta.id)


class OptionCard(ButtonBehavior, RoundedCard):
    """Вариант ответа: карточка, которая умеет подсветиться после проверки."""

    index = NumericProperty(0)
    option_text = StringProperty("")
    pick_callback = ObjectProperty(None, allownone=True)
    locked = BooleanProperty(False)

    def __init__(self, **kwargs):
        kwargs.setdefault("orientation", "horizontal")
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("bg_color", T.CARD)
        kwargs.setdefault("padding", [dp(12), dp(10), dp(12), dp(10)])
        super().__init__(**kwargs)
        self._label = WrapLabel(
            text="", font_size=T.BODY, color=T.TEXT, markup=True
        )
        self.add_widget(self._label)
        self._label.bind(height=self._sync_height)
        self.bind(option_text=self._sync_text, state=self._refresh_bg)
        self._sync_text()
        self._sync_height()

    def _sync_text(self, *_args):
        self._label.text = self.option_text

    def _sync_height(self, *_args):
        self.height = self._label.height + dp(22)

    def _refresh_bg(self, *_args):
        if self.locked:
            return
        self.bg_color = T.CARD_PRESSED if self.state == "down" else T.CARD

    def mark(self, kind: str) -> None:
        """kind: correct | wrong | neutral."""
        if kind == "correct":
            self.bg_color = T.SUCCESS_BG
        elif kind == "wrong":
            self.bg_color = T.DANGER_BG
        else:
            self.bg_color = T.CARD

    def on_release(self):
        if self.locked:
            return
        if self.pick_callback is not None:
            self.pick_callback(self.index)


class CircuitDiagram(Widget):
    """Векторная схема цепи: последовательно, параллельно, с ЭДС.

    Текстовые подписи — обычные Label-дети, их координаты пересчитываются
    при изменении размера. Никаких картинок и текстур, кроме текста.
    """

    mode = StringProperty("series")

    def __init__(self, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(158))
        super().__init__(**kwargs)
        self._labels = {}
        for key in ("r1", "r2", "src", "rload"):
            label = Label(
                text="",
                markup=True,
                font_size=T.SMALL,
                color=T.TEXT_MUTED,
                size_hint=(None, None),
                size=(dp(64), dp(18)),
                halign="center",
                valign="middle",
                opacity=0,
            )
            self.add_widget(label)
            self._labels[key] = label
        self.bind(pos=self._redraw, size=self._redraw, mode=self._redraw)
        Clock.schedule_once(self._redraw, 0)

    # ------------------------------------------------------------------ public
    def _reset_labels(self):
        for label in self._labels.values():
            label.opacity = 0

    def _place(self, key, x, y, text):
        label = self._labels[key]
        label.text = text
        label.center = (x, y)
        label.opacity = 1

    # ----------------------------------------------------------------- drawing
    def _redraw(self, *_args):
        # Рисуем в canvas.before: canvas.clear() удалил бы и canvas-ы
        # дочерних Label-подписей.
        self.canvas.before.clear()
        self._reset_labels()
        width, height = self.size
        if width < dp(80) or height < dp(80):
            return
        x, y = self.pos
        with self.canvas.before:
            Color(*T.DIAGRAM)
            if self.mode == "parallel":
                self._draw_parallel(x, y, width, height)
            elif self.mode == "emf":
                self._draw_emf(x, y, width, height)
            else:
                self._draw_series(x, y, width, height)

    @staticmethod
    def _wire(points):
        Line(points=points, width=dp(2), joint="round", cap="round")

    def _resistor(self, cx, cy, rw, rh):
        Color(*T.WHITE)
        Rectangle(pos=(cx - rw / 2, cy - rh / 2), size=(rw, rh))
        Color(*T.DIAGRAM)
        Line(
            rounded_rectangle=(cx - rw / 2, cy - rh / 2, rw, rh, dp(3)),
            width=dp(2),
        )

    def _battery(self, cx, cy, plate):
        Color(*T.DIAGRAM)
        Line(points=[cx - plate, cy + dp(3), cx + plate, cy + dp(3)], width=dp(2))
        Line(
            points=[cx - plate * 0.55, cy - dp(3), cx + plate * 0.55, cy - dp(3)],
            width=dp(2),
        )

    def _draw_series(self, x, y, width, height):
        left = x + width * 0.12
        right = x + width * 0.88
        top = y + height * 0.68
        bottom = y + height * 0.26
        middle = (top + bottom) / 2
        rw = (right - left) * 0.17
        rh = height * 0.13
        cx1 = left + (right - left) * 0.33
        cx2 = left + (right - left) * 0.67
        gap = height * 0.18

        self._wire([left, top, cx1 - rw / 2, top])
        self._wire([cx1 + rw / 2, top, cx2 - rw / 2, top])
        self._wire([cx2 + rw / 2, top, right, top])
        self._wire([right, top, right, bottom])
        self._wire([right, bottom, left, bottom])
        self._wire([left, top, left, middle + gap / 2])
        self._wire([left, middle - gap / 2, left, bottom])
        self._battery(left, middle, (right - left) * 0.035)
        self._resistor(cx1, top, rw, rh)
        self._resistor(cx2, top, rw, rh)

        self._place("r1", cx1, top + rh, "R[sub]1[/sub]")
        self._place("r2", cx2, top + rh, "R[sub]2[/sub]")
        self._place("src", left, bottom - dp(12), "ε, r")

    def _draw_parallel(self, x, y, width, height):
        left = x + width * 0.12
        right = x + width * 0.88
        top = y + height * 0.70
        bottom = y + height * 0.30
        middle = (top + bottom) / 2
        branch1 = left + (right - left) * 0.42
        branch2 = left + (right - left) * 0.68
        rw = (right - left) * 0.09
        rh = height * 0.16
        gap = height * 0.18

        self._wire([left, top, right, top])
        self._wire([left, bottom, right, bottom])
        self._wire([branch1, top, branch1, middle + rh / 2])
        self._wire([branch1, middle - rh / 2, branch1, bottom])
        self._wire([branch2, top, branch2, middle + rh / 2])
        self._wire([branch2, middle - rh / 2, branch2, bottom])
        self._wire([left, top, left, middle + gap / 2])
        self._wire([left, middle - gap / 2, left, bottom])
        self._battery(left, middle, (right - left) * 0.035)
        self._resistor(branch1, middle, rw, rh)
        self._resistor(branch2, middle, rw, rh)

        self._place("r1", branch1, top + dp(14), "R[sub]1[/sub]")
        self._place("r2", branch2, top + dp(14), "R[sub]2[/sub]")
        self._place("src", left, bottom - dp(12), "ε, r")

    def _draw_emf(self, x, y, width, height):
        left = x + width * 0.12
        right = x + width * 0.88
        top = y + height * 0.68
        bottom = y + height * 0.26
        middle = (top + bottom) / 2
        rw = (right - left) * 0.20
        rh = height * 0.14
        cx = left + (right - left) * 0.62
        gap = height * 0.18

        self._wire([left, top, cx - rw / 2, top])
        self._wire([cx + rw / 2, top, right, top])
        self._wire([right, top, right, bottom])
        self._wire([right, bottom, left, bottom])
        self._wire([left, top, left, middle + gap / 2])
        self._wire([left, middle - gap / 2, left, bottom])
        self._battery(left, middle, (right - left) * 0.035)
        self._resistor(cx, top, rw, rh)

        self._place("src", left, bottom - dp(12), "ε, r")
        self._place("rload", cx, top + rh, "R")
