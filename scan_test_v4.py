#import matplotlib.pyplot as plt
from datetime import datetime
import time, sys, os
import argparse
import numpy as np
from itertools import count
import threading

#библиотеки приборов Tonghui
import Tonghui_libs
#библиотеки контроллера управления ножами
from Motion_control import Controller, InitSpeed, PrintPosition, StartMove, pos_to_x
#пользовательские библиотеки
from User_libs import CreateSavePath, ParseTaskFile, ReadINItoDict, ParseCommandLineDevices

#принимает имя файла из задания и путь к директории сохранения, возвращает полный путь к файлу
def get_experiment_file_info(task_filename, save_path):
	base_name = task_filename.replace('.txt', '') if task_filename else datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
	
	if not os.path.exists(save_path + base_name + ".txt"):
		filename = base_name
	else:
		filename = next(f"{base_name}({n})" for n in count(1) if not os.path.exists(save_path + f"{base_name}({n}).txt"))
		
	return save_path + filename + ".txt"

#принимает объект контроллера, список осей и индекс текущей точки сканирования, перемещает ножи и ждет остановки
def move_axes_to_position(acs, axes, cpos):
	for ax in axes:
		if ax['is_used']:
			acs.ptp(ax['number'], ax['pos'][cpos])
	time.sleep(0.01)
	acs.wait()

#принимает словарь ключей приборов, возвращает шапку
def build_file_header(data_keys):
	header = 'time, s\tAPT pos, mm\tAPL pos, mm\tAPR pos, mm\tAPB pos, mm'
	for device_name, keys in data_keys.items():
		for key in keys:
			header += f'\t{device_name}.{key}'
	return header

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

#Параметр для задания фиксированного периода шага измерения в секундах
arg_parser.add_argument('-p', '--period', type=float, default=1.0,
						help="Период одного шага измерения в секундах. По умолчанию: 1.0 с.")

args = arg_parser.parse_args()

#---ФИЛЬТРАЦИЯ И АВТОМАТИЧЕСКОЕ СКЛЕИВАНИЕ КАНАЛОВ---
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
	device_data_keys[device_name] = list(probe_measure.keys())

#---ОСНОВНОЙ ЦИКЛ ЗАПУСКА ЭКСПЕРИМЕНТОВ---
for task_index in tasks_to_run:
	task = all_tasks[task_index]
	
	#Определяем режим открытия файла: для сингл-режима со второго эксперимента — дозапись 'a', иначе запись 'w'
	file_mode = 'a' if args.singlefile and task_index != tasks_to_run else 'w'
	
	#Генерируем путь: только на первом шаге для сингл-режима, либо всегда для раздельных файлов
	if file_mode == 'w':
		full_save_path = get_experiment_file_info(task['filename'], SavePath)
		
	print(f"\n Запуск эксперимента №{task_index}.")
	print(f"Результаты сохраняем в: {full_save_path}")
	
	try:
		#Время начала измерений
		start_time = time.time()
		
		with open(full_save_path, file_mode, encoding='utf-8') as file:
			
			#Подготавливаем и записываем шапку в файл (только если файл открыт в режиме перезаписи)
			if file_mode == 'w':
				file.write(build_file_header(device_data_keys) + '\n')

			#---ОСНОВНОЙ ЦИКЛ СКАНИРОВАНИЯ ПО КООРДИНАТАМ ЗАДАНИЯ---		
			for cpos in range(task['intervals'] + 1):
				#Отправляем используемые оси в следущую точку
				move_axes_to_position(acs, task['axes'], cpos)

				#Опрашиваем положение всех осей
				FP = [acs.get_fpos(ax['number']) for ax in task['axes']]
				
				#Фиксируем высокоточную стартовую метку времени измерения
				t_measure_start = time.perf_counter()
				
				thread_results = {}
				threads = []
				
				#Вспомогательная функция-воркер для параллельного опроса приборов
				def worker(d_name, d_obj):
					thread_results[d_name] = d_obj.SingleMeasure()
				
				#Создаем и запускаем поток для каждого подключенного прибора
				for device_name, device_obj in DEVICES.items():
					t_thread = threading.Thread(target=worker, args=(device_name, device_obj))
					threads.append(t_thread)
					t_thread.start()
				
				#Ждем завершения опроса абсолютно всех приборов
				for thread in threads:
					thread.join()
				
				#Вычисляем время с начала эксперимента
				measurement_time = time.time() - start_time
				
				#Последовательно опрашиваем все приборы и собираем данные
				device_results_line = ""
				
				for device_name in DEVICES.keys():
					results = thread_results.get(device_name)
					
					#Вытаскиваем значения по ключам. Если прибор вернул False — пишем NaN
					for key in device_data_keys[device_name]:
						val = results.get(key) if results else float('nan')
						device_results_line += f'\t{val:.3e}'

				#Формируем финальную строку и записываем в файл
				to_write = f'{measurement_time:.3f}\t{FP[0]:.3f}\t{FP[1]:.3f}\t{FP[2]:.3f}\t{FP[3]:.3f}' + device_results_line
				print(to_write)
				file.write(to_write + '\n')
				
				#Вычисляем фактически затраченное время на опрос и расчеты
				t_fact = time.perf_counter() - t_measure_start
				t_sleep = args.period - t_fact
				
				#Удерживаем жесткую временную сетку шага измерения
				if t_sleep > 0:
					time.sleep(t_sleep)
				else:
					print(f"[WARNING] Итерация {cpos} не уложилась в период! Затрачено: {t_fact:.3f} с из {args.period} с.")

	except KeyboardInterrupt:
		print("Программа остановлена пользователем")
		sys.exit(0)
	finally:
		#пока пусто
		pass
