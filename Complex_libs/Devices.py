import sys
import time
import importlib

#пользовательские библиотеки
from User_libs import process_and_print_devices
from .DeviceSpecParser import DeviceSpecParser

class Devices:
    def __init__(self, args):
        #1-2. Считываем Devices.ini и разбираем аргумент -d новым парсером
        self.spec = DeviceSpecParser('Complex_libs', 'Devices.ini')
        self.devices_pool = self.spec.pool
        self.req_devices = self.spec.parse(args.devices)

        #2a. Список графиков (@имя_полотна) становится аргументом args.graph
        args.graph = self.spec.build_graphs(self.req_devices)

        #3. Обрабатываем режимы работы и выводим состав комплекса на экран
        process_and_print_devices(self.req_devices, args.faststart)

        #4. Инициализируем и настраиваем приборы из запрошенного списка
        self.devices = {}
        for device_name, device_info in self.req_devices.items():
            library_folder = self.devices_pool[device_name]['LibraryFolder']
            library_name = device_info['LibraryName']
            
            #Динамически импортируем модуль бренда (эквивалентно: import Folder.Module)
            device_module = importlib.import_module(f"{library_folder}.{library_name}")
            device = device_module.Device()
            
            #Берем параметры подключения из пула INI
            connection_details = self.devices_pool[device_name].copy()
            
            if not device.Initialize(**connection_details):
                sys.exit(1)
                
            #Вызываем конфигурацию, передавая только имя пресета (или словарь каналов)
            device_config = device_info['Config']
            if not device.ConfigureDevice(ConfigName=device_config):
                sys.exit(1)
                
            #Сохраняем настроенный прибор в словарь активных устройств класса
            self.devices[device_name] = device
            
        #5. Делаем пробный опрос приборов для фиксации ключей возвращаемых данных
        #   и оставляем только те величины, которые были запрошены в аргументе -d
        self.device_data_keys = {}
        self.device_columns = {}
        for device_name, device_obj in self.devices.items():
            probe_measure = False
            for attempt in range(3):
                probe_measure = device_obj.SingleMeasure()
                if probe_measure:
                    break
                time.sleep(0.5)
                
            if not probe_measure:
                print(f"[ERROR] Не удалось выполнить пробное измерение для прибора {device_name}!")
                sys.exit(1)

            probe_keys = list(probe_measure.keys())
            columns = []
            for column in self.req_devices[device_name]['Columns']:
                if column['key'] in probe_keys:
                    columns.append(column)
                else:
                    print(f"[WARNING] Прибор {device_name}: величина '{column['value']}' "
                          f"не возвращается прибором и будет пропущена")

            self.device_columns[device_name] = columns
            self.device_data_keys[device_name] = [column['key'] for column in columns]

    def reconnect(self, device_name):
        ''' Повторное подключение и настройка прибора после потери связи.
            Ничего не знает о внутренностях драйвера: просто заново вызывает
            Initialize/ConfigureDevice/пробный опрос. Возвращает True или False. '''
        device = self.devices[device_name]
        try:
            if not device.Initialize(**self.devices_pool[device_name].copy()):
                return False
            if not device.ConfigureDevice(ConfigName=self.req_devices[device_name]['Config']):
                return False
            for attempt in range(3):
                if isinstance(device.SingleMeasure(), dict):
                    return True
                time.sleep(0.5)
            return False
        except Exception:
            return False
