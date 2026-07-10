import argparse
from datetime import datetime
from Complex_libs.Devices import Devices
from User_libs import CreateSavePath, get_experiment_file_info
from measurement import MeasurementSession

#---БЛОК РАЗБОРА АРГУМЕНТОВ---
arg_parser = argparse.ArgumentParser(
    description="Программа для логирования данных с приборов.")

arg_parser.add_argument('-d', '--devices', nargs='+', type=str, required=True,
    help="Имена приборов и их конфигов")

arg_parser.add_argument('-fs', '--faststart', action='store_true',
    help="Запуск измерений без предварительной настройки приборов.")

arg_parser.add_argument('-g', '--graph', nargs='+', type=str, default=None,
    help="Имена каналов для вывода на график")

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
full_save_path = get_experiment_file_info(args.filename, SavePath)

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