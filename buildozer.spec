[app]

# Название на экране телефона
title = Электричество ЕГЭ

package.name = electricityege
package.domain = ru.ege.electricity

source.dir = .
source.include_exts = py,json,md,txt
source.exclude_dirs = tests,tools,docs,.ui-shots,.ui-data,.test-artifacts,.git,.buildozer

version = 1.0.0

# Проверенная связка для Android:
# p4a v2024.01.21 -> Python 3.11.5, pyjnius 1.6.1, Kivy 2.3.0.
# Более новые p4a используют Python 3.14, под который старые pyjnius/Kivy
# ещё не собраны.
p4a.branch = v2024.01.21

requirements = python3,kivy==2.3.0

orientation = portrait
fullscreen = 0

android.api = 33
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True
android.allow_backup = True

p4a.bootstrap = sdl2

[buildozer]
log_level = 2
warn_on_root = 1
