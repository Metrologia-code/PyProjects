import argparse
import time
from Motion_control import Controller, InitSpeed, MoveBlades
from Complex_libs.Devices import Devices
from User_libs import CreateSavePath, ParseTaskFile, get_experiment_file_info
from measurement import MeasurementSession

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
arg_parser.add_argument('-x', '--xaxis', type=str, default='time',
    choices=['time', 'APT', 'APL', 'APR', 'APB'],
    help="Ось X для графика. Возможные значения:\n"
         "  time  — время (по умолчанию);\n"
         "  APT   — координата оси APT;\n"
         "  APL   — координата оси APL;\n"
         "  APR   — координата оси APR;\n"
         "  APB   — координата оси APB.")
args = arg_parser.parse_args()

#---ИНИЦИАЛИЗАЦИЯ ИЗМЕРИТЕЛЬНОГО КОМПЛЕКСА---
Instruments = Devices(args)

#---ИНИЦИАЛИЗАЦИЯ КОНТРОЛЛЕРА МОТОРОВ---
acs = Controller(ip="192.168.88.10", port=701)
acs.connect()
InitSpeed(acs)

#---ОБРАБОТКА ТАБЛИЦЫ ЗАДАНИЙ---
all_tasks = ParseTaskFile(args.taskfile)
tasks_to_run = args.run if args.run else range(len(all_tasks))
SavePath = CreateSavePath(LAN_Path='\\\\MetroBulk\\Public\\EXP_DATA')

#---ПОДГОТОВКА CALLBACK ДЛЯ ОСИ X ГРАФИКА---
AXIS_NUMBERS = {'APT': 0, 'APL': 1, 'APR': 2, 'APB': 3}
if args.xaxis == 'time':
    x_callback = None
    x_label = 't, сек'
else:
    ax_num = AXIS_NUMBERS[args.xaxis]
    # x_callback читает координату из атрибута move_blades.last_positions,
    # который обновляется при каждом вызове move_blades
    x_callback = lambda n=ax_num: move_blades.last_positions[n]
    x_label = f'{args.xaxis}, мм'

#---ОСНОВНОЙ ЦИКЛ ЗАПУСКА ЭКСПЕРИМЕНТОВ---
for task_index in tasks_to_run:
    task = all_tasks[task_index]
    file_mode = 'a' if args.singlefile and task_index != tasks_to_run[0] else 'w'
    if file_mode == 'w':
        full_save_path = get_experiment_file_info(task['filename'], SavePath)

    def move_blades(point_idx, task=task):
        if point_idx == 0:
            pos_info = ", ".join(f"{ax['name']}={ax['pos'][point_idx]:.3f} мм" for ax in task['axes'])
            print(f"--> Ножи перемещаются в начальное положение: {pos_info}")
        MoveBlades(acs, task['axes'], point_idx)
        FP = [acs.get_fpos(ax['number']) for ax in task['axes']]
        move_blades.last_positions = FP
        return f'\t{FP[0]:.3f}\t{FP[1]:.3f}\t{FP[2]:.3f}\t{FP[3]:.3f}'

    prefix = 'time, s\tAPT pos, mm\tAPL pos, mm\tAPR pos, mm\tAPB pos, mm'
    session = MeasurementSession(
        args, 
        Instruments,
        full_save_path, 
        file_mode, 
        header_prefix=prefix, 
        row_prefix_callback=move_blades,
        task_info=f"Запуск эксперимента №{task_index + 1}.",
        wait_callback=lambda task=task: time.sleep(task['post_delay']),
        x_callback=x_callback,
        x_label=x_label
    )
    session.run_measurement_loop(
        num_points=task['intervals'] + 1
    )

if 'session' in locals() and session.Plots:
    session.Plots.keep_open()