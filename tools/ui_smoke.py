"""Автоматический прогон интерфейса и скриншоты (только для разработки).

Запуск (Windows, из корня проекта)::

    python tools/ui_smoke.py

Скриншоты складываются в ``.ui-shots``. Прогресс пишется в ``.ui-data``,
боевую базу приложение не трогает. Скрипт проходит тему «Электрический заряд»,
отвечает на все вопросы (один — намеренно неверно) и проверяет переходы.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("KIVY_NO_ARGS", "1")
os.environ["EGE_USER_DIR"] = str(ROOT / ".ui-data")

from kivy.config import Config  # noqa: E402

Config.set("graphics", "multisamples", "0")
Config.set("graphics", "width", "412")
Config.set("graphics", "height", "860")

from kivy.clock import Clock  # noqa: E402
from kivy.core.window import Window  # noqa: E402

from app.ui.app import ElectricityApp  # noqa: E402

SHOTS = ROOT / ".ui-shots"
if SHOTS.exists():
    shutil.rmtree(SHOTS)
SHOTS.mkdir(parents=True)
shutil.rmtree(ROOT / ".ui-data", ignore_errors=True)
COUNTER = 0


def shot(name: str) -> None:
    global COUNTER
    COUNTER += 1
    path = SHOTS / f"{COUNTER:02d}-{name}.png"
    Window.screenshot(name=str(path))
    print("SHOT", path, flush=True)


def later(delay, callback):
    Clock.schedule_once(lambda _dt: callback(), delay)


def answer_current(wrong: bool) -> None:
    screen = app.quiz_screen
    session = screen._session
    if session is None:
        return
    question = session.current
    if question.kind == "choice":
        index = int(question.answer)
        if wrong:
            index = (index + 1) % len(question.options)
        screen._options[index].on_release()
    else:
        value = float(question.answer)
        if wrong:
            value = value * 2 + 1
        if screen._input is not None:
            screen._input.text = f"{value:g}".replace(".", ",")
        screen._submit_numeric()


def main() -> None:
    global app
    app = ElectricityApp()

    def start_home():
        shot("home")
        later(0.4, open_charge)

    def open_charge():
        app.home._rows[0].on_release()
        later(0.5, lesson_top)

    def lesson_top():
        shot("lesson-top")
        app.lesson_screen._scroll.scroll_y = 0.5
        later(0.5, lesson_mid)

    def lesson_mid():
        shot("lesson-mid")
        app.lesson_screen._scroll.scroll_y = 0.0
        later(0.4, lesson_bottom)

    def lesson_bottom():
        shot("lesson-bottom")
        later(0.2, start_quiz)

    def start_quiz():
        app.start_quiz("charge")
        later(0.5, lambda: ask(1))

    def ask(number: int):
        screen = app.quiz_screen
        question = screen._session.current
        shot(f"quiz-{number}-{'choice' if question.kind == 'choice' else 'numeric'}")
        answer_current(wrong=(number == 3))
        later(0.4, lambda: feedback(number))

    def feedback(number: int):
        shot(f"quiz-feedback-{number}")
        screen = app.quiz_screen
        is_last = screen._session.is_last
        screen._next()
        if is_last:
            later(0.9, result)
        else:
            later(0.35, lambda: ask(number + 1))

    def result():
        shot("result")
        app.back()
        later(0.6, home_progress)

    def home_progress():
        shot("home-progress")
        scroll = app.home._topics_scroll
        scroll.scroll_y = 0.0
        scroll.update_from_scroll()
        Clock.schedule_once(lambda *_: Window.canvas.ask_update(), 0.1)
        later(0.5, home_scrolled)

    def home_scrolled():
        # После программного scroll_y нужен принудительный кадр, иначе
        # Window.screenshot снимет предыдущий кадр.
        shot("home-scrolled")
        later(0.3, formulas)

    def formulas():
        shot("formulas")
        app.back()
        later(0.4, circuits)

    def circuits():
        app.open_lesson("circuits")
        later(0.5, circuits_scroll)

    def circuits_scroll():
        app.lesson_screen._scroll.scroll_y = 0.42
        later(0.4, circuits_shot)

    def circuits_shot():
        shot("circuits-diagram")
        app.lesson_screen._scroll.scroll_y = 0.55
        later(0.4, circuits_shot2)

    def circuits_shot2():
        shot("circuits-diagram2")
        later(0.4, nav_home)

    def nav_home():
        app.back()
        later(0.5, nav_lesson)

    def nav_lesson():
        app.open_lesson("charge")
        later(0.5, nav_quiz)

    def nav_quiz():
        app.start_quiz("charge")
        later(0.5, nav_back)

    def nav_back():
        app.back()  # quiz -> lesson, содержимое должно пересобраться
        later(0.6, nav_assert)

    def nav_assert():
        print(
            "NAV",
            app.sm.current,
            "lesson_widgets=", len(app.lesson_screen._grid.children),
            flush=True,
        )
        app.back()
        later(0.4, stop)

    def stop():
        app.stop()

    later(0.9, start_home)
    app.run()


if __name__ == "__main__":
    main()
