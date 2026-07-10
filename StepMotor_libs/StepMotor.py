import struct
from enum import IntEnum, Enum, auto
import logging
from dataclasses import dataclass
from pymodbus.client import ModbusTcpClient
from pymodbus import ModbusException
from pymodbus.exceptions import ConnectionException
from time import sleep
import datetime

# Задаем расширенный формат логирования: время - уровень - сообщение
logging.basicConfig(format="%(asctime)s %(levelname)-8s %(message)s", level=logging.ERROR, datefmt="%Y-%m-%d %H:%M:%S")

# Получаем экземпляр логгера библиотеки
logger = logging.getLogger("pymodbus")
logger.setLevel(logging.ERROR)

# Настройки подключения к USR-TCP232-304 по умолчанию
SERVER_IP = "192.168.88.13"
SERVER_PORT = 8234


class MoveCommand(IntEnum):
    """MOVE-команды для записи в CMD-регистр"""
    MOVE = 1
    GOTO = 2
    GOTO_DIR = 3
    GOHOME = 4


class RunCommand(IntEnum):
    """RUN-команды для записи в CMD-регистр"""
    RUN = 0
    GOUNTIL_SLOWSTOP = 5
    GOUNTIL_FRONT_SLOWSTOP = 6
    GOUNTIL_HARDSTOP = 7
    GOUNTIL_FRONT_HARDSTOP = 8
    RELEASE = 9
    FRONT_RELEASE = 10


class MemoryType(Enum):
    """Типы регистров и полей для доступа через протокол Modbus"""
    HOLDING = auto()
    INPUT = auto()
    COIL = auto()
    DISCRETE = auto()


@dataclass(frozen=True, slots=True)
class Field:
    """Класс описывающий регистры и поля: адрес, тип, хранимый тип данных, размер"""
    address: int
    memory: MemoryType
    datatype: ModbusTcpClient.DATATYPE | None
    count: int = 1


class ModbusFields:
    """Список регистров и полей для доступа через протокол Modbus.
    Список можно пополнять по мере необходимости."""
    D352 = Field(0x3200, MemoryType.INPUT, ModbusTcpClient.DATATYPE.UINT16)  # Показания с потенциометра "0"
    D353 = Field(0x3201, MemoryType.INPUT, ModbusTcpClient.DATATYPE.UINT16)  # Показания с потенциометра "1"
    D354 = Field(0x3202, MemoryType.INPUT, ModbusTcpClient.DATATYPE.UINT16)  # Показания с потенциометра "SPEED"
    ABS = Field(0x5006, MemoryType.HOLDING, ModbusTcpClient.DATATYPE.INT32, count=2)  # Текущая позиция
    U_STEP = Field(0x5009, MemoryType.HOLDING, ModbusTcpClient.DATATYPE.UINT16)  # Величина дробления полного шага
    DIR = Field(0x500A, MemoryType.COIL, None)  # Направление (True - прямое, False - обратное)
    TARGET_POS = Field(0x500E, MemoryType.HOLDING, ModbusTcpClient.DATATYPE.INT32, count=2)  # Целевая позиция
    CMD = Field(0x5010, MemoryType.HOLDING, ModbusTcpClient.DATATYPE.UINT16)  # Команда драйверу (CMD-регистр)
    MOTOR_STATUS = Field(0x5037, MemoryType.DISCRETE, None, count=7)  # Текущее состояние двигателя
    SPIN = Field(0x5100, MemoryType.COIL, None)  # Старт выполнения команды в CMD-регистре
    REBOOT = Field(0x8101, MemoryType.COIL, None)  # Перезагрузка контроллера

    # Управление системным временем и датой SMSD-4.2
    DATA_TIME = Field(0x8110, MemoryType.HOLDING, ModbusTcpClient.DATATYPE.UINT16, count=6)  # Сек, мин, ч, д, мес, год
    DATA_TIME_SET = Field(0x8111, MemoryType.COIL, None, count=2)  # Флаги установки времени и даты
    DATA_TIME_PROTECT = Field(0x8110, MemoryType.COIL, None)  # Флаги защиты установки времени и даты


@dataclass(frozen=True, slots=True)
class MotorStatus:
    HIZ: bool | None = None  # HiZ-состояние
    STOP: bool | None = None  # Режим удержания
    ACCELERATING: bool | None = None  # Ускорение
    DECELERATING: bool | None = None  # Торможение
    STEADY: bool | None = None  # Движение с постоянной скоростью
    BUSY_MOVE: bool | None = None  # Невозможность применения команд группы MOVE
    BUSY_RUN: bool | None = None  # Невозможность применения команд группы RUN

    def __str__(self):
        return '\n'.join([f'HIZ: {self.HIZ}',
                          f'STOP: {self.STOP}',
                          f'ACCELERATING: {self.ACCELERATING}',
                          f'DECELERATING: {self.DECELERATING}',
                          f'STEADY: {self.STEADY}',
                          f'BUSY_MOVE: {self.BUSY_MOVE}',
                          f'BUSY_RUN: {self.BUSY_RUN}'])

    @property
    def busy(self):
        return self.BUSY_MOVE or self.BUSY_RUN

    @property
    def moving(self):
        return self.ACCELERATING or self.DECELERATING or self.STEADY


class StepMotor:
    def __init__(self, host: str = SERVER_IP, port: int = SERVER_PORT, unit_id: int = 1, timeout: float = 3.0):
        """Инициализация параметров подключения."""
        self.unit_id = unit_id
        self.client = ModbusTcpClient(host=host, port=port, timeout=timeout)

    def __enter__(self):
        """Контекстный менеджер: открытие подключения."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Контекстный менеджер: закрытие подключения."""
        self.disconnect()

    def connect(self) -> bool:
        """Установка соединения с Modbus TCP сервером."""
        if not self.client.connected and not self.client.connect():
            raise ConnectionException(f'Connection failed')

        logger.info(f"Подключение установлено.")
        return self.client.connected

    def disconnect(self):
        """Закрытие соединения."""
        if self.client and self.client.connected:
            self.client.close()
            logger.info("Соединение разорвано.")

    def _convert_from_registers(self, registers: list[int], data_type: ModbusTcpClient.DATATYPE):
        """Преобразование «сырых» данных из 16-битных регистров Modbus в читаемые типы данных Python"""
        return self.client.convert_from_registers(registers=registers, data_type=data_type, word_order="little")

    def _convert_to_registers(self, value: int | float | str | list[bool] | list[int] | list[float],
                              data_type: ModbusTcpClient.DATATYPE) -> list[int]:
        """Преобразование значение любого типа в список 16-битных регистров Modbus"""
        return self.client.convert_to_registers(value=value, data_type=data_type, word_order="little")

    @staticmethod
    def _execute(fn, *args, **kwargs):
        try:
            r = fn(*args, **kwargs)
            if r.isError():
                logger.error(f"Ошибка Modbus при чтении: {r}")
                return None
            return r
        except ModbusException as e:
            logger.error(f"Исключение библиотеки Modbus: {e}")
            return None

    def _read_input_registers(self, address: int, *, count: int = 1):
        r = self._execute(self.client.read_input_registers, address, count=count, device_id=self.unit_id)
        return None if r is None else r.registers

    def _read_holding_registers(self, address: int, *, count: int = 1):
        r = self._execute(self.client.read_holding_registers, address, count=count, device_id=self.unit_id)
        return None if r is None else r.registers

    def _write_holding_registers(self, address: int, values: list[int]):
        return self._execute(self.client.write_registers, address, values, device_id=self.unit_id) is not None

    def _read_discrete_inputs(self, address: int, *, count: int = 1):
        r = self._execute(self.client.read_discrete_inputs, address, count=count, device_id=self.unit_id)
        return None if r is None else r.bits[:count]

    def _read_coils(self, address: int, *, count: int = 1):
        r = self._execute(self.client.read_coils, address, count=count, device_id=self.unit_id)
        return None if r is None else r.bits[:count]

    def _write_coils(self, address: int, values: list[bool]):
        return self._execute(self.client.write_coils, address, values, device_id=self.unit_id) is not None

    def _read(self, field: Field):
        if field.memory is MemoryType.HOLDING:
            data = self._read_holding_registers(field.address, count=field.count)
            if data:
                return self.client.convert_from_registers(data, field.datatype, word_order="little")

        elif field.memory is MemoryType.INPUT:
            data = self._read_input_registers(field.address, count=field.count)
            if data:
                return self.client.convert_from_registers(data, field.datatype, word_order="little")

        elif field.memory is MemoryType.COIL:
            return self._read_coils(field.address, count=field.count)

        elif field.memory is MemoryType.DISCRETE:
            return self._read_discrete_inputs(field.address, count=field.count)

    def _write(self, field: Field, values):
        if field.memory is MemoryType.HOLDING:
            try:
                registers = self._convert_to_registers(values, data_type=field.datatype)
                return self._write_holding_registers(field.address, registers)
            except (struct.error, TypeError):
                return False

        elif field.memory is MemoryType.COIL:
            return self._write_coils(field.address, list(values))

        elif field.memory is MemoryType.INPUT or field.memory is MemoryType.DISCRETE:
            logger.error(f'Запись значения по адресу {field.address} невозможна. Поле доступно только для чтения.')

    @property
    def status(self):
        bits = self._read(ModbusFields.MOTOR_STATUS)
        if bits:
            return MotorStatus(HIZ=bits[0],
                               STOP=bits[1],
                               ACCELERATING=bits[2],
                               DECELERATING=bits[3],
                               STEADY=bits[4],
                               BUSY_MOVE=bits[5],
                               BUSY_RUN=bits[6]
                               )
        return MotorStatus()

    @property
    def current_position(self):
        return self._read(ModbusFields.ABS)

    def reset_current_position(self):
        return self._write(ModbusFields.ABS, 0)

    @property
    def u_step(self):
        return self._read(ModbusFields.U_STEP)

    @u_step.setter
    def u_step(self, value):  # Почему-то устанавливается значение 6 и 9, надо проверять
        self._write(ModbusFields.U_STEP, value)

    @property
    def direction(self):
        return self._read(ModbusFields.DIR)[0]

    @direction.setter
    def direction(self, value):
        self._write(ModbusFields.DIR, [bool(value)])

    @property
    def target_position(self):
        return self._read(ModbusFields.TARGET_POS)

    @target_position.setter
    def target_position(self, value):
        self._write(ModbusFields.TARGET_POS, value)

    @property
    def command(self) -> MoveCommand | RunCommand | None:
        value = self._read(ModbusFields.CMD)

        try:
            return MoveCommand(value)
        except ValueError:
            pass

        try:
            return RunCommand(value)
        except ValueError:
            pass

        return value

    @command.setter
    def command(self, cmd: MoveCommand | RunCommand):
        self._write(ModbusFields.CMD, int(cmd))

    def _wait(self):
        while self.status.moving:
            sleep(0.01)

    def _spin(self):
        if not self.status.busy:
            if self._write(ModbusFields.SPIN, [True]):
                self._wait()
                return True
            logger.error(f'Не удалось выполнить команду SPIN.')
            return False
        logger.error(f'Запуск движения в данный момент невозможно.')
        return False

    def reboot(self):
        return self._write(ModbusFields.REBOOT, [True])

    def get_data_time(self):
        [seconds, minutes, hours, day, month, year] = self._read(ModbusFields.DATA_TIME)
        return datetime.datetime(year=2000 + year, month=month, day=day, hour=hours, minute=minutes, second=seconds)

    def set_data_time(self, dt: datetime.datetime = datetime.datetime.now()):
        self._write(ModbusFields.DATA_TIME_PROTECT, [False])
        self._write(ModbusFields.DATA_TIME, [dt.second, dt.minute, dt.hour, dt.day, dt.month, dt.year % 100])
        self._write(ModbusFields.DATA_TIME_SET, [True, True])
        self._write(ModbusFields.DATA_TIME_PROTECT, [True])

    def go_to(self, mirosteps_position):
        self.target_position = mirosteps_position
        self.command = MoveCommand.GOTO
        return self._spin()

    def go_home(self):
        self.command = MoveCommand.GOHOME
        return self._spin()
