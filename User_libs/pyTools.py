from datetime import datetime
import os, sys
import configparser
import numpy as np
from itertools import count
from .TaskFileParser import TaskFileParser


def ParseLoggerArguments(LaunchArguments=None, ):
    ''' принимает список из аргументов в формате строк
        возвращает словарь с правильными типами данных '''
    #создаем словарь из аргументов, с которыми была запущена программа
    Arguments = dict(arg.split(':', 1) for arg in LaunchArguments)
    #словарь для парсинга аргументов
    conversions = {
        #парсим ConfigName, если он словарь (для двухканального TH1992B)
        'ConfigName': lambda x: dict(arg.split(':', 1) for arg in x.split(',')) if ':' in x else x,
        #преобразуем строки в числа
        'MeasTime': float,
        'MeasPoints': int,
        'CanvasPoints': int,
        #формируем списки из имен измеряемых величин
        'DataNames': lambda x: x.split(','),
        'LineNames': lambda x: x.split(','),
        #конвертируем строки в булевые переменные
        'EnablePlot': lambda x: {'true': True, 'false': False}[x.lower()],
        'YTransform': lambda x: {'true': True, 'false': False}[x.lower()],
    }
    #парсим аргументы
    for key, converter in conversions.items():
        if key in Arguments:
            Arguments[key] = converter(Arguments[key])
    return Arguments

def CreateDirIfNot(dirpath):
    try:
        os.mkdir(dirpath)
    except:
        pass

def CreateSavePath(LAN_Path=None, ):
    ''' LAN_Path - путь к файловому хранилищу
        формирует путь к папке для сохранения данных
        и создает в ней подпапку с текущей датой
        возвращает путь в виде строки '''
    ProgramPath = os.getcwd()
    TodayNameDir = '\\' + datetime.now().strftime("%Y_%m_%d") + '\\'
    #сохраняем в хранилище MetroBulk, если оно доступно
    if os.path.exists(LAN_Path):
        SavePath = LAN_Path + TodayNameDir
    #если подключение к MetroBulk отсутствует - сохраняем в местную папку Data
    else:
        DataPath = ProgramPath + '\\Data'
        #создаем папку Data в корне, если ее нет
        CreateDirIfNot(DataPath)
        SavePath = DataPath + TodayNameDir
    #создаем папку с текущей датой, если ее нет
    CreateDirIfNot(SavePath)
    return SavePath

def CreateCameraPath(file, ):
    try:
        ProgramPath = os.path.dirname(os.path.abspath(file))
    except NameError:
        ProgramPath = os.getcwd()
    TodayNameDir = '\\' + datetime.now().strftime("%Y_%m_%d") + '\\'
    #сохраняем в хранилище MetroBulk, если оно доступно

    DataPath = ProgramPath + '\\OpenCV'
    #создаем папку Data в корне, если ее нет
    CreateDirIfNot(DataPath)
    SavePath = DataPath + TodayNameDir
    #создаем папку с текущей датой, если ее нет
    CreateDirIfNot(SavePath)
    return SavePath

def FormatTime(seconds, ):
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d} час {m:02d} мин {s:02d} сек" if h else f"{m:02d} мин {s:02d} сек" if m else f"{s:02d} сек"


'''#****** Парсер текстового файла со списком экспериментов для сканирования щелью
def ParseTaskFile(task_filename, ):
    #
    def parse_axis_values(value_str):
        # Разбираем '-6:6' или '20' в кортеж (start, end)
        parts = value_str.split(":")
        start, end = parts if len(parts) > 1 else parts * 2
        return float(start), float(end)
    #---ПАРСИНГ ТЕКСТОВОГО ФАЙЛА---
    ALL_TASKS = []
    with open(task_filename, "r", encoding="utf-8") as file:
        for line in file:
            #1. Отрезаем комментарий, убираем пробелы по краям и режем по табуляции
            parts = line.split('#')[0].strip().split('\t')
            #2. Пропускаем строку, если она пустая
            if parts == ['']: continue
            #а вот как можно было одной строкой
            #if (parts := line.split('#')[0].strip().split('\t')) == ['']: continue
            #3. Заполняем intervals (всегда 5-й элемент по счету)
            intervals = int(parts[4])
            #4. Проверяем имя файла (6-й элемент по счету). Если его нет — оставляем пустым
            filename = (parts[5:] or [""])[0].strip()
            #5. Парсим значения координат и формируем словарь осей
            apt, apl, apr, apb = map(parse_axis_values, parts[:4])
            axes = [
                {'name': 'APT', 'number': 0, 'start': apt[0], 'end': apt[1]},
                {'name': 'APL', 'number': 1, 'start': apl[0], 'end': apl[1]},
                {'name': 'APR', 'number': 2, 'start': apr[0], 'end': apr[1]},
                {'name': 'APB', 'number': 3, 'start': apb[0], 'end': apb[1]} ]
            #Добавляем к словарям осей массивы координат и информацию об их использовании
            for ax in axes:
                ax['pos'] = np.linspace(ax['start'], ax['end'], intervals + 1)
                ax['is_used'] = (ax['start'] != ax['end'])
                #start, end = ax['start'], ax['end']
                #ax['pos'] = [start + i * (end - start) / intervals for i in range(intervals + 1)]
                #ax['is_used'] = (start != end)
            #6. Сохраняем словарь-эксперимент в общий пул
            ALL_TASKS.append({'axes': axes, 'intervals': intervals, 'filename': filename})
    return ALL_TASKS'''

def ParseTaskFile(task_filename, ):
    ''' Обёртка над TaskFileParser для совместимости со старым интерфейсом. '''
    return TaskFileParser().parse(task_filename)


#****** Универсальный парсер INI-файла в Python-словарь
def ReadINItoDict(folder_name, config_filename):
    #Путь к конфигу в указанной папке
    config_path = os.path.join(folder_name, config_filename)
    
    config = configparser.ConfigParser()
    #Сохраняем оригинальный регистр букв (CamelCase) из INI-файла
    config.optionxform = str
    config.read(config_path, encoding='utf-8')
    #Считываем все секции и их параметры
    all_sections_dict = {name: dict(config[name]) for name in config.sections()}

    return all_sections_dict


def get_experiment_file_info(task_filename, save_path, mode_prefix=''):
    #Явно заданное имя файла считается финальным, иначе имя генерируется
    #в формате <режим>_<гггг>-<мм>-<дд>_<чч>-<мм>-<сс>
    if task_filename:
        base_name = task_filename.replace('.txt', '')
    else:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        base_name = f"{mode_prefix}_{timestamp}" if mode_prefix else timestamp
    
    if not os.path.exists(save_path + base_name + ".txt"):
        filename = base_name
    else:
        filename = next(f"{base_name}({n})" for n in count(1) if not os.path.exists(save_path + f"{base_name}({n}).txt"))
        
    return save_path + filename + ".txt"


def process_and_print_devices(req_devices, faststart_flag):
    #Если включен быстрый старт, переводим все приборы и каналы в режим FastStart
    if faststart_flag:
        for dev_info in req_devices.values():
            cfg = dev_info['Config']
            if isinstance(cfg, dict):
                for ch in cfg.keys():
                    if cfg[ch] is not None: cfg[ch] = "FastStart"
            else:
                dev_info['Config'] = "FastStart"

    print("\n==================================================")
    print(" СОСТАВ ИЗМЕРИТЕЛЬНОГО КОМПЛЕКСА:")
    for device_name, device_info in req_devices.items():
        cfg = device_info['Config']
        if isinstance(cfg, dict):
            ch_status = [f"Канал {ch}: {preset if preset else '<Не используется>'}" for ch, preset in cfg.items()]
            print(f" -> Прибор: {device_name} ({', '.join(ch_status)})")
        else:
            status = cfg if cfg else "<Не используется>"
            print(f" -> Прибор: {device_name}: {status}")
    print("==================================================\n")

# Принимает словарь колонок приборов, возвращает шапку файла результатов
# Формат колонки: <имя_прибора>[.ch<номер>]=<величина>, <единица>
def build_file_header(data_columns, prefix=''):
    header = prefix
    for device_name, columns in data_columns.items():
        for column in columns:
            if column['channel']:
                column_name = f"{device_name}.ch{column['channel']}"
            else:
                column_name = device_name
            header += f"\t{column_name}={column['value']}, {column['unit']}"
    return header + '\n'

