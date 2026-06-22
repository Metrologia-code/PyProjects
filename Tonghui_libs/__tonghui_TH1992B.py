import time
import random
import math

class Device:
    def __init__(self):
        print("[TEST] Создан виртуальный прибор TH1992B")

    def Initialize(self, **kwargs):
        print(f"[TEST] TH1992B: Имитация подключения к {kwargs.get('DeviceAddress')} — УСПЕШНО")
        return True

    def ConfigureDevice(self, ConfigName):
        print(f"[TEST] TH1992B: Загружен пресет {ConfigName}")
        return True

    def SingleMeasure(self):
        measure_time = time.time()
        drift = math.sin(measure_time)
        results = {
            'CURR1': 1.5e-3 + random.uniform(-1e-4, 1e-4) + drift * 1e-4,
            'VOLT1': 12.0 + random.uniform(-0.5, 0.5) + drift * 2.0,
            'RES1':  100.0 + random.uniform(-2.0, 2.0),
            'CURR2': 4.5e-9 + random.uniform(-5e-10, 5e-10),
            'VOLT2': 5.0 + random.uniform(-0.2, 0.2),
            'RES2':  1000.0 + random.uniform(-10.0, 10.0)
        }
        return results
