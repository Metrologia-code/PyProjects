import time

class Controller:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        # Генератор координат: храним текущее положение каждой оси
        self._positions = {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0}

    def connect(self):
        print(f"[TEST] Имитация подключения к контроллеру {self.ip}:{self.port} — УСПЕШНО")

    def ptp(self, axis_number, position):
        # Запоминаем целевую координату — get_fpos вернёт её
        self._positions[axis_number] = position

    def wait(self):
        pass

    def get_fpos(self, axis_number):
        return self._positions[axis_number]

    def enable_axis(self, axis_number):
        pass

    def m_state(self, axis_number):
        # В тестах все оси всегда включены
        return 'ON'

def InitSpeed(acs):
    for ax in range(4):
        if acs.m_state(ax) == 'OFF':
            acs.enable_axis(ax)
            print(f"Ось {ax} была выключена, включаем")
    print("[TEST] Имитация установки скоростей осей — УСПЕШНО")

def PrintPosition(acs):
    pass

def pos_to_x(axes, pos):
    return 0.0

def MoveBlades(acs, axes, cpos):
    if cpos == 0:
        # На первом шаге отправляем ВСЕ оси в start
        for ax in axes:
            acs.ptp(ax['number'], ax['pos'][cpos])
    else:
        # На остальных шагах двигаем только используемые оси
        for ax in axes:
            if ax['is_used']:
                acs.ptp(ax['number'], ax['pos'][cpos])
    time.sleep(0.01)
    acs.wait()