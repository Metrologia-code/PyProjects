from datetime import datetime
import time
import threading
from Complex_libs.Devices import Devices
from User_libs import build_file_header, Plotter

class MeasurementSession:
    def __init__(self, args, file_path, file_mode='w', row_prefix_callback=None, canvas_points=20):
        """
        row_prefix_callback: функция, принимающая номер итерации и возвращающая
                            строку-префикс, которая будет приклеена к данным приборов.
                            Если None — префикс пустой.
        canvas_points: количество точек по оси X на графике.
        """
        self.args = args
        self.file_path = file_path
        self.file_mode = file_mode
        self.row_prefix_callback = row_prefix_callback
        
        # Инициализация измерительного комплекса
        self.Instruments = Devices(args)
        
        # Подготовка графика
        self.Plots = None
        if args.graph:
            import matplotlib.pyplot as plt
            plt.close('all')
            print(f"График сохраняем в: {file_path.replace('.txt', '.png')}")
            self.Plots = Plotter(
                args=args.graph, 
                x_label='t, сек', 
                plot_name=f"Измерение", 
                x_pts=canvas_points
            )
            time.sleep(0.5)
        
        self.start_time = time.time()
    
    def run_measurement_loop(self, num_points, task_info=""):
        """
        Основной цикл измерений.
        """
        print(f"\n{task_info}")
        print(f"Результаты сохраняем в: {self.file_path}")
        
        try:
            with open(self.file_path, self.file_mode, encoding='utf-8') as file:
                # Записываем шапку только при создании нового файла
                if self.file_mode == 'w':
                    file.write(build_file_header(self.Instruments.device_data_keys) + '\n')
                
                # Основной цикл измерений
                for point_idx in range(num_points):
                    # Фиксируем высокоточную стартовую метку времени (включая подготовку точки)
                    t_measure_start = time.perf_counter()
                    
                    # Получаем префикс строки (может включать перемещение осей)
                    if self.row_prefix_callback:
                        prefix = self.row_prefix_callback(point_idx)
                    else:
                        prefix = ""
                    
                    # Параллельный опрос всех приборов
                    thread_results = {}
                    threads = []
                    
                    def worker(d_name, d_obj):
                        thread_results[d_name] = d_obj.SingleMeasure()
                    
                    for device_name, device_obj in self.Instruments.devices.items():
                        t_thread = threading.Thread(target=worker, args=(device_name, device_obj))
                        threads.append(t_thread)
                        t_thread.start()
                    
                    for thread in threads:
                        thread.join()
                    
                    # Вычисляем время с начала эксперимента
                    measurement_time = time.time() - self.start_time
                    
                    # Собираем показания приборов
                    device_results_line = ""
                    for device_name in self.Instruments.devices.keys():
                        results = thread_results.get(device_name)
                        for key in self.Instruments.device_data_keys[device_name]:
                            val = results.get(key) if results else float('nan')
                            device_results_line += f'\t{val:.3e}'
                    
                    # Формируем финальную строку: время + префикс + данные приборов
                    to_write = f'{measurement_time:.3f}{prefix}{device_results_line}'
                    
                    print(to_write)
                    file.write(to_write + '\n')
                    
                    # Обновляем график
                    if self.Plots:
                        self.Plots.plot_routine(point_idx, measurement_time, thread_results)
                    
                    # Вычисляем фактически затраченное время (включая подготовку точки)
                    t_fact = time.perf_counter() - t_measure_start
                    t_sleep = self.args.period - t_fact
                    
                    # Удерживаем жесткую временную сетку шага измерения
                    if t_sleep > 0:
                        time.sleep(t_sleep)
                    else:
                        print(f"[WARNING] Итерация {point_idx} не уложилась в период! Затрачено: {t_fact:.3f} с из {self.args.period} с.")
        
        except KeyboardInterrupt:
            print("Программа остановлена пользователем")
            import sys
            sys.exit(0)
        finally:
            # Сохраняем снимок графика при любом завершении (штатном или по Ctrl+C)
            if self.Plots:
                self.Plots.save_figure(self.file_path.replace('.txt', ''))
        
        if self.Plots:
            self.Plots.keep_open()