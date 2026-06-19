import sys
import os
import time
import importlib
import configparser

#пользовательские библиотеки
from User_libs import ReadINItoDict, ParseCommandLineDevices, process_and_print_devices

class DEVICES:
    def __init__(self, args):
        #1. Считываем все доступные приборы из Devices.ini в пул
        self.devices_pool = ReadINItoDict('Complex_libs', 'Devices.ini')
        
        #2. Передаем список из консоли и считанный пул приборов в функцию разбора
        self.req_devices = ParseCommandLineDevices(args.devices, self.devices_pool)
        
        #3. Обрабатываем режимы работы и выводим состав комплекса на экран
        process_and_print_devices(self.req_devices, args.faststart)
        
        #4. Инициализируем и настраиваем приборы из запрошенного списка
        self.Device = {}
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
            self.Device[device_name] = device
            
        #5. Делаем пробный опрос приборов для фиксации ключей возвращаемых данных
        self.device_data_keys = {}
        for device_name, device_obj in self.Device.items():
            probe_measure = False
            for attempt in range(3):
                probe_measure = device_obj.SingleMeasure()
                if probe_measure:
                    break
                time.sleep(0.5)
                
            if not probe_measure:
                print(f"[ERROR] Не удалось выполнить пробное измерение для прибора {device_name}!")
                sys.exit(1)
                
            self.device_data_keys[device_name] = list(probe_measure.keys())
