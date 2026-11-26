"""Сборка Kivy-приложения и навигация.

Память: экраны создаются один раз (это лёгкие контейнеры), а тяжёлое
содержимое каждого экрана освобождается через 0,24 с после ухода с него —
когда анимация перехода закончилась. Кэш уроков при этом тоже очищается.
"""
from __future__ import annotations

import gc
import os
from pathlib import Path

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen, ScreenManager, SlideTransition
from kivy.utils import platform

from ..content import ContentError, ContentRepository
from ..storage import ProgressStore
from . import theme as T
from .screens import (
    FormulasScreen,
    HomeScreen,
    LessonScreen,
    QuizScreen,
    ResultScreen,
)
from .widgets import RoundedButton, WrapLabel


class ElectricityApp(App):
    """Точка входа мобильного приложения."""

    def build(self):
        self.title = "Электричество · ЕГЭ"
        Window.clearcolor = T.BG
        if platform == "android":
            # Клавиатура не закрывает поле ввода.
            Window.softinput_mode = "below_target"

        self.repo = None
        self.store = None
        try:
            self.repo = ContentRepository()
        except ContentError as exc:
            return self._fatal_screen(str(exc))

        self._cleanup_tokens: dict[Screen, int] = {}
        base = Path(os.environ.get("EGE_USER_DIR") or self.user_data_dir).expanduser()
        base.mkdir(parents=True, exist_ok=True)
        self._db_path = str(base / "progress.sqlite3")
        self.store = self._create_store()

        self.home = HomeScreen(self)
        self.lesson_screen = LessonScreen(self)
        self.quiz_screen = QuizScreen(self)
        self.result_screen = ResultScreen(self)
        self.formulas_screen = FormulasScreen(self)

        self.sm = ScreenManager(
            transition=SlideTransition(direction="left", duration=0.18)
        )
        for screen in (
            self.home,
            self.lesson_screen,
            self.quiz_screen,
            self.result_screen,
            self.formulas_screen,
        ):
            self.sm.add_widget(screen)
        self.sm.current = "home"
        # ScreenManager не всегда присылает on_pre_enter первому экрану.
        self.home.on_pre_enter()
        return self.sm

    # ------------------------------------------------------------------ storage
    def _create_store(self) -> ProgressStore:
        try:
            return ProgressStore(self._db_path)
        except Exception:
            # На крайний случай работаем без сохранения прогресса, но
            # приложение не падает.
            self._db_path = ":memory:"
            return ProgressStore(":memory:")

    def get_store(self) -> ProgressStore | None:
        if self.repo is None:
            return None
        if self.store is None or self.store.closed:
            self.store = self._create_store()
        return self.store

    # --------------------------------------------------------------- navigation
    def _go(self, name: str, direction: str = "left") -> None:
        if self.sm.current == name:
            return
        previous = self.sm.current_screen
        self.sm.transition.direction = direction
        self.sm.current = name
        if previous is not None:
            token = self._cleanup_tokens.get(previous, 0) + 1
            self._cleanup_tokens[previous] = token
            Clock.schedule_once(
                lambda _dt, screen=previous, tok=token: self._cleanup(screen, tok),
                0.24,
            )

    def _cleanup(self, screen: Screen, token: int) -> None:
        if self.sm.current_screen is screen:
            return
        if self._cleanup_tokens.get(screen) != token:
            return
        release = getattr(screen, "release", None)
        if callable(release):
            release()

    def back(self) -> bool:
        if self.repo is None:
            return False
        current = self.sm.current
        if current == "home":
            return False
        if current == "quiz":
            meta = self.quiz_screen.meta
            if meta is not None:
                try:
                    self.lesson_screen.open(meta)
                except ContentError:
                    self._go("home", "right")
                    return True
                self._go("lesson", "right")
            else:
                self._go("home", "right")
            return True
        self._go("home", "right")
        return True

    def open_lesson(self, lesson_id: str) -> None:
        if self.repo is None:
            return
        try:
            meta = self.repo.topic(lesson_id)
            self.lesson_screen.open(meta)
        except ContentError as exc:
            self._show_error("Не удалось открыть тему", str(exc))
            return
        self._go("lesson")

    def start_quiz(self, lesson_id: str) -> None:
        if self.repo is None:
            return
        try:
            meta = self.repo.topic(lesson_id)
            self.quiz_screen.start(meta)
        except (ContentError, ValueError) as exc:
            self._show_error("Не удалось начать тест", str(exc))
            return
        self._go("quiz")

    def finish_quiz(self, summary) -> None:
        record = False
        try:
            store = self.get_store()
            if store is not None:
                _, record = store.save_attempt(
                    summary.lesson_id, summary.correct, summary.total
                )
        except Exception:
            record = False
        self.result_screen.show(summary, record)
        self._go("result")

    def show_formulas(self) -> None:
        if self.repo is None:
            return
        self.formulas_screen.load()
        self._go("formulas")

    def reset_progress(self) -> None:
        try:
            store = self.get_store()
            if store is not None:
                store.reset()
        except Exception:
            pass
        self.home.refresh()

    # -------------------------------------------------------------------- errors
    def _show_error(self, title: str, message: str) -> None:
        content = BoxLayout(
            orientation="vertical", padding=[dp(14)] * 4, spacing=dp(10)
        )
        content.add_widget(WrapLabel(text=message, font_size=T.BODY))
        button = RoundedButton(text="Понятно", height=dp(44))
        content.add_widget(button)
        popup = Popup(
            title=title,
            content=content,
            size_hint=(0.9, None),
            height=dp(230),
        )
        button.bind(on_release=lambda *_: popup.dismiss())
        popup.open()

    def _fatal_screen(self, message: str) -> Screen:
        screen = Screen(name="error")
        box = BoxLayout(
            orientation="vertical", padding=[dp(20)] * 4, spacing=dp(12)
        )
        box.add_widget(
            Label(
                text="Не удалось загрузить курс",
                font_size=T.H2,
                bold=True,
                color=T.DANGER,
                size_hint_y=None,
                height=dp(32),
                halign="left",
                valign="middle",
            )
        )
        box.add_widget(WrapLabel(text=message, font_size=T.SMALL))
        screen.add_widget(box)
        return screen

    # --------------------------------------------------------------- lifecycle
    def on_start(self):
        Window.bind(on_keyboard=self._on_keyboard)
        # Все объекты, созданные к этому моменту, живут до конца приложения.
        # GC больше не сканирует их на каждой сборке — меньше рывков и RAM.
        if hasattr(gc, "freeze"):
            gc.freeze()

    def on_pause(self):
        if self.store is not None and not self.store.closed:
            try:
                self.store.close()
            except Exception:
                pass
        return True

    def on_resume(self):
        if self.repo is None:
            return
        self.get_store()
        if getattr(self.home, "_built", False):
            self.home.refresh()

    def on_stop(self):
        if self.store is not None and not self.store.closed:
            try:
                self.store.close()
            except Exception:
                pass
        if self.repo is not None:
            self.repo.release()

    def _on_keyboard(self, _window, key, *_args):
        if key == 27:  # Escape на десктопе, кнопка «назад» на Android
            return self.back()
        return False
