[app]

# Название на экране телефона
title = Электричество ЕГЭ

package.name = electricityege
package.domain = ru.ege.electricity

source.dir = .
source.include_exts = py,json,md,txt
source.exclude_dirs = tests,tools,docs,.ui-shots,.ui-data,.test-artifacts,.git,.buildozer

version = 1.0.0

# Только необходимое: Kivy и стандартная библиотека Python.
# Никаких тяжёлых UI-библиотек и картинок.
requirements = python3,kivy==2.3.2

orientation = portrait
fullscreen = 0

android.api = 34
android.minapi = 24
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True
android.allow_backup = True

p4a.bootstrap = sdl2

[buildozer]
log_level = 2
warn_on_root = 1
