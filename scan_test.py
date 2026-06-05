#import matplotlib.pyplot as plt
from datetime import datetime
import time, sys
import argparse
import numpy as np

#библиотеки приборов Tonghui
import Tonghui_libs
#библиотеки контроллера управления ножами
from Motion_control import Controller, InitSpeed, PrintPosition, StartMove, pos_to_x
#пользовательские библиотеки
from User_libs import CreateSavePath, ParseTaskFile, ReadINItoDict, ParseCommandLineDevices

#---БЛОК РАЗБОРА АРГУМЕНТОВ КОМАНДНОЙ СТРОКИ---
arg_parser = argparse.ArgumentParser(description="Программа для автоматизации серии экспериментов сканирования щелью.")

#Обязательный параметр для выбора приборов и их конфигураций
arg_parser.add_argument('-d', '--devices', nargs='+', type=str, required=True,
                        help="Имена приборов и их конфигов (например: -d TH1992B_1.1:FDUCK_I TH1992B_1.2:APL_I TH2690A_1:PICOAMMETER_TEST_1).")

#Параметр для выбора конкретных экспериментов (необязательный)
arg_parser.add_argument('-r', '--run', nargs='+', type=int, default=None,
                        help="Индексы экспериментов для запуска. Если параметр не указан — запустятся ВСЕ эксперименты из файла.")

#Параметр для выбора файла с заданиями (необязательный, с дефолтным значением)
arg_parser.add_argument('-tf', '--taskfile', type=str, default='Axes_scan_default.txt',
                        help="Путь к текстовому файлу с таблицей заданий. По умолчанию: 'Axes_scan_default.txt'.")

#Параметр для запуска измерений без предварительной настройки приборов
arg_parser.add_argument('-fs', '--faststart', action='store_true',
                        help="Запуск измерений без предварительной настройки приборов.")

args = arg_parser.parse_args()

#---ФИЛЬТРАЦИЯ И АВТОМАТИЧЕСКОЕ СКЛЕИВАНИЕ КАНАЛОВ---
#1. Считываем все доступные приборы в теле программы
devices_pool = ReadINItoDict('INI', 'Instrument.ini')

#2. Передаем список из консоли и считанный словарь приборов в функцию разбора
req_devices = ParseCommandLineDevices(args.devices, devices_pool)

#---ИНИЦИАЛИЗАЦИЯ И НАСТРОЙКА ПРИБОРОВ---
#Словарь для хранения объектов подключенных приборов
DEVICES = {}

for device_name, device_info in req_devices.items():
    lib_name = device_info['LibraryName']
    
    DEVICE = getattr(Tonghui_libs, lib_name).Device()
    
    #Берем параметры подключения из INI
    connection_details = devices_pool[device_name].copy()
    
    if not DEVICE.Initialize(**connection_details):
        sys.exit(1)
        
    #Вызываем конфигурацию всегда, передавая имя пресета и флаг быстрого запуска
    device_config = device_info['Config']
    if not DEVICE.ConfigureDevice(ConfigName=device_config, FastStart=args.faststart):
        sys.exit(1)
        
    #Сохраняем настроенный прибор в словарь активных приборов
    DEVICES[device_name] = DEVICE

    
#подключаемся к контроллеру моторов осей и устанавливаем скорости движения
acs = Controller(ip="192.168.88.10", port=701)
acs.connect()
InitSpeed(acs)
 
#Списки для построения графика
FPosition = list()
Current = list()

#Задержка перед измерением после остановки осей
t = 0.1

#теперь надо открывать цикл экспериментов
