from datetime import datetime
import os

class Transformation():

    def __init__(self, ):
        
        self.Transforms = {'RES2T': self.Trasform_RES_to_Temp, }

    def Trasform_RES_to_Temp(self, y_data, Rc=0, **kwargs):
        #преобразование сопротивления в температуру
        return [((y-Rc)/100-1)/0.00385 for y in y_data]

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

def CreateSavePath(file, LAN_Path=None, ):
    ''' file - путь к файлу, который вызвал функцию 
        LAN_Path - путь к файловому хранилищу
        формирует путь к папке для сохранения данных
        и создает в ней подпапку с текущей датой
        возвращает путь в виде строки '''
    LoggerPath = os.path.dirname(os.path.abspath(file))
    TodayNameDir = '\\' + datetime.now().strftime("%Y_%m_%d") + '\\'
    #сохраняем в хранилище MetroBulk, если оно доступно
    if os.path.exists(LAN_Path):
        SavePath = LAN_Path + TodayNameDir
    #если подключение к MetroBulk отсутствует - сохраняем в местную папку Data
    else:
        DataPath = LoggerPath + '\\Data'
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

        