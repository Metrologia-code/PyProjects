# AGENTS.md

Руководство для агентов, работающих с этим репозиторием.

## Назначение проекта

Проект — лабораторное ПО для метрологических измерений. Состоит из **двух основных программ** и их зависимостей:

- **`devices_logger.py`** — логирование данных с измерительных приборов (Tonghui) с заданным периодом, в реальном времени, с сохранением в файл и графиком.
- **`axes_scanner.py`** — автоматизация серии экспериментов сканирования щелью: читает файл заданий, перемещает ножи (оси APT/APL/APR/APB) через контроллер движения и снимает показания приборов в каждой позиции.

Всё остальное в папке проекта (см. раздел «Игнорируемые файлы») — legacy-скрипты, отдельные утилиты и старые версии. Их НЕ трогать и не учитывать.

## Обязательные правила

1. Работать только с файлами, относящимися к `devices_logger.py` и `axes_scanner.py` (см. разделы ниже).
2. Запускать программы ТОЛЬКО из корня проекта (пути в коде относительные).
3. Комментарии в коде и вывод программ — на русском (существующий стиль).
4. Зависимости (`requirements.txt`) не урезать: там указаны также пакеты для игнорируемых утилит.
5. Директории `Data/` и `Temp/` — рабочие каталоги данных, они в .gitignore; результаты туда пишутся автоматически.
6. Не менять механизм подключения дамми-библиотек (см. раздел «Дамми-библиотеки»).

## Как запускать

Основные аргументы CLI задокументированы в `instruction.txt` (источник истины). Кратко:

### devices_logger.py

```
python devices_logger.py -d ИМЯ_ПРИБОРА[.номер_канала]:ИМЯ_ПРЕСЕТА [ИМЯ_ПРИБОРА...] \
    [-fs] [-g ИМЯ_ПРИБОРА.ВЕЛИЧИНА[номер_канала] ...] [-p СЕК] [-n ТОЧКИ] [-cp ТОЧКИ_ГРАФИКА]
```

- `-fs` / `--faststart` — запуск без предварительной настройки приборов.
- `-g` / `--graph` — каналы для графика (пример: `-g TH1992B_1.CURR1 TH2690A_1.CURR`).
- `-p` / `--period` — период шага измерения, сек (по умолч. 1.0).
- `-f` / `--filename` — имя файла результатов; если не задано — генерируется автоматически.
- `-n` / `--points` — число измерений (по умолч. 999999).
- `-cp` / `--canvaspoints` — точек по оси X на графике (по умолч. 3600).

Пример:
```
python devices_logger.py -d TH1992B_1.1:APL_I TH1992B_1.2:APL_I TH2690A_1:FDUK -g TH1992B_1.CURR1 TH1992B_1.CURR2 TH2690A_1.CURR -n 300 -cp 200 -fs
```

### axes_scanner.py

```
python axes_scanner.py -d ИМЯ_ПРИБОРА[.номер_канала]:ИМЯ_ПРЕСЕТА [ИМЯ_ПРИБОРА...] \
    [-r ИНДЕКСЫ 0 2 3] [-tf ПУТЬ_К_ЗАДАНИЮ] [-fs] [-g КАНАЛЫ] [-sf] [-x time|APT|APL|APR|APB]
```

- `-r` / `--run` — индексы экспериментов из файла заданий (по умолч. все).
- `-tf` / `--taskfile` — путь к файлу заданий (по умолч. `Axes_scan_default.txt`).
- `-sf` / `--singlefile` — сохранять все эксперименты в один файл.
- `-x` / `--xaxis` — ось X графика: время или координата одной из осей.

Пример:
```
python axes_scanner.py -d TH1992B_1.1:APL_I TH1992B_1.2:APL_I -g TH1992B_1.CURR1 TH1992B_1.CURR2 -tf EXP2_APL+APT.txt
```

## Структура ядра проекта

```
devices_logger.py           # Гл. программа 1: логгер приборов
axes_scanner.py             # Гл. программа 2: сканер щелью (чтение заданий + движение осей + измерение)
measurement.py              # Общий движок MeasurementSession: цикл опроса, запись, график, Ctrl+C
instruction.txt             # Документация CLI обеих программ и форматов конфигов приборов
requirements.txt            # Зависимости Python (НЕ урезать)
AGENTS.md                   # Этот файл
README.md                   # Описание структуры проекта (поддерживать в актуальном виде)

Complex_libs/
    Devices.ini             # Пул приборов: имя -> папка библиотеки, имя драйвера, подключение, число каналов
    Devices.py              # Класс Devices: чтение пула, разбор CLI-списка приборов, динамический импорт драйверов
    __init__.py

User_libs/
    pyTools.py              # Основные утилиты (см. ниже)
    pyPlotter.py            # Plotter: графики в реальном времени
    pyPlot.py               # Планировщик-предшественник (PlotterClass), переэкспортируется __init__.py
    __init__.py             # from .pyPlot import * / .pyPlotter import * / .pyTools import *

Tonghui_libs/
    tonghui_TH1992B.py      # Драйвер TH1992B (2 канала)
    tonghui_TH2690A.py      # Драйвер TH2690A (1 канал)
    __tonghui_TH1992B.py    # Дамми-драйвер TH1992B (виртуальный, для отладки без железа)
    __tonghui_TH2690A.py    # Дамми-драйвер TH2690A
    __init__.py             # from . import tonghui_TH2690A, tonghui_TH1992B
    config/
        Tonghui_TH1992B_config.ini   # Пресеты измерений TH1992B
        Tonghui_TH2690A_config.ini   # Пресеты измерений TH2690A

Motion_control/
    Controller.py           # Контроллер ACS (TCP, по умолч. 192.168.88.10:701): connect, ptp, wait, get_fpos и т.д.
    MotionControlTools.py   # InitSpeed, MoveBlades, pos_to_x, PrintPosition
    __init__.py             # from .Controller import * / from .MotionControlTools import * (НАСТОЯЩИЙ)
    __init__dummy.py        # Дамми-версия (виртуальный контроллер, для отладки без железа)

Axes_scan_default.txt       # Файл заданий по умолчанию для axes_scanner
EXP*.txt, Axes_scan_task_*.txt, 2029.09.10_*.txt, end_switch.txt, Axes_test_task_01.txt
                            # Рабочие файлы заданий экспериментов (вход для axes_scanner)
```

## Ключевые конвенции и точки интеграции

### 1. Пул приборов и синтаксис `-d` (`Complex_libs/Devices.py`, `User_libs/pyTools.py`)

- `Devices.ini` задаёт состав приборов: `[TH1992B_1]` → `LibraryFolder/Tonghui_libs`, `LibraryName/tonghui_TH1992B`, `ConnectionMethod/TCPIP`, `DeviceAddress:DevicePort`, `Channels=2`.
- Синтаксис CLI: `ИмяПрибора[.номер_канала]:ИмяПресета`. Для многоканального прибора каналы указываются через точку (`TH1992B_1.2`), конфиг задаётся для каждого канала отдельно.
- Если пресет не указан — используется `FastStart`; флаг `-fs` переводит все каналы в `FastStart`.
- Драйвер подключается динамически: `importlib.import_module(f"{LibraryFolder}.{LibraryName}")` → класс `Device`.

### 2. Контракт драйвера прибора

Любой драйвер (в т.ч. дамми) обязан реализовывать класс `Device` с методами:

- `Initialize(**connection_details)` → bool;
- `ConfigureDevice(ConfigName)` → bool (`ConfigName` — строка пресета или `{канал: пресет}` для многоканальных);
- `SingleMeasure()` → dict вида `{'CURR1': ..., 'RES1': ..., 'VOLT1': ...}` (ключи — имена величин; для многоканального прибора суффикс — номер канала).

`Devices` после настройки делает пробное `SingleMeasure()` и фиксирует `device_data_keys` (она же — шапка файла).

### 3. Гибкая замена драйверов (настройка Les commandes_dummy)

Дамми-библиотеки включаются НЕ через код или конфиги, а **временным переименованием файлов**:

- **Tonghui**: дамми `__tonghui_TH1992B.py` переименовывается в `tonghui_TH1992B.py`, а настоящий `tonghui_TH1992B.py` — во `tonghui_TH1992B_.py` (или `_real`). То же для `__tonghui_TH2690A.py`/`tonghui_TH2690A.py`. `Tonghui_libs/__init__.py` и `Devices.ini` не меняются — импорт идёт по имени.
- **Motion_control**: дамми `__init__dummy.py` переименовывается в `__init__.py`, а настоящий `__init__.py` — в `__init__.py_` (или `__init__real.py`).
- После окончания отладки имена возвращаются как были (реальный файл — основное имя, дамми — с `__`/суффиксом `dummy`).
- После переименования полезно очистить `__pycache__`, чтобы не подхватывался устаревший байткод.

### 4. Файлы заданий axes_scanner (`ParseTaskFile` в `User_libs/pyTools.py`)

TSV-файл, строки: комментарии отрезаются по `#`, пустые строки пропускаются.

```
#APT	APL	APR	APB	intvls	post_delay	filename
10:20	20	20	20	15	0.5	test_file_1.txt #здесь можно комментарий написать
10:25	25	25	25	15	0.1	test_file_2.txt
```

- Колонки: `APT APL APR APB  intvls  post_delay  filename`.
- Значение оси: диапазон `start:end` или одиночное число (ось неподвижна, `is_used=False`).
- `intvls` — число интервалов; координаты строятся через `np.linspace(start, end, intervals + 1)`.
- `post_delay` — пауза после выхода позиции (по умолч. 0.0); `filename` — имя файла результата (по умолч. генерируется).
- Номера осей для контроллера: `APT=0, APL=1, APR=2, APB=3` (словарь `AXIS_NUMBERS` в `axes_scanner.py`).

### 5. Движение осей (`Motion_control`)

- `Controller` общается с контроллером ACS по TCP-сокету.
- `InitSpeed(acs)` — включение осей и установка скоростей.
- `MoveBlades(acs, axes, cpos)` — на `cpos==0` двигает все оси в `start`, далее только используемые (`is_used`). Обновляет позиции для графика.
- `axes_scanner.py` в каждом шаге вызывает `move_blades` как `row_prefix_callback`: координаты осей дописываются в строку результата.

### 6. Цикл измерения и файл результата (`measurement.py`)

- `MeasurementSession.run_measurement_loop(num_points)` — последовательный проход: параллельно опрашивает все приборы (потоки), формирует TSV-строку `время + prefix + значения`.
- Заголовок пишется при `file_mode='w'` через `build_file_header`, сброс буфера на диск — раз в минуту.
- При `-g` строится `Plotter`; график сохраняется в PNG рядом с .txt; Ctrl+C сохраняет рисунок и завершает программу.
- Путь сохранения: `CreateSavePath('\\\\MetroBulk\\Public\\EXP_DATA')` — при доступности сетевого хранилища туда, иначе локально в `Data/<ГГГГ_ММ_ДД>/`; имя файла уникализируется (суффикс `(n)`).

### 7. График (`User_libs/pyPlotter.py`)

- Синтаксис каналов: `ИмяПрибора.Параметр[номер канала]`, напр. `TH1992B_1.CURR1`, `TH2690A_1.CURR`.
- Имя параметра должно содержать `CURR`/`VOLT`/`RES` (для размерности `I`/`V`/`Ohm`).
- Трансформации: `Параметр=Имя:Настройка`, напр. `TH1992B_1.RES1=T1:Pt100_default` (преобразование сопротивления Pt100 в температуру, см. `Transformation.Trasform_RES_to_Temp` в `pyTools.py`).
- Аргументы `-g` делятся пополам: первая половина — левая ось Y, вторая — правая.

## Игнорируемые файлы (legacy, отдельные утилиты, старые версии)

НЕ связаны с двумя главными программами — не изменять, не использовать, не ломать:

- `pyLogger.py`, все `pyLogger_*.bat` (предшественник devices_logger.py).
- `pyRetriever.py`, `pyRetriever_VAH-meter.bat`, `Retriever_libs/` (ВАХ-метр).
- Старые сканеры: `Axes_Scan_v2.py`, `Axes_Scan_Tonghui.py`, `Axes_Scan_Tonghui_Baturin_Calibration.py` + их `.bat`, `Axes_Scan_OnTime.py`, `Motor_Scan.py`, `Moving_To_Limits_And_Assign.py`, `scan_test_v4.py`, `step_motor_example.py`.
- `opencv_test_Baturin.py`, ноутбуки `*.ipynb`.
- `StepMotor_libs/`, `Legacy/`.
- `User_libs/heatmap.py`, `User_libs/creat_mapping_testfile.py`, `User_libs/experiment_data.txt`.
- `daily-Alexei.sh`, `daily-Luparev.sh`, `Git-guide.txt`, `terminal.txt`.
- `Data/`, `Temp/` — рабочие каталоги данных.