import pyvisa, configparser, time, datetime, os.path, random

class Device():
    ''' класс для работы с прибором
        использует конфигурационные ini файлы для настройки прибора
        ключевые методы для внешнего вызова:
            Initialize(ConnectionMethod=, **ConnectionDetails, ) - для подключения
            ConfigureDevice(ConfigName=, FilePath=, FileName=, ) - для настройки
            SingleMeasure() - для измерения
            Close() - для отключения
    '''

    def __init__(self, ):
        
        #название прибора, для внешнего использования
        self.Name = 'Tonghui TH1992B'
        
        #пауза - используется между последовательными write и query
        self.Pause = 0.05
        
        #длинная пауза - используется между включением канала и последующей проверкой
        self.LongPause = 2
        
        #эксклюзивно для источника-измерителя Tonghui TH1992B
        #в таком формате будут возвращать данные команды FETCh? и MEASure?
        #порядок аргументов фиксированный (еще есть TIME, но не используем)
        #мы будем всегда забирать данные в одном и том же формате
        #для всех приборов: используется для составления словаря измеренных данных
        self.DataFormat = 'VOLTage,CURR,RES'
        
        #DeviceCommands содержит {'ИмяКоманды' : ['КодКоманды', 'Пауза'], }
        #компоненты команд {ch}, {mode}, {sens} - эксклюзивно для источника-измерителя Tonghui TH1992B
        #{ch} - номер канала (1 либо 2)
        #{mode} - режим источника (VOLT либо CURR)
        #{sens} - режим измерителя (VOLT либо CURR)
        #{val} - аргумент команды прибора. возможные значения указаны в комментариях
        #каждую команду можно также использовать для запроса с val='?'
        self.DeviceCommands = {
            #Режим работы источника
            #VOLT, CURR. один всегда mode (SOURce), второй - sens (SENSe)
            'Mode'            : [':SOUR{ch}:FUNC:MODE{val}'        , self.Pause     ],
            #Режим сигнала источника
            #FIX, SWE, LIST
            'AWG'             : [':SOUR{ch}:{mode}:MODE{val}'      , self.Pause     ],
            #Диапазон сигнала источника напр./тока
            #для VOLT - 0.2, 2, 20, 200
            #для CURR - 0.00000001, 0.0000001... 1, 1.5, 3
            'SOURCE-range'    : [':SOUR{ch}:{mode}:RANG{val}'      , self.Pause     ],
            #Режим автоматического переключения диапазонов измерения
            #ON, OFF
            'SENSE-range auto': [':SENS{ch}:{sens}:RANG:AUTO{val}' , self.Pause     ],
            #Диапазон измерения
            #для VOLT - 0.2, 2, 20, 200
            #для CURR - 0.00000001, 0.0000001... 1, 1.5, 3
            'SENSE-range'     : [':SENS{ch}:{sens}:RANG{val}'      , self.Pause     ],
            #Лимит измерения напр./тока
            #
            'SENSE Limit'     : [':SENS{ch}:{sens}:PROT:LEV{val}'  , self.Pause     ],
            #Значение сигнала напр./тока источника
            #
            'SOURCE-value'    : [':SOUR{ch}:{mode}{val}'           , self.Pause     ],
            #Способ отключения канала
            #ZERO, HIZ, NORM
            'Off state'       : [':OUTP{ch}:OFF:MODE{val}'         , self.Pause     ],
            #Значение апертуры измерения
            #
            'Aperture'        : [':SENS{ch}:{sens}:APER{val}'      , self.Pause     ],
            #State of low end
            #GRO, FLO
            'Low T'           : [':OUTP{ch}:LOW{val}'              , self.Pause     ],
            #Overvoltage/overcurrent protection
            #1, 0
            'OVP/OCP'         : [':OUTP{ch}:PROT{val}'             , self.Pause     ],
            #Вкл/выкл фильтра вывода
            #1, 0
            'Filter'          : [':OUTP{ch}:FILT{val}'             , self.Pause     ],
            #Time constant of output filter
            #5e-06
            'LPF-t'           : [':OUTP{ch}:FILT:TCON{val}'        , self.Pause     ],
            #High capacitance mode
            #1, 0
            'High C'          : [':OUTP{ch}:HCAP:STAT{val}'        , self.Pause     ],
            #Remote function (4-wire)
            #1, 0
            #если 1 - то используется схема подключения 4-wire, если 0 - то 2-wire
            'Sensing'         : [':SENS{ch}:REM{val}'              , self.Pause     ],
            #Формат  возвращаемых данных
            #VOLTage,CURR,RES,TIME (строгий порядок)
            'FORMAT'          : [':FORM:ELEM:SENS{val}'            , self.Pause     ],
            #Статус канала
            #1, 0
            'ChannelState'    : ['OUTP{ch}:STAT{val}'              , self.LongPause ],
        }

    def _OpenResource(self, Resource, ):
        ''' используется в _Open()
            возвращает True или False '''
        #подключаемся к прибору
        try:
            self.tonghui = self.rm.open_resource(Resource, read_termination='\n')
            print(f'{self.tonghui.query("*IDN?")} - подключено к {Resource}')
        except Exception as e:
            print(f'{e}\nПодключиться к {Resource} не удалось')
            return False
        else:
            #проверяем очередь команд прибора
            #эксклюзивно для источника-измерителя Tonghui TH1992B
            #как красиво исправить - не понятно
            #отправить read(), в т.ч. побайтовый, не помогает
            #помогает отправить MEAS? (при включенном канале)
            #т.е. после начала измерений оно исправляется само
            #пока не знаю, что с этим делать. мб ничего, и вообще убрать
            if self.tonghui.query('*OPC?') == '0':
                print('Очередь команд занята')
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
    
    def Initialize1(self, ConnectionMethod='TCPIP', **ConnectionDetails, ):
        #для тестов
        return True

    def GetParameter(self, CommandName, **Parameters):
        ''' метод для внешнего и внутреннего вызова
            также используется в SetParameter()
            возвращает считанную строку или False '''
        #
        command, _ = self.DeviceCommands[CommandName]
        try:
            return self.tonghui.query(command.format(val='?', **Parameters))
        except Exception as e:
            print(f'<{CommandName}> : не удалось считать\n{e}')
            return False

    def SetParameter(self, CommandName, CommandArgument, **Parameters):
        ''' метод для внешнего и внутреннего вызова
            использует словарь DeviceCommands = {'ИмяКоманды' : ['КодКоманды', 'Пауза'], }
            пример команды прибора: :SENS{ch}:{sens}:RANG{val}
            после установки параметра проверяет, удалось ли установить
            возвращает True или False '''
        #
        command, pause  = self.DeviceCommands[CommandName]
        #устанавливаем значение параметра
        self.tonghui.write(command.format(val=f' {CommandArgument}', **Parameters))
        time.sleep(pause)
        check = self.GetParameter(CommandName, **Parameters)
        if check and check != CommandArgument:
            print(f'<{CommandName}> не удалось изменить на: {CommandArgument}')
            print(f'(Считанное значение: {check})')
        return check == CommandArgument

    def _ProcessDeviceSettings(self, ConfigName, FilePath, FileName, ):
        ''' внутренний метод, используется в ConfigureDevice()
            парсим полученные извне аргументы и считываем конфигурационный файл
            для Tonghui TH1992B аргумент ConfigName также задает, с какими каналами будем работать
            поэтому метод SingleMeasure() не будет работать, если вызвать его до _ProcessDeviceSettings()
            вообще это не есть хорошо, но пока так
            возвращает True или False '''
        #список используемых каналов
        #эксклюзивно для источника-измерителя Tonghui TH1992B
        self.ChannelsList = list(ConfigName)
        #формируем список имен измеряемых величин в соответствии с каналами измерения
        self.DataNames = [f'{name}{ch}' for ch in self.ChannelsList for name in self.DataFormat.split(',')]
        #формируем строку из списка каналов для аргумента команлы MEASure?
        self.ChannelsString = ','.join(self.ChannelsList)
        #считываем файл с пресетами
        self.AllConfigs = configparser.ConfigParser()
        self.AllConfigs.optionxform = str
        #дефолтный или заданный путь к конфигурационному файлу
        FilePath = FilePath or os.path.dirname(os.path.abspath(__file__)) + '\\config\\'
        if not self.AllConfigs.read(FilePath + FileName):
            print(f'Не удалось считать файл: {FilePath + FileName}')
            return False
        return True
        
    def ConfigureDevice(self, ConfigName={'1':'DEFAULT', '2':'DEFAULT', }, 
                        FilePath=None, FileName = 'Tonghui_TH1992B_config.ini', ):
        ''' универсальный метод для внешнего вызова
            во всех остальных библиотеках должен вызываться точно так же
            тогда программы смогут работать с любым прибором
            тип данных PresetName является словарем только для Tonghui TH1992B
            возвращает True или False '''
        #эксклюзивно для источника-измерителя Tonghui TH1992B
        if not self.SetParameter('FORMAT', self.DataFormat, ):
            return False
        #подготавливаем настройки
        if not self._ProcessDeviceSettings(ConfigName, FilePath, FileName, ):
            return False
        #настраиваем канал(ы)
        for ch in self.ChannelsList:
            #получаем словарь настроек, предназначенных для канала
            ConfigDict = self.AllConfigs[ConfigName[ch]]
            #режимы работы прибора
            mode = ConfigDict['Mode']
            sens = 'CURR' if mode == 'VOLT' else 'VOLT'
            #словарь компонентов команд для SetParameter() и GetParameter()
            Parameters = {'ch':ch, 'mode':mode, 'sens':sens}
            #итерируем параметры настроек и устанавливаем их
            for CommandName, CommandArgument in ConfigDict.items():
                if not self.SetParameter(CommandName, CommandArgument, **Parameters):
                    return False
            #в случае успешной настройки включаем канал(ы)
            if not self.SetParameter('ChannelState', '1', ch=ch):
                return False
        return True

    def _ReEnableChannels(self, ):
        ''' внутренний метод, используется в SingleMeasure() только для Tonghui TH1992B
            проверяет, отключены ли каналы, и пробует включить
            всегда возвращает False, потому что измерение уже провалено '''
        for ch in self.ChannelsList:
            if self.GetParameter('ChannelState', ch=ch) == '0':
                ErrorTime = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
                print(ErrorTime, f'Измерить не удалось, канал {ch} отключен!')
                #пробуем включить канал
                if self.SetParameter('ChannelState', '1', ch=ch):
                    print(f'Канал {ch} удалось включить')
        return False
    
    def SingleMeasure1(self, ):
        ''' универсальный метод для внешнего вызова
            возвращает измереные данные в виде {'DataName':Value, } или False '''
        #возможны два варианта провала: прибор вернул 'Invalid' или тайм-аут
        try:
            #отправка запроса
            MeasuredData = self.tonghui.query(f':MEAS? (@{self.ChannelsString})')
        except Exception as e:
            print(datetime.now().strftime("%Y-%m-%d %H-%M-%S"), e, )
            #переподключение будем вызывать извне
            return False
        else:
            #'Invalid' возвращается при попытке измерить выключенный канал
            if MeasuredData == 'Invalid':
                #пробуем включить канал(ы), если отключен(ы)
                return self._ReEnableChannels()
            ListData = list(map(float, MeasuredData.split(',')))
        #формируем словарь измеренных данных
        DictData = dict(zip(self.DataNames, ListData))
        return DictData

    def SingleMeasure(self, ):
        #для тестов
        return {
            'VOLTage1': round(random.uniform(0.5, 5.0), 4),
            'CURR1': round(random.uniform(0.001, 0.1), 6),
            'RES1': round(random.uniform(500, 1000), 2),
            'VOLTage2': round(random.uniform(0.5, 5.0), 4),
            'CURR2': round(random.uniform(0.001, 0.1), 6),
            'RES2': round(random.uniform(50, 1000), 2)/3,
        }

    def GetIDN(self, ):
        #метод для внешнего вызова
        return self.tonghui.query("*IDN?")
    
    def GetIDN1(self, ):
        #для тестов
        return "TH1992B"
    
    def Close(self, ):
        #метод для внешнего вызова
        print(f'{self.tonghui.query("*IDN?")} - отключение')
        self.tonghui.close()