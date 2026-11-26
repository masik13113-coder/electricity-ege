"""Запуск приложения.

Запуск на компьютере (для разработки)::

    python main.py

На Android приложение собирается buildozer'ом; точка входа та же.
"""
from __future__ import annotations

import os

# Kivy не должен пытаться разбирать аргументы командной строки Android.
os.environ.setdefault("KIVY_NO_ARGS", "1")

from kivy.config import Config  # noqa: E402

# Отключаем сглаживание (MSAA): на телефоне это экономит память GPU
# и ускоряет отрисовку, а на качестве текста не сказывается.
Config.set("graphics", "multisamples", "0")
Config.set("graphics", "width", "412")
Config.set("graphics", "height", "860")
Config.set("graphics", "resizable", "1")

from app.ui.app import ElectricityApp  # noqa: E402


if __name__ == "__main__":
    ElectricityApp().run()
