from datetime import datetime
import time, sys, os
import argparse
import numpy as np
import threading

#библиотеки приборов
from Complex_libs.Devices import DEVICES
#библиотеки контроллера управления ножами
from Motion_control import Controller, InitSpeed, PrintPosition, StartMove, pos_to_x, move_axes_to_position
#пользовательские библиотеки
from User_libs import CreateSavePath, ParseTaskFile, build_file_header, get_experiment_file_info

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

#---ФИЛЬТРАЦИЯ, ИНИЦИАЛИЗАЦИЯ И НАСТРОЙКА СТЕНДА---
#Создаем объект измерительного комплекса, который забирает на себя всю подготовку приборов
Instruments = DEVICES(args)

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
				file.write(build_file_header(Instruments.device_data_keys) + '\n')

			#---ОСНОВНОЙ ЦИКЛ СКАНИРОВАНИЯ ПО КООРДИНАТАМ ЗАДАНИЯ---
			for cpos in range(task['intervals'] + 1):
				#Выводим информацию о переезде в начальное положение на первом шаге
				if cpos == 0:
					pos_info = ", ".join(f"{ax['name']}={ax['pos'][cpos]:.3f} мм" for ax in task['axes'])
					print(f"--> Ножи перемещаются в начальное положение: {pos_info}")

				#Фиксируем высокоточную стартовую метку времени измерения
				t_measure_start = time.perf_counter()

				#Отправляем используемые оси в следущую точку
				move_axes_to_position(acs, task['axes'], cpos)

				#Опрашиваем положение всех осей
				FP = [acs.get_fpos(ax['number']) for ax in task['axes']]
				
				#Стабилизационная задержка перед измерением
				time.sleep(t)
				
				thread_results = {}
				threads = []
				
				#Вспомогательная функция-воркер для параллельного опроса приборов
				def worker(d_name, d_obj):
					thread_results[d_name] = d_obj.SingleMeasure()
				
				#Создаем и запускаем поток для каждого подключенного прибора
				for device_name, device_obj in Instruments.Device.items():
					t_thread = threading.Thread(target=worker, args=(device_name, device_obj))
					threads.append(t_thread)
					t_thread.start()
				
				#Ждем завершения опроса абсолютно всех приборов
				for thread in threads:
					thread.join()
				
				#Вычисляем время с начала эксперимента, в которое были завершены все измерения
				measurement_time = time.time() - start_time
				
				#Последовательно собираем строку из данных
				device_results_line = ""
				
				for device_name in Instruments.Device.keys():
					results = thread_results.get(device_name)
					
					#Вытаскиваем значения по ключам. Если прибор вернул False — пишем NaN
					for key in Instruments.device_data_keys[device_name]:
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
