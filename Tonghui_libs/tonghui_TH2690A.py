import pyvisa, configparser, time, os.path
from datetime import datetime

class Device():
    '''
    класс для работы с прибором
    использует конфигурационные ini файлы для настройки прибора
    ключевые методы для внешнего вызова:
        Initialize(**ConnectionDetails, ) - для подключения
        ConfigureDevice(ConfigName=, FilePath=, FileName=, ) - для настройки
        SingleMeasure() - для измерения
        Close() - для отключения
    '''

    def __init__(self, ):
        
        #название прибора, для внешнего использования
        self.Name = 'Tonghui TH2690A'
        
        #пауза - используется между последовательными write и query
        self.Pause = 0.05
        
        #длинная пауза - используется между включением канала и последующей проверкой
        self.LongPause = 2
        
        #эксклюзивно для измерителя Tonghui TH2690A
        #это формат строки, в котором возвращает данные команда FETCH:ALL?
        #для всех приборов: используется для составления словаря измеренных данных
        self.DataFormat = 'VOLTage,CURR,char,time,vsource,math,temp,hum'
        
        #DeviceCommands содержит {'ИмяКоманды' : ['КодКоманды', 'Пауза'], }
        #{val} - аргумент команды прибора. возможные значения указаны в комментариях
        self.DeviceCommands = {
            #Режим прибора
            #RES|VOLT|CURR|SRC
            'Func'            : ['FUNC:FUNC{val}'      ,  self.Pause   ],
            #Диапазон измерения
            #номер из таблицы
            'Range'           : ['{mode}:RANGE{val}'   ,  self.Pause   ],
            #Скорость измерения
            #FAST|MID|SLOW
            'Speed'           : ['{mode}:SPEED{val}'   ,  self.Pause   ],
            #Страница дисплея, необходимо быть на ней для измерения
            #MEAS
            'DisplayPage'     : ['DISP:PAGE{val}'      ,  self.Pause   ],
            #Включение/выключение источника
            #ON|OFF
            'SourceSwitch'    : ['FUNC:SRC{val}'       ,  self.Pause   ],
            #Включение/выключение амперметра
            #ON|OFF
            'AmmeterSwitch'   : ['FUNC:AMMET{val}'     ,  self.Pause   ],
            #Запуск/остановка измерения
            #RUN|STOP
            'RunStop'         : ['FUNC:{val}'          ,  self.Pause   ],
        }

    def _OpenResource(self, Resource, ):
        ''' используется в _Open()
            возвращает True или False '''
        #подключаемся к прибору
        try:
            self.tonghui = self.rm.open_resource(Resource, read_termination='\n')
            print(f'{self.tonghui.query("*IDN?")} - подключено к {Resource}')
        except Exception as e:
            #print(f'{e}\nПодключиться к {Resource} не удалось')
            print(f'Подключиться к {Resource} не удалось')
            return False
        else:
            return True
    
    def _OpenTCPIP(self, DeviceAddress=None, DevicePort=None, **kwargs):
        ''' используется в Initialize()
            возвращает True или False '''
        if not DeviceAddress or not DevicePort:
            print('Параметры подключения по TCPIP (DeviceAddress и/или DevicePort) не заданы')
            return False
        TCPIP = f'TCPIP0::{DeviceAddress}::{DevicePort}::SOCKET'
        return self._OpenResource(TCPIP)

    def _OpenUSBTCM(self, DeviceSerial=None, **kwargs):
        ''' используется в Initialize()
            возвращает True или False '''
        if not DeviceSerial:
            print('Серийный номер прибора (DeviceSerial) для подключения по USBTCM не задан')
            return False
        #получаем список всех подключенных приборов
        Resources = self.rm.list_resources()
        #пример элемента из Resources - USB0::0x1105::0x1992::W152230156::INSTR
        USBTCM = next((item for item in Resources if DeviceSerial in item), None)
        return self._OpenResource(USBTCM)

    def Initialize(self, ConnectionMethod='TCPIP', **ConnectionDetails, ):
        ''' универсальный метод для внешнего вызова
            возвращает True или False '''
        #создаем объект ResourceManager, если его еще нет
        if not hasattr(self, 'rm'):
            self.rm = pyvisa.ResourceManager()
        Open = {'TCPIP':self._OpenTCPIP, 'USBTCM':self._OpenUSBTCM, }
        return Open[ConnectionMethod](**ConnectionDetails)

    def _ReadBytes(self, device, ):
        data, byte = '', ''
        while True:
            try:
                byte = device.read_bytes(1)
                data += byte.decode()
            except:
                break
        if data[-1] == '\n':
            data = data[:-1]
        return data

    def _CustomQuery(self, device, command, ):
        device.write(command)
        return self._ReadBytes(device)

    def GetParameter(self, CommandName, **Parameters):
        ''' метод для внешнего и внутреннего вызова
            также используется в SetParameter()
            возвращает считанную строку или пустую '''
        #
        command, _ = self.DeviceCommands[CommandName]
        try:
            #TH2690A почему-то не возвращает конец строки в ряде запросов
            #return self.tonghui.query(command.format(val='?', **Parameters))
            return self._CustomQuery(self.tonghui, command.format(val='?', **Parameters))
        except Exception as e:
            print(f'<{CommandName}> : не удалось считать\n{e}')
            return ''

    def _NotationConverter(self, argument, ):
        ''' конвертирует строку в число, если это возможно 
            возвращает либо аргумент без изменений, либо int, либо float '''
        for converter in (int, float):
            try:
                return converter(argument)
            except:
                continue
        return argument
    
    def _NotationFormatter(self, value, ):
        ''' на случай, если придется писать числа прибору только в децимальной нотации '''
        if isinstance(value, float):
            return format(value, '.15f').rstrip('0').rstrip('.')
        return value
    
    def SetParameter(self, CommandName, CommandArgument, **Parameters):
        ''' метод для внешнего и внутреннего вызова
            использует словарь DeviceCommands = {'ИмяКоманды' : ['КодКоманды', 'Пауза'], }
            пример команды прибора: {mode}:SPEED{val}
            после установки параметра проверяет, удалось ли установить
            возвращает True или False '''
        #распаковка команды прибора
        command, pause  = self.DeviceCommands[CommandName]
        #конвертируем строку аргумента в число, если это число
        CommandArgument = self._NotationConverter(CommandArgument)
        #устанавливаем значение параметра
        self.tonghui.write(command.format(val=f' {CommandArgument}', **Parameters))
        print(command.format(val=f' {CommandArgument}', **Parameters))
        time.sleep(pause)
        #конвертируем ответ прибора в число, если это число
        check = self._NotationConverter( self.GetParameter(CommandName, **Parameters) )
        #сравниваем либо строку со строкой, либо число с числом
        if check and check != CommandArgument:
            print(f'<{CommandName}> не удалось изменить на: {CommandArgument}')
            print(f'(Считанное значение: {check})')
        return check == CommandArgument

    def _ProcessDeviceSettings(self, ConfigName, FilePath, FileName, ):
        ''' внутренний метод, используется в ConfigureDevice()
            парсим полученные извне аргументы и считываем конфигурационный файл
            для Tonghui TH2690A аргумент ConfigName задает имя пресета настроек в ini файле
            возвращает True или False '''
        #формируем список имен измеряемых величин
        self.DataNames = self.DataFormat.split(',')
        #считываем файл с пресетами
        self.AllConfigs = configparser.ConfigParser()
        self.AllConfigs.optionxform = str
        #дефолтный или заданный путь к конфигурационному файлу
        FilePath = FilePath or os.path.dirname(os.path.abspath(__file__)) + '\\config\\'
        if not self.AllConfigs.read(FilePath + FileName):
            print(f'Не удалось считать файл: {FilePath + FileName}')
            return False
        return True
        
    def ConfigureDevice(self, ConfigName='DEFAULT', 
                        FilePath=None, FileName = 'Tonghui_TH2690A_config.ini', ):
        ''' универсальный метод для внешнего вызова
            во всех остальных библиотеках должен вызываться точно так же
            тогда программы смогут работать с любым прибором
            возвращает True или False '''
        #подготавливаем настройки
        if not self._ProcessDeviceSettings(ConfigName, FilePath, FileName, ):
            return False
        #получаем словарь настроек для выбранного пресета
        ConfigDict = self.AllConfigs[ConfigName]
        #режим работы прибора
        mode = ConfigDict['Func']
        #словарь компонентов команд для SetParameter() и GetParameter()
        Parameters = {'mode': mode, }
        #итерируем параметры настроек и устанавливаем их
        for CommandName, CommandArgument in ConfigDict.items():
            if not self.SetParameter(CommandName, CommandArgument, **Parameters):
                return False
        #в случае успешной настройки 'включаем канал'
        '''if not self.SetParameter('DisplayPage', 'MEAS'):
            return False
        if not self.SetParameter('SourceSwitch', 'OFF'):
            return False  
        if not self.SetParameter('AmmeterSwitch', 'ON'):
            return False'''
        #запускаем измерение
        '''time.sleep(self.MassivePause)
        if not self.SetParameter('RunStop', 'RUN', ):
            return False'''
        time.sleep(2)
        #Run/Stop measurement 'FUNC:RUN|STOP'
        self.tonghui.write('FUNC:RUN')
        #если не подождать, то измерение стартанет, но кнопка не загорится
        time.sleep(2)
        return True

    def SingleMeasure(self, ):
        ''' универсальный метод для внешнего вызова
            возвращает измереные данные в виде {'DataName':Value, } или False '''
        try:
            #отправка запроса всех данных
            MeasuredData = self.tonghui.query('FETCH:ALL?')
        except Exception as e:
            print(datetime.now().strftime("%Y-%m-%d %H-%M-%S"), e, )
            #переподключение будем вызывать извне
            return False
        else:
            #print(MeasuredData)
            #ListData = list(map(float, MeasuredData.split(',')))
            ListData = MeasuredData.split(',')
            
        #формируем словарь измеренных данных
        DictData = dict(zip(self.DataNames, ListData))
        #return DictData
        ReturnKeys = ['VOLTage', 'CURR', ]
        ReturnDict = {k: float(DictData[k]) for k in ReturnKeys if k in DictData}
        return ReturnDict

    def GetIDN(self, ):
        #метод для внешнего вызова
        return self.tonghui.query("*IDN?")
    
    def Close(self, ):
        #метод для внешнего вызова
        #останавливаем измерение и выключаем функции
        #self.SetParameter('RunStop', 'STOP', Pause=self.MassivePause)
        #self.SetParameter('AmmeterSwitch', 'OFF')
        #self.SetParameter('SourceSwitch', 'OFF')
        print(f'{self.tonghui.query("*IDN?")} - отключение')
        self.tonghui.close()