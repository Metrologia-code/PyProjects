import os
import shutil
import sys

# (основной файл, дамми-файл, резерв реального файла)
TARGETS = [
    ("Tonghui_libs/tonghui_TH1992B.py", "Tonghui_libs/__tonghui_TH1992B.py", "Tonghui_libs/tonghui_TH1992B_real.py"),
    ("Tonghui_libs/tonghui_TH2690A.py", "Tonghui_libs/__tonghui_TH2690A.py", "Tonghui_libs/tonghui_TH2690A_real.py"),
    ("Motion_control/__init__.py",      "Motion_control/__init__dummy.py",   "Motion_control/__init__real.py"),
]

if not (os.path.isdir("Tonghui_libs") and os.path.isdir("Motion_control")):
    sys.exit("Ошибка: запускать из корня проекта.")

states = {os.path.exists(backup) for _, _, backup in TARGETS}
if len(states) != 1:
    sys.exit("Ошибка: состояние файлов несогласовано (часть дамми, часть реальные).")
was_dummy = states.pop()

for main, dummy, backup in TARGETS:
    if was_dummy:                 # дамми -> реальные
        os.replace(main, dummy)
        os.replace(backup, main)
    else:                         # реальные -> дамми
        os.replace(main, backup)
        os.replace(dummy, main)

for root, dirs, _ in os.walk("."):
    if "__pycache__" in dirs:
        shutil.rmtree(os.path.join(root, "__pycache__"))
        dirs.remove("__pycache__")

print("Установлено состояние:", "real" if was_dummy else "dummy")
