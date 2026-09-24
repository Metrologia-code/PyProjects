import argparse
from datetime import datetime
from Complex_libs.Devices import Devices
from User_libs import CreateSavePath, get_experiment_file_info
from measurement import MeasurementSession

#---БЛОК РАЗБОРА АРГУМЕНТОВ---
arg_parser = argparse.ArgumentParser(
    description="Программа для логирования данных с приборов.")

arg_parser.add_argument('-d', '--devices', nargs='+', type=str, required=True,
    help="Описание устройств в формате\n"
         "<имя>[.ch<номер>][~<пресет>]=<величины>[;ch<номер>[~<пресет>]=<величины>...],\n"
         "где каждая величина — <величина>[@<имя_полотна>].\n"
         "Пример: TH1992B_1.ch1~TEST_VOLT=CURR,VOLT@p1;ch2=CURR@p1 TH2690A_1~PRESET_1=CURR@p2")

arg_parser.add_argument('-fs', '--faststart', action='store_true',
    help="Запуск измерений без предварительной настройки приборов.")

arg_parser.add_argument('-pl', '--plot', nargs='+', type=str, default=None,
    help="Настройки окна графиков в формате key=value (габариты):\n"
         "  width=<дюймы>, height=<дюймы> — размер окна;\n"
         "  canvas_height=<дюймы> — высота одного полотна;\n"
         "  n_cols=<число> — число колонок полотен.")

arg_parser.add_argument('-np', '--noplot', action='store_true',
    help="Отключить построение графиков, даже если полотна указаны в -d.")

arg_parser.add_argument('-ho', '--hold', action='store_true',
    help="Не закрывать окно графиков по завершении программы — ждать закрытия пользователем.")

arg_parser.add_argument('-p', '--period', type=float, default=1.0,
    help="Период одного шага измерения в секундах")

arg_parser.add_argument('-f', '--filename', type=str, default=None,
    help="Имя файла для сохранения результатов. Если не указано — генерируется автоматически")

arg_parser.add_argument('-n', '--points', type=int, default=999999,
    help="Количество измерений (точек). По умолчанию: 999999")

arg_parser.add_argument('-cp', '--canvaspoints', type=int, default=3600,
    help="Количество точек по оси X на графике. По умолчанию: 3600")

args = arg_parser.parse_args()

#---ИНИЦИАЛИЗАЦИЯ ИЗМЕРИТЕЛЬНОГО КОМПЛЕКСА---
Instruments = Devices(args)

#---ПОДГОТОВКА ПУТИ---
SavePath = CreateSavePath(LAN_Path='\\\\MetroBulk\\Public\\EXP_DATA')
full_save_path = get_experiment_file_info(args.filename, SavePath, mode_prefix='logger')

#---ЗАПУСК ЛОГГЕРА---
session = MeasurementSession(
    args, 
    Instruments, 
    full_save_path, 
    file_mode='w', 
    canvas_points=args.canvaspoints
)

#---ВЫВОД ПАРАМЕТРОВ ЭКСПЕРИМЕНТА---
whole_time = (args.points - 1) * args.period
print(f'''
Желаемое время измерения\t= {args.period} сек
Количество измерений (точек)\t= {args.points}
Ожидаемое время выполнения\t= {whole_time / 3600:.2f} ч ({whole_time:.0f} сек)
...........
Время начала измерений: \t{datetime.now().strftime('%Y-%m-%d %H:%M')}
''')

session.run_measurement_loop(num_points=args.points)

# Конец программы: окно графика по умолчанию закрывается вместе с процессом,
# ключ -ho/--hold удерживает его открытым до закрытия пользователем
if session is not None and session.Plots is not None and args.hold:
    session.Plots.keep_open()