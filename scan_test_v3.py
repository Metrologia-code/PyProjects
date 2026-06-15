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
arg_parser = argparse.ArgumentParser(
    description="Программа для автоматизации серии экспериментов сканирования щелью.")

#Обязательный параметр для выбора приборов и их конфигураций
arg_parser.add_argument('-d', '--devices', nargs='+', type=str, required=True,
                        help="Имена приборов и их конфигов,\n"
                             "например: -d TH1992B_1.1:FDUCK_I TH1992B_1.2:APL_I TH2690A_1:PICOAMMETER_TEST_1.")

#Параметр для выбора конкретных экспериментов (необязательный)
arg_parser.add_argument('-r', '--run', nargs='+', type=int, default=None,
                        help="Индексы экспериментов для запуска (например: -r 0 2 3).\n"
                             "Если параметр не указан — запустятся ВСЕ эксперименты из файла.")

#Параметр для выбора файла с заданиями (необязательный, с дефолтным значением)
arg_parser.add_argument('-tf', '--taskfile', type=str, default='Axes_scan_default.txt',
                        help="Путь к текстовому файлу с таблицей заданий. По умолчанию: 'Axes_scan_default.txt'.")

#Параметр для запуска измерений без предварительной настройки приборов
arg_parser.add_argument('-fs', '--faststart', action='store_true',
                        help="Запуск измерений без предварительной настройки приборов.")

#Параметр для включения отображения графиков во время эксперимента
arg_parser.add_argument('-g', '--graph', action='store_true',
                        help="Включить построение графиков во время измерений.")

#Параметр для сохранения всех результатов в один общий файл
arg_parser.add_argument('-sf', '--singlefile', action='store_true',
                        help="Сохранять результаты всех экспериментов в один файл.")

args = arg_parser.parse_args()

#---ФИЛЬТРАЦИЯ И АВТОМАТИЧЕСКОЕ СКЛЕИЕМЫЕ КАНАЛОВ---
#1. Считываем все доступные приборы в теле программы
devices_pool = ReadINItoDict('INI', 'Instrument.ini')

#2. Передаем список из консоли и считанный словарь приборов в функцию разбора
req_devices = ParseCommandLineDevices(args.devices, devices_pool)

print(req_devices)

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

#---ОБРАБОТКА ТАБЛИЦЫ ЗАДАНИЙ И ПОДГОТОВКА ПУТИ---
#Считываем список всех экспериментов из текстового файла
all_tasks = ParseTaskFile(args.taskfile)

#Определяем индексы экспериментов, которые нужно запустить
tasks_to_run = args.run if args.run else range(len(all_tasks))

#Генерируем путь к папке сохранения результатов
SavePath = CreateSavePath(LAN_Path='\\\\MetroBulk\\Public\\EXP_DATA', )

#Делаем пробный опрос приборов для фиксации ключей возвращаемых данных
device_data_keys = {}
for device_name, device_obj in DEVICES.items():
    probe_measure = device_obj.SingleMeasure()
    print(f'Пробное измерение:\n{probe_measure}')
    device_data_keys[device_name] = list(probe_measure.keys())

#---ОСНОВНОЙ ЦИКЛ ЗАПУСКА ЭКСПЕРИМЕНТОВ---
for task_index in tasks_to_run:
    task = all_tasks[task_index]
    
    #Формируем путь к файлу: для сингл-режима только на первом шаге, иначе для каждого таска
    if not args.singlefile or task_index == tasks_to_run[0]:
        if task['filename']:
            current_filename = task['filename']
        else:
            current_filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".txt"
        full_save_path = SavePath + current_filename
        
    print(f"\n Запуск эксперимента №{task_index}.")
    print(f"Результаты сохраняем в: {full_save_path}")
    
    try:
        #Время начала измерений
        start_time = time.time()
        
        #Определяем режим открытия файла: для сингл-режима со второго эксперимента — дозапись 'a', иначе запись 'w'
        file_mode = 'a' if args.singlefile and task_index != tasks_to_run[0] else 'w'
        
        with open(full_save_path, file_mode, encoding='utf-8') as file:
            
            #Подготавливаем и записываем шапку в файл (только если файл открыт в режиме перезаписи)
            if file_mode == 'w':
                header = 'time, s\tAPT pos, mm\tAPL pos, mm\tAPR pos, mm\tAPB pos, mm'
                
                #Динамически формируем колонки на основе реальных ключей из SingleMeasure
                for device_name, keys in device_data_keys.items():
                    for key in keys:
                        header += f'\t{device_name}.{key}'
                        
                file.write(header + '\n')

            #---ОСНОВНОЙ ЦИКЛ СКАНИРОВАНИЯ ПО КООРДИНАТАМ ЗАДАНИЯ---
            intervals = task['intervals']
            axes = task['axes']
            
            for cpos in range(intervals + 1):
                #Отправляем используемые оси в следущую точку
                for ax in axes:
                    if ax['is_used']:
                        acs.ptp(ax['number'], ax['pos'][cpos])
                
                #Ожидаем окончания движения всех осей
                time.sleep(0.01)
                acs.wait()

                #Опрашиваем положение всех осей
                FP = [acs.get_fpos(ax['number']) for ax in axes]
                
                #Стабилизационная задержка перед измерением
                time.sleep(t)
                
                #Последовательно опрашиваем все приборы и собираем данные
                measurement_time = time.time() - start_time
                device_results_line = ""
                measurement_failed = False
                
                for device_name, device_obj in DEVICES.items():
                    results = device_obj.SingleMeasure()
                    
                    #выполняем, если прибор вернул измерения, иначе прерываем шаг
                    if results:
                        device_results_line += "".join(f"\t{val:.3e}" for val in results.values())
                    else:
                        measurement_failed = True
                        break

                #Если хотя бы один прибор сбоит — пропускаем запись этой точки
                if measurement_failed:
                    continue

                #Формируем финальную строку и записываем в файл
                to_write = f'{measurement_time:.3f}\t{FP[0]:.3f}\t{FP[1]:.3f}\t{FP[2]:.3f}\t{FP[3]:.3f}' + device_results_line
                print(to_write)
                file.write(to_write + '\n')

    except KeyboardInterrupt:
        print("Программа остановлена пользователем")
        sys.exit(0)
    finally:
        #пока пусто
        pass
