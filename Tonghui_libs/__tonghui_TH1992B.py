import time
import random
import math

class Device:
    def __init__(self):
        print("[TEST] Создан виртуальный прибор TH1992B")

    def Initialize(self, **kwargs):
        return True

    def ConfigureDevice(self, ConfigName):
        return True

    def SingleMeasure(self):
        # ВОСПРОИЗВЕДЕНИЕ БАГА ЧЕРЕЗ ЧИСТЫЕ СИГНАЛЫ РАЗНЫХ МАСШТАБОВ
        # Первый ток выдает миллиамперы (порядок -3 -> сбросится в 0), 
        # а второй ток выдает пикоамперы (порядок -12).
        # На стыке их объединения строковый split('_') в плоттере сломается и выдаст int() NameError
        results = {
            'CURR1': 1.5e-3 + random.uniform(-1e-4, 1e-4), # Порядок -3 -> уйдет в класс 10^0
            'VOLT1': 12.0 + random.uniform(-0.5, 0.5),
            'RES1':  100.0 + random.uniform(-2.0, 2.0),
            
            'CURR2': 4.5e-12 + random.uniform(-5e-13, 5e-13), # Порядок -12 -> уйдет в класс 10^-12
            'VOLT2': 5.0 + random.uniform(-0.2, 0.2),
            'RES2':  100.0 + random.uniform(-2.0, 2.0)
        }
        return results
