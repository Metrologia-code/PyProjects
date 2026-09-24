import time
import random

class Device:
    def __init__(self):
        print("[TEST] Создан виртуальный прибор TH2690A")

    def Initialize(self, **kwargs):
        print(f"[TEST] TH2690A: Имитация подключения к {kwargs.get('DeviceAddress')} — УСПЕШНО")
        return True

    def ConfigureDevice(self, ConfigName):
        print(f"[TEST] TH2690A: Загружен пресет {ConfigName}")
        return True

    def SingleMeasure(self):
        results = {
            'VOLT': 12.0 + random.uniform(-0.5, 0.5),
            'CURR': 2.2e-3 + random.uniform(-1e-4, 1e-4),
        }
        return results
