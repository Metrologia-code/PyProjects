import pyvisa, configparser, time, datetime, os.path

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
        self.Name = 'Tonghui_TH2690A'
        
        #пауза - используется между последовательными write и query
        self.Pause = 0.05
        
        #длинная пауза - используется между включением измерения и последующей проверкой
        self.MassivePause = 2
        
        #эксклюзивно для измерителя Tonghui TH2690A
        #это формат строки, в котором возвращает данные команда FETCH:ALL?
        #для всех приборов: используется для составления словаря измеренных данных
        self.DataFormat = 'VOLTage,CURR,char,time,vsource,math,temp,hum'
        
        #DeviceCommands содержит {'ИмяКоманды':['КодКоманды','ОписаниеКоманды'], }
        #{val} - аргумент команды прибора. возможные значения указаны в комментариях ниже
        self.DeviceCommands = {
        'Func'             : ['FUNC:FUNC{val}'            ,  'Режим прибора'                           ],
        #RES|VOLT|CURR|SRC
        'Range'            : ['{mode}:RANGE{val}'         ,  'Диапазон измерения'                      ],
        #номер из таблицы?
        'Speed'            : ['{mode}:SPEED{val}'         ,  'Скорость измерения'                      ],
        #FAST|MID|SLOW
        'DisplayPage'      : ['DISP:PAGE{val}'            ,  'Страница дисплея'                        ],
        #MEAS
        'SourceSwitch'     : ['FUNC:SRC{val}'             ,  'Включение/выключение источника'          ],
        #ON|OFF
        'AmmeterSwitch'    : ['FUNC:AMMET{val}'           ,  'Включение/выключение амперметра'         ],
        #ON|OFF  
        'RunStop'          : ['FUNC:{val}'                ,  'Запуск/останов измерения'                ],
        #RUN|STOP
        }

    def _OpenResource(self, Resource, ):
        '''
        используется в _Open()
        '''
        #создаем объект pyvisa, подключаемся к прибору
        if not hasattr(self, 'rm'):
            self.rm = pyvisa.ResourceManager()
        try:
            self.tonghui = self.rm.open_resource(Resource, read_termination='\n')
            print(f'{self.tonghui.query("*IDN?")} - подключено к {Resource}')
        except Exception as e:
            print(f'{e}\nПодключиться к {Resource} не удалось')
            return False
        else:
            return True
    
    def _Open(self, DeviceAddress='', DevicePort='', DeviceSerial=''):
        '''
        используется в Initialize()
        '''
        #выбираем, как подключаться, и используем _OpenResource() для подключения
        if DeviceAddress and DevicePort:
            #подключаемся по TCPIP
            TCPIP = f'TCPIP0::{DeviceAddress}::{DevicePort}::SOCKET'
            #DeviceAddress = '192.168.88.12', DevicePort = '45454'
            return self._OpenResource(TCPIP)
        elif DeviceSerial:
            #список подключенных приборов:
            Resources = rm.list_resources()
            USB = next((item for item in Resources if DeviceSerial in item), None)
            #DeviceSerial = 'W152230156', USB0::0x1105::0x1992::W152230156::INSTR
            return self._OpenResource(USB)
        else:
            print('Параметры подключения не заданы')
            return False

    def Initialize(self, **ConnectionDetails, ):
        '''
        универсальный метод для внешнего вызова
        во всех остальных библиотеках должен вызываться точно так же
        тогда программы смогут работать с любым прибором
        '''
        return self._Open(**ConnectionDetails)

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
        '''
        метод для внешнего и внутреннего вызова
        использует словарь DeviceCommands = {'ИмяКоманды':['КодКоманды','ОписаниеКоманды'], }
        также используется в SetParameter()
        '''
        #
        command, explanation  = self.DeviceCommands[CommandName]
        try:
            #TH2690A почему-то не возвращает конец строки в ряде запросов
            #return self.tonghui.query(command.format(val='?', **Parameters))
            return self._CustomQuery(self.tonghui, command.format(val='?', **Parameters))
        except Exception as e:
            print(f'{explanation} <{CommandName}> : не удалось считать\n{e}')
            return False

    def SetParameter(self, CommandName, CommandArgument, Pause=None, **Parameters):
        '''
        метод для внешнего и внутреннего вызова
        использует словарь DeviceCommands = {'ИмяКоманды':['КодКоманды','ОписаниеКоманды'], }
        пример команды прибора: {mode}:SPEED{val}
        после установки параметра проверяет, удалось ли установить
        '''
        #
        command, explanation  = self.DeviceCommands[CommandName]
        #если аргумент не задан - используем self.Pause
        Pause = Pause or self.Pause
        #устанавливаем значение
        self.tonghui.write(command.format(val=f' {CommandArgument}', **Parameters))
        time.sleep(Pause)
        check = self.GetParameter(CommandName, **Parameters)
        if check and check != CommandArgument:
            print(f'{explanation} <{CommandName}> не удалось изменить на: {CommandArgument}')
            print(f'(Считанное значение: {check})')
        return check == CommandArgument

    def _ProcessDeviceSettings(self, ConfigName, FilePath, FileName, ):
        '''
        внутренний метод, используется в ConfigureDevice()
        парсим полученные извне аргументы и считываем конфигурационный файл
        для Tonghui TH2690A аргумент ConfigName задает имя пресета настроек в ini файле
        '''
        #формируем список имен измеряемых величин
        self.DataNames = self.DataFormat.split(',')
        #считываем файл с пресетами
        self.AllConfigs = configparser.ConfigParser()
        self.AllConfigs.optionxform = str
        #дефолтный или заданный путь к конфигурационному файлу
        FilePath = FilePath or os.path.dirname(os.path.abspath(__file__)) + '\\Config\\'
        if not self.AllConfigs.read(FilePath + FileName):
            print(f'Не удалось считать файл: {FilePath + FileName}')
            return False
        return True
        
    def ConfigureDevice(self, ConfigName='DEFAULT', 
                        FilePath=None, FileName = 'Tonghui_TH2690A_config.ini', ):
        '''
        универсальный метод для внешнего вызова
        во всех остальных библиотеках должен вызываться точно так же
        тогда программы смогут работать с любым прибором
        '''
        #подготавливаем настройки
        if self._ProcessDeviceSettings(ConfigName, FilePath, FileName, ) == False:
            return False
        #получаем словарь настроек для выбранного пресета
        ConfigDict = self.AllConfigs[ConfigName]
        #режим работы прибора
        mode = ConfigDict['Func']
        #словарь компонентов команд для SetParameter() и GetParameter()
        Parameters = {'mode': mode, }
        #итерируем параметры настроек и устанавливаем их
        for CommandName, CommandArgument in ConfigDict.items():
            if self.SetParameter(CommandName, CommandArgument, **Parameters) == False:
                return False
                
        #в случае успешной настройки 'включаем канал'
        if self.SetParameter('DisplayPage', 'MEAS') == False:
            return False
        if self.SetParameter('SourceSwitch', 'OFF') == False:
            return False  
        if self.SetParameter('AmmeterSwitch', 'ON') == False:
            return False
        
        #запускаем измерение
        '''time.sleep(self.MassivePause)
        if self.SetParameter('RunStop', 'RUN', Pause=self.MassivePause) == False:
            return False'''
        #Run/Stop measurement 'FUNC:RUN|STOP'
        time.sleep(2)
        self.tonghui.write('FUNC:RUN')
        #если не подождать, то измерение стартанет, но кнопка не загорится
        time.sleep(2)

        return True

    def SingleMeasure(self, ):
        '''
        универсальный метод для внешнего вызова
        возвращает измереные данные в виде {'DataName':Value, } или False
        '''
        try:
            #отправка запроса всех данных
            MeasuredData = self.tonghui.query('FETCH:ALL?')
        except Exception as e:
            print(datetime.now().strftime("%Y-%m-%d %H-%M-%S"), e, )
            return False
        else:
            #print(MeasuredData)
            #ListData = list(map(float, MeasuredData.split(',')))
            ListData = MeasuredData.split(',')
            
        #формируем словарь измеренных данных
        DictData = dict(zip(self.DataNames, ListData))
        #return DictData
        volt = float(DictData['VOLTage'])
        curr = volt = float(DictData['CURR'])
        return [volt, curr]

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