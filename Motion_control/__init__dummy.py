import time

class Controller:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
    def connect(self):
        print(f"[TEST] Имитация подключения к контроллеру {self.ip}:{self.port} — УСПЕШНО")
    def ptp(self, axis_number, position):
        pass 
    def wait(self):
        pass 
    def get_fpos(self, axis_number):
        return 0.000 
    def enable_axis(self, axis_number):
        pass

def InitSpeed(acs):
    print("[TEST] Имитация установки скоростей осей — УСПЕШНО")

def PrintPosition(acs):
    pass

def StartMove(acs, used_axis: int, to_go: int):
    pass

def pos_to_x(axes, pos):
    return 0.0

# Добавляем недостающую функцию измерительного шага осей
def move_axes_to_position(acs, axes, cpos):
    for ax in axes:
        if ax['is_used']:
            acs.ptp(ax['number'], ax['pos'][cpos])
    time.sleep(0.01)
    acs.wait()
