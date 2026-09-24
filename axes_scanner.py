import argparse
import os
import time
from Motion_control import Controller, InitSpeed, MoveBlades
from Complex_libs.Devices import Devices
from User_libs import CreateSavePath, ParseTaskFile, get_experiment_file_info
from measurement import MeasurementSession

#---БЛОК РАЗБОРА АРГУМЕНТОВ КОМАНДНОЙ СТРОКИ---
arg_parser = argparse.ArgumentParser(
    description="Программа для автоматизации серии экспериментов сканирования щелью.")
arg_parser.add_argument('-d', '--devices', nargs='+', type=str, required=True,
    help="Описание устройств в формате\n"
         "<имя>[.ch<номер>][~<пресет>]=<величины>[;ch<номер>[~<пресет>]=<величины>...],\n"
         "где каждая величина — <величина>[@<имя_полотна>].\n"
         "Пример: TH1992B_1.ch1~FDUCK_I=CURR,RES;ch2~APL_I=CURR TH2690A_1~PICOAMMETER_TEST_1=CURR")
arg_parser.add_argument('-r', '--run', nargs='+', type=int, default=None,
    help="Индексы экспериментов для запуска (например: -r 0 2 3).\n"
         "Если параметр не указан — запустятся ВСЕ эксперименты из файла.")
arg_parser.add_argument('-tf', '--taskfile', type=str, default='Axes_scan_default.txt',
    help="Путь к текстовому файлу с таблицей заданий. По умолчанию: 'Axes_scan_default.txt'.")
arg_parser.add_argument('-fs', '--faststart', action='store_true',
    help="Запуск измерений без предварительной настройки приборов.")
arg_parser.add_argument('-pl', '--plot', nargs='+', type=str, default=None,
    help="Настройки окна графиков в формате key=value (габариты):\n"
         "  width=<дюймы>, height=<дюймы> — размер окна;\n"
         "  canvas_height=<дюймы> — высота одного полотна;\n"
         "  n_cols=<число> — число колонок полотен;\n"
         "  figure_width_step=<дюймы> — запас ширины на дополнительную ось Y.")
arg_parser.add_argument('-np', '--noplot', action='store_true',
    help="Отключить построение графиков, даже если полотна указаны в -d.")
arg_parser.add_argument('-ho', '--hold', action='store_true',
    help="Не закрывать окно графиков по завершении программы — ждать закрытия пользователем.")
arg_parser.add_argument('-sf', '--singlefile', action='store_true',
    help="Сохранять результаты всех экспериментов в один файл.")
arg_parser.add_argument('-x', '--xaxis', type=str, default='time',
    choices=['time', 'APT', 'APL', 'APR', 'APB'],
    help="Ось X для графика по умолчанию (если задание не переопределяет её столбцом x_axis).\n"
         "Возможные значения:\n"
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
#Режим для авто-имени файла результатов — имя файла задания без расширения
mode_prefix = os.path.splitext(os.path.basename(args.taskfile))[0]
SavePath = CreateSavePath(LAN_Path='\\\\MetroBulk\\Public\\EXP_DATA')

#---ОСНОВНОЙ ЦИКЛ ЗАПУСКА ЭКСПЕРИМЕНТОВ---
session = None
for task_index in tasks_to_run:
    task = all_tasks[task_index]
    file_mode = 'a' if args.singlefile and task_index != tasks_to_run[0] else 'w'
    if file_mode == 'w':
        full_save_path = get_experiment_file_info(task['filename'], SavePath, mode_prefix=mode_prefix)

    def move_blades(point_idx, task=task):
        if point_idx == 0:
            pos_info = ", ".join(f"{ax['name']}={ax['pos'][point_idx]:.3f} мм" for ax in task['axes'])
            print(f"--> Ножи перемещаются в начальное положение: {pos_info}")
        MoveBlades(acs, task['axes'], point_idx)
        FP = [acs.get_fpos(ax['number']) for ax in task['axes']]
        move_blades.last_positions = FP
        return f'\t{FP[0]:.3f}\t{FP[1]:.3f}\t{FP[2]:.3f}\t{FP[3]:.3f}'

    #Ось X для графика: столбец x_axis задания переопределяет глобальный -x
    x_name = task['x_axis'] or args.xaxis
    if x_name == 'time':
        x_callback = None
        x_label = 't, сек'
    else:
        ax_num = next(ax['number'] for ax in task['axes'] if ax['name'] == x_name)
        # x_callback читает координату из атрибута move_blades.last_positions,
        # который обновляется при каждом вызове move_blades
        x_callback = lambda n=ax_num: move_blades.last_positions[n]
        x_label = f'{x_name}, мм'

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

# Конец программы: окно графика по умолчанию закрывается вместе с процессом,
# ключ -ho/--hold удерживает его открытым до закрытия пользователем
if session is not None and session.Plots is not None and args.hold:
    session.Plots.keep_open()