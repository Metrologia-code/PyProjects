## 📁 Структура проекта

```text
├── Data/                                       # Директория для записи данных (игнорируется в .gitignore)
│   └── YYYY_MM_DD/                             # Создается автоматически, если используется pyTools.py
├── INI/                                        # Директория для разных конфигурационных файлов
│   └── Instrument.ini                          # Перечень всех доступных приборов и параметров подключения
├── Legacy/                                     # Древние программы
│   ├── mesh_scan_4_TH1992B.py                  # Heatmap сканирование на TH1992B
│   ├── mesh_scan_4_TH2690A.py                  # Heatmap сканирование на TH2690A
│   └── MovingToLimitsAndAssign.py              # ???
├── Motion_control/                             # Библиотеки для контроллера осей
│   ├── Controller.py                           # Библиотека управления контроллером осей
│   └── MotionControlTools.py                   # Дополнительные библиотеки для контроллера осей
├── Retriever_libs/                             # Библиотеки ВАХ-метра
│   ├── config/                                 # Конфигурации ВАХ-метра
│   │   └── sweep_config.ini                    # Пресеты для измерения ВАХ
│   ├── retriever_tools.py                      # Библиотека функций для измерения ВАХ
│   └── retriever_widgets.py                    # Библиотека интерфейса ВАХ-метра
├── Tonghui_libs/                               # Библиотеки измерителей Tonghui
│   ├── config/                                 # Конфигурации измерителей Tonghui
│   │   ├── Tonghui_TH1992B_config.ini          # Пресеты измерерий для TH1992B
│   │   └── Tonghui_TH2690A_config.ini          # Пресеты измерерий для TH2690A
│   ├── tonghui_TH1992B.py                      # Библиотека для работы с TH1992B
│   └── tonghui_TH2690A.py                      # Библиотека для работы с TH2690A
├── User_libs/                                  # Вспомогательные библиотеки
│   ├── pyPlot.py                               # Библиотека для создания графиков
│   └── pyTools.py                              # Парсер аргументов, создание путей к файлам, и др.
├── Axes_Scan_OnTime.py                         # Сканирование ножами с шагом по времени
├── Axes_Scan_Tonghui.py                        # Сканирование ножами и измерение 1 прибором Tonghui
├── Axes_Scan_v2.py                             # Универсальный сканер ножами
├── Axes_scan_default.txt                       # Дефолтный файл с заданием для Axes_Scan_v2.py
├── Axes_Scan_Tonghui_Baturin_Calibration.py    # ???
├── opencv_test_Baturin.py                      # ???
├── pyLogger.py                                 # Универсальный логгер
├── pyRetriever.py                              # ВАХ-метр
├── daily-Alexei.sh                             # Скрипт для работы с git
├── ~.bat                                       # Исполняемые файлы для запуска .py (с параметрами)
├── .gitignore                                  # Игнорируемые файлы git
├── Git-guide.txt                               # Инструкция для работы с git
├── Axis_move.ipynb                             # 
├── Draft.ipynb                                 # 
├── opencv_test_Baturin.ipynb                   # 
├── requirements.txt                            # Список зависимостей
└── README.md                                   # Этот файл
```

