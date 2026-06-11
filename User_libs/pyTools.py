from datetime import datetime
import os, sys
import configparser

class Transformation():

    def __init__(self, ):
        
        self.Transforms = {'RES2T': self.Trasform_RES_to_Temp, }

    def Trasform_RES_to_Temp(self, y_data, R0=100, Rc=0, **kwargs):
        #преобразование сопротивления в температуру
        return [self._RTD_Pt_res_to_temp(y, R0=R0, Rc=Rc) for y in y_data]

    @staticmethod
    def _RTD_Pt_res_to_temp(R, /, R0=100, Rc=0):
        a = 3.9083 * 10 ** -3
        b = -5.775 * 10 ** -7
        c = -4.183 * 10 ** -12

        if R >= R0:
            # для положительных температур решаем квадратное уравнение R = Rc + R0 * (1 + a * t + b * t^2)
            d = a ** 2 - 4 * b * (R0 - R + Rc) / R0
            t = (d ** 0.5 - a) / (2 * b)
            return t
        else:
            # для отрицательных температур решение ищем методом Ньютона-Рафсона (хватает 2-3 итераций)
            # уравнение R = Rc + R0 * (1 + a * t + b * t^2 + c * (t - 100) * t^3)
            t = (R - Rc - R0) / (a * R0)
            while True:
                f_t = (c * t ** 4 - 100 * c * t ** 3 + b * t ** 2 + a * t + 1) * R0 + Rc - R
                df_dt = (4 * c * t ** 3 - 300 * c * t ** 2 + 2 * b * t + a) * R0
                t -= f_t / df_dt
                if abs(f_t / df_dt) < 0.0001:
                    return t

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


#****** Парсер текстового файла со списком экспериментов для сканирования щелью
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
            '''а вот как можно было одной строкой
            if (parts := line.split('#')[0].strip().split('\t')) == ['']: continue'''
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
            #6. Сохраняем словарь-эксперимент в общий пул
            ALL_TASKS.append({'axes': axes, 'intervals': intervals, 'filename': filename})
    return ALL_TASKS


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


#****** Парсер аргумента --devises
def ParseCommandLineDevices(raw_devices_list, devices_pool):
    #Словарь, где соберем имя прибора, модель, канал (если есть) и конфиг
    requested_devices = {}

    for item in raw_devices_list:
        #1. Разделяем имя прибора (с возможным каналом) и его конфиг по двоеточию
        if ':' in item:
            device_part, config_name = item.split(':', 1)
            config_name = config_name.strip()
        else:
            device_part, config_name = item, None
            
        #2. Проверяем, указан ли конкретный канал через точку (например, "TH1992B_1.2")
        if '.' in device_part:
            device_name, channel_num = device_part.split('.', 1)
        else:
            device_name, channel_num = device_part, None
            
        #Проверяем наличие базового имени прибора в переданном словаре devices_pool
        if device_name not in devices_pool:
            print(f"\n[ОШИБКА]: Прибор '{device_name}' не найден в Instrument.ini!")
            sys.exit(1)
            
        #Если прибор встречается впервые, инициализируем его структуру
        if device_name not in requested_devices:
            requested_devices[device_name] = {
                'LibraryName': devices_pool[device_name]['LibraryName'], #Марка прибора из INI
                'Config': {} if channel_num else None,
            }

        #ОБЩИЙ БЛОК ПРОВЕРКИ ОШИБОК ВВОДА
        is_already_dict = isinstance(requested_devices[device_name]['Config'], dict)
        
        #1. Проверяем смешивание одноканального и многоканального режимов
        if (channel_num is not None) != is_already_dict:
            print(f"\n[ОШИБКА]: Прибор '{device_name}' не может одновременно настраиваться как одноканальный и многоканальный!")
            sys.exit(1)
        #2. Проверяем повторный ввод канала для многоканального прибора
        elif is_already_dict and channel_num in requested_devices[device_name]['Config']:
            print(f"\n[ОШИБКА]: Канал {channel_num} для прибора '{device_name}' указан несколько раз!")
            sys.exit(1)
        #3. Проверяем повторный ввод для одноканального прибора
        elif not is_already_dict and requested_devices[device_name]['Config'] is not None:
            print(f"\n[ОШИБКА]: Прибор '{device_name}' указан в аргументах несколько раз!")
            sys.exit(1)

        #Запись имен конфигураций (если были заданы)
        if channel_num:
            requested_devices[device_name]['Config'][channel_num] = config_name
        else:
            requested_devices[device_name]['Config'] = config_name
                
    return requested_devices