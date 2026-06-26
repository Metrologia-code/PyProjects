import argparse
from Motion_control import Controller, InitSpeed, move_axes_to_position
from User_libs import CreateSavePath, ParseTaskFile, get_experiment_file_info
from measurement_core import MeasurementSession

#---БЛОК РАЗБОРА АРГУМЕНТОВ КОМАНДНОЙ СТРОКИ---
arg_parser = argparse.ArgumentParser(
    description="Программа для автоматизации серии экспериментов сканирования щелью.")

arg_parser.add_argument('-d', '--devices', nargs='+', type=str, required=True,
    help="Имена приборов и их конфигов,\n"
         "например: -d TH1992B_1.1:FDUCK_I TH1992B_1.2:APL_I TH2690A_1:PICOAMMETER_TEST_1.")

arg_parser.add_argument('-r', '--run', nargs='+', type=int, default=None,
    help="Индексы экспериментов для запуска (например: -r 0 2 3).\n"
         "Если параметр не указан — запустятся ВСЕ эксперименты из файла.")

arg_parser.add_argument('-tf', '--taskfile', type=str, default='Axes_scan_default.txt',
    help="Путь к текстовому файлу с таблицей заданий. По умолчанию: 'Axes_scan_default.txt'.")

arg_parser.add_argument('-fs', '--faststart', action='store_true',
    help="Запуск измерений без предварительной настройки приборов.")

arg_parser.add_argument('-g', '--graph', nargs='+', type=str, default=None,
    help="Имена каналов и трансформаций для вывода на график,\n"
         "например: -g TH1992B_1.CURR1 TH1992B_1.RES1=T1:Pt100_default")

arg_parser.add_argument('-sf', '--singlefile', action='store_true',
    help="Сохранять результаты всех экспериментов в один файл.")

arg_parser.add_argument('-p', '--period', type=float, default=1.0,
    help="Период одного шага измерения в секундах. По умолчанию: 1.0 с.")

args = arg_parser.parse_args()

#---ИНИЦИАЛИЗАЦИЯ КОНТРОЛЛЕРА МОТОРОВ---
acs = Controller(ip="192.168.88.10", port=701)
acs.connect()
InitSpeed(acs)

#---ОБРАБОТКА ТАБЛИЦЫ ЗАДАНИЙ---
all_tasks = ParseTaskFile(args.taskfile)
tasks_to_run = args.run if args.run else range(len(all_tasks))
SavePath = CreateSavePath(LAN_Path='\\MetroBulk\\Public\\EXP_DATA')

#---ОСНОВНОЙ ЦИКЛ ЗАПУСКА ЭКСПЕРИМЕНТОВ---
for task_index in tasks_to_run:
    task = all_tasks[task_index]
    
    # Определяем режим файла
    file_mode = 'a' if args.singlefile and task_index != tasks_to_run[0] else 'w'
    
    if file_mode == 'w':
        full_save_path = get_experiment_file_info(task['filename'], SavePath)
    
    # Функция, которая перемещает ножи в нужную позицию и возвращает координаты
    def move_blades(point_idx, task=task):
        if point_idx == 0:
            pos_info = ", ".join(f"{ax['name']}={ax['pos'][point_idx]:.3f} мм" for ax in task['axes'])
            print(f"--> Ножи перемещаются в начальное положение: {pos_info}")
        
        move_axes_to_position(acs, task['axes'], point_idx)
        FP = [acs.get_fpos(ax['number']) for ax in task['axes']]
        
        return f'\t{FP[0]:.3f}\t{FP[1]:.3f}\t{FP[2]:.3f}\t{FP[3]:.3f}'
    
    # Создаем сессию измерений
    session = MeasurementSession(args, full_save_path, file_mode, row_prefix_callback=move_blades)
    
    # Запускаем цикл измерений
    session.run_measurement_loop(
        num_points=task['intervals'] + 1,
        task_info=f"Запуск эксперимента №{task_index}."
    )