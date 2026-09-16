import time
import random
import math

class Device:
    def __init__(self):
        print("[TEST] Создан виртуальный прибор TH1992B")
        # Счётчик вызовов: первые 2 вызова дают 0.0 (пробный опрос Devices.py + первый
        # отсчёт измерительного цикла), затем сигнал уходит в отрицательные наноамперы.
        # Ось Y при этом фиксирует порядок 10^0 и не перестраивается -> деградация формата.
        self._n = 0

    def Initialize(self, **kwargs):
        return True

    def ConfigureDevice(self, ConfigName):
        return True

    def SingleMeasure(self):
        self._n += 1
        if self._n <= 2:
            # пробный опрос Devices + первый отсчёт: пикоамперы -> ось замораживает (1e-11)
            curr1 = -9e-11 + random.uniform(-1e-11, 1e-11)
        else:
            # лавинообразный рост модуля тока: к последней точке достигаем ~ -0.09 А,
            # тик -0.09/1e-11 = -9e+09 -> на оси появится "-9e+09" (тот самый "-9+09")
            k = (self._n - 2) * (9.0 / 29.0)
            curr1 = -9e-11 * (10 ** k) * (1 + random.uniform(-0.02, 0.02))
        results = {
            'CURR1': curr1,
            'VOLTage1': 12.0 + random.uniform(-0.5, 0.5),
            'RES1':  100.0 + random.uniform(-2.0, 2.0),
            'CURR2': 4.5e-12 + random.uniform(-5e-13, 5e-13),
            'VOLT2': 5.0 + random.uniform(-0.2, 0.2),
            'RES2':  100.0 + random.uniform(-2.0, 2.0)
        }
        return results
