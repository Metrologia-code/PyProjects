import os
import sys
import configparser


class DeviceSpecParser:
    ''' Разбор описания устройств (Devices.ini нового формата)
        и аргумента -d нового синтаксиса.

        Синтаксис -d:
            <имя>[.ch<номер>][~<пресет>]=<величины>[;ch<номер>[~<пресет>]=<величины>...]
        Каждая величина:
            <измеряемая_величина>[@<имя_полотна>]

        Класс читает Devices.ini, разбирает командную строку и возвращает
        структуры, совместимые с текущей логикой проекта:
            pool        - пул устройств (в т.ч. legacy-ключи для инициализации драйверов);
            req_devices - {имя: {'LibraryName', 'Config', 'Columns'}};
            build_graphs() - структурированный список кривых для графиков.
    '''

    def __init__(self, folder_name, config_filename):
        self.pool = {}
        self._read_ini(folder_name, config_filename)

    #---ЧТЕНИЕ И НОРМАЛИЗАЦИЯ Devices.ini---
    def _read_ini(self, folder_name, config_filename):
        config_path = os.path.join(folder_name, config_filename)
        config = configparser.ConfigParser()
        #Сохраняем регистр ключей как в файле
        config.optionxform = str
        if not config.read(config_path, encoding='utf-8'):
            self._error(f"Не удалось считать файл описания устройств: {config_path}")
        for section in config.sections():
            self.pool[section] = self._normalize_section(dict(config[section]))

    @staticmethod
    def _split_list(value):
        return [item.strip() for item in value.split(',') if item.strip()]

    def _normalize_section(self, raw):
        def get(key, default=''):
            return raw.get(key, default).strip()

        interface = get('interface', 'tcpip').lower()
        address = get('address', '')
        #Для tcpip адрес задается в виде ip:port, для остальных интерфейсов - как есть
        device_address, device_port = address, ''
        if interface == 'tcpip' and ':' in address:
            device_address, device_port = address.rsplit(':', 1)

        return {
            #Новые поля
            'Type': get('type', 'instrument').lower(),
            'Model': get('model'),
            'Interface': interface,
            'Address': address,
            'Channels': self._split_list(get('channels', '')),
            'Values': self._split_list(get('values', '')),
            'Units': self._split_list(get('units', '')),
            'Axes': self._split_list(get('axes', '')),
            'AxesNames': self._split_list(get('axesnames', '')),
            #Legacy-совместимые ключи (используются Devices.py и драйверами)
            'LibraryFolder': get('folder', ''),
            'LibraryName': get('model'),
            'ConnectionMethod': interface.upper(),
            'DeviceAddress': device_address,
            'DevicePort': device_port,
        }

    #---РАЗБОР АРГУМЕНТА -d---
    def parse(self, raw_devices_list):
        requested_devices = {}

        for token in raw_devices_list:
            token = token.strip()
            if not token:
                continue

            segments = token.split(';')
            #Первый сегмент содержит имя устройства, канал и, возможно, пресет
            first_target, first_values = self._split_segment(segments[0], token)
            device_name, channel, preset = self._parse_device_target(first_target)
            dev_info = self.pool[device_name]

            if device_name in requested_devices:
                self._error(f"Устройство '{device_name}' указано несколько раз")

            if dev_info['Channels']:
                if channel is None:
                    self._error(f"Для устройства '{device_name}' обязательно указать канал (ch<номер>)")
                config = {ch: None for ch in dev_info['Channels']}
            else:
                if channel is not None:
                    self._error(f"У устройства '{device_name}' нет каналов")
                config = None

            columns = []
            self._add_segment_columns(dev_info, channel, first_values, columns)
            if dev_info['Channels']:
                config[channel] = preset if preset else "FastStart"
            else:
                config = preset if preset else "FastStart"

            #Последующие сегменты - это каналы того же устройства (имя не повторяется)
            for segment in segments[1:]:
                ch_target, ch_values = self._split_segment(segment, token)
                ch, ch_preset = self._parse_channel_target(ch_target)

                if not dev_info['Channels']:
                    self._error(f"Устройство '{device_name}' не имеет каналов")
                if ch not in dev_info['Channels']:
                    self._error(f"У устройства '{device_name}' нет канала ch{ch}")
                if config[ch] is not None:
                    self._error(f"Канал ch{ch} устройства '{device_name}' указан несколько раз")

                self._add_segment_columns(dev_info, ch, ch_values, columns)
                config[ch] = ch_preset if ch_preset else "FastStart"

            requested_devices[device_name] = {
                'LibraryName': dev_info['LibraryName'],
                'Config': config,
                'Columns': columns,
            }

        return requested_devices

    def _split_segment(self, segment, token):
        if '=' not in segment:
            self._error(f"В аргументе '{token}' отсутствует '=' перед перечнем величин")
        target, values = segment.split('=', 1)
        return target, values

    def _parse_device_target(self, target):
        preset = None
        if '~' in target:
            target, preset = target.split('~', 1)
            preset = preset.strip() or None

        channel = None
        if '.' in target:
            name, ch_part = target.split('.', 1)
            channel = self._parse_channel(ch_part)
        else:
            name = target
        name = name.strip()

        if not name:
            self._error("Не указано имя устройства")
        if name not in self.pool:
            self._error(f"Устройство '{name}' не найдено в Devices.ini")
        if self.pool[name]['Type'] != 'instrument':
            self._error(f"Устройство '{name}' не является измерителем (type != instrument)")

        return name, channel, preset

    def _parse_channel_target(self, target):
        preset = None
        if '~' in target:
            target, preset = target.split('~', 1)
            preset = preset.strip() or None
        channel = self._parse_channel(target)
        return channel, preset

    def _parse_channel(self, ch_part):
        ch_part = ch_part.strip()
        if not ch_part.startswith('ch') or not ch_part[2:].isdigit():
            self._error(f"Неверный формат канала '{ch_part}', ожидается ch<номер>")
        return ch_part[2:]

    def _add_segment_columns(self, dev_info, channel, values_str, columns):
        if not values_str.strip():
            self._error("Не указан перечень измеряемых величин после '='")

        seen_values = set()
        for item in values_str.split(','):
            item = item.strip()
            if not item:
                self._error(f"Пустая величина в наборе '{values_str}'")

            label = None
            if '@' in item:
                value, label = item.split('@', 1)
                value, label = value.strip(), label.strip()
                if not label:
                    self._error(f"Пустое имя полотна после '@' в '{item}'")
            else:
                value = item

            if value not in dev_info['Values']:
                self._error(f"Величина '{value}' недоступна для устройства '{dev_info['Model']}'")
            if value in seen_values:
                self._error(f"Величина '{value}' указана несколько раз")
            seen_values.add(value)

            unit = self._unit_for(dev_info, value)
            key = f"{value}{channel}" if channel else value
            columns.append({
                'key': key,
                'channel': channel,
                'value': value,
                'unit': unit,
                'canvas': label,
            })

    @staticmethod
    def _unit_for(dev_info, value):
        values, units = dev_info['Values'], dev_info['Units']
        index = values.index(value)
        return units[index] if index < len(units) else ''

    #---ФОРМИРОВАНИЕ СПИСКА ГРАФИКОВ---
    def build_graphs(self, req_devices):
        graphs = []
        for device_name, device_info in req_devices.items():
            for column in device_info.get('Columns', []):
                if column.get('canvas'):
                    graphs.append({
                        'device': device_name,
                        'key': column['key'],
                        'channel': column['channel'],
                        'value': column['value'],
                        'unit': column['unit'],
                        'canvas': column['canvas'],
                    })
        return graphs

    @staticmethod
    def _error(message):
        print(f"\n[ОШИБКА]: {message}")
        sys.exit(1)
