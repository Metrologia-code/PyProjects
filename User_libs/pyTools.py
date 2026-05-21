from datetime import datetime
import os

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
    ''' file - путь к файлу, который вызвал функцию 
        LAN_Path - путь к файловому хранилищу
        формирует путь к папке для сохранения данных
        и создает в ней подпапку с текущей датой
        возвращает путь в виде строки '''
    '''try:
        ProgramPath = os.path.dirname(os.path.abspath(file))
    except NameError:
        ProgramPath = os.getcwd()'''
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

        