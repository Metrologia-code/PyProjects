# Метрологический проект

Лабораторное ПО для метрологических измерений. Две основные программы:

- **`devices_logger.py`** — логирование данных с измерительных приборов (Tonghui) в реальном времени с сохранением в файл и графиком.
- **`axes_scanner.py`** — автоматизация серии экспериментов сканирования щелью: файл заданий → движение ножей (оси APT/APL/APR/APB) → измерение приборов в каждой позиции.

## 📁 Структура проекта

```text
devices_logger.py                   # Гл. программа 1: логгер приборов
axes_scanner.py                     # Гл. программа 2: сканер щелью
measurement.py                      # Общий движок MeasurementSession: цикл опроса, запись, график
instruction.txt                     # Документация CLI обеих программ и форматов конфигов приборов
requirements.txt                    # Список зависимостей
AGENTS.md                           # Руководство для агентов
├── Complex_libs/                   # Управление измерительным комплексом
│   ├── Devices.ini                 # Пул приборов: type/model/interface/address/channels/values/units
│   ├── DeviceSpecParser.py         # Разбор Devices.ini и аргумента -d нового синтаксиса
│   └── Devices.py                  # Инициализация драйверов, пробный опрос, список колонок
├── User_libs/                      # Вспомогательные библиотеки
│   ├── pyTools.py                  # Парсеры, пути файлов, трансформации (Pt100→температура)
│   ├── pyPlotter.py                # Plotter: графики в реальном времени
│   └── pyPlot.py                   # Предшественник Plotter'а (переэкспортируется)
├── Tonghui_libs/                   # Драйверы измерителей Tonghui
│   ├── tonghui_TH1992B.py          # Драйвер TH1992B (2 канала)
│   ├── tonghui_TH2690A.py          # Драйвер TH2690A (1 канал)
│   ├── __tonghui_TH1992B.py        # Дамми-драйвер TH1992B (для отладки без железа)
│   ├── __tonghui_TH2690A.py        # Дамми-драйвер TH2690A
│   └── config/                     # Пресеты измерений (INI)
├── Motion_control/                 # Управление контроллером движения ACS
│   ├── Controller.py               # Контроллер ACS (TCP 192.168.88.10:701)
│   ├── MotionControlTools.py       # InitSpeed, MoveBlades, pos_to_x и др.
│   └── __init__dummy.py            # Дамми-контроллер (для отладки без железа)
├── Axes_scan_default.txt           # Дефолтный файл заданий для axes_scanner
├── EXP*.txt                        # Файлы заданий экспериментов (вход сканера)
├── Axes_scan_task_*.txt            # Файлы заданий экспериментов
├── 2026.09.10_*.txt                # Файлы заданий экспериментов
├── end_switch.txt                  # Файл заданий (проверка концевиков)
├── Axes_test_task_01.txt           # Тестовый файл заданий
├── Data/                           # Рабочий каталог данных (в .gitignore)
├── Temp/                           # Рабочий каталог данных (НЕ в .gitignore)
└── Legacy/                         # Древние программы (не трогать)
```

## Как запускать

Пример для `devices_logger.py`:

```
python devices_logger.py -d "TH1992B_1.ch1~APL_I=CURR,VOLT@current;ch2~APL_I=CURR@current" "TH2690A_1~FDUK=CURR@current" -n 300 -cp 200 -fs
```

Пример для `axes_scanner.py`:

```
python axes_scanner.py -d "TH1992B_1.ch1~APL_I=CURR,RES@scan;ch2~APL_I=CURR@scan" -tf EXP2_APL+APT.txt
```

Синтаксис `-d`: `<имя>[.ch<номер>][~<пресет>]=<величины>[;ch<номер>...]`, каждая величина — `<величина>[@<имя_полотна>]`. Указание `@` выводит величину на график (полотна одного окна располагаются вертикально), отсутствие `~` означает запуск без настройки прибора.

Габариты окна/полотен задаются ключом `-pl` (например, `-pl width=12 height=6 canvas_height=2.5`), а `-np` отключает построение графиков, даже если `@` указаны в `-d`. По умолчанию окно графика закрывается по завершении программы; ключ `-ho` (`--hold`) оставляет его открытым до закрытия пользователем.

Полное описание аргументов — в `instruction.txt`, правила работы с репозиторием — в `AGENTS.md`.

## Legacy (игнорируется)

`pyLogger.py` + `pyLogger_*.bat`, `pyRetriever.py` + `Retriever_libs/`, старые сканеры (`Axes_Scan_*.py`, `Motor_Scan.py`, `Moving_To_Limits_And_Assign.py`, `scan_test_v4.py`, `step_motor_example.py`), `opencv_test_Baturin.py`, `StepMotor_libs/`, ноутбуки `*.ipynb`, `heatmap.py` и др. — см. полный список в `AGENTS.md`.