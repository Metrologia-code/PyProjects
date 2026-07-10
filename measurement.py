from datetime import datetime
import time
import threading
import signal
import os
from Complex_libs.Devices import Devices
from User_libs import build_file_header, Plotter

class MeasurementSession:
    def __init__(self, args, instruments, file_path, file_mode='w', header_prefix='time, s', 
                 row_prefix_callback=None, canvas_points=20000, task_info="", wait_callback=None,
                 x_callback=None, x_label='t, сек'):
        if task_info:
            print(f"\n{task_info}")
        print(f"Результаты сохраняем в: {file_path}")
        self.args = args
        self.Instruments = instruments
        self.file_path = file_path
        self.file_mode = file_mode
        self.header_prefix = header_prefix
        self.row_prefix_callback = row_prefix_callback
        self.wait_callback = wait_callback
        self.x_callback = x_callback
        self.x_label = x_label
        # Установка обработчика Ctrl+C на уровне ОС
        self._original_sigint = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, self._handle_sigint)
        # Подготовка графика
        self.Plots = None
        if args.graph:
            import matplotlib.pyplot as plt
            plt.close('all')
            time.sleep(0.5)
            print(f"График сохраняем в: {file_path.replace('.txt', '.png')}")
            self.Plots = Plotter(
                args=args.graph, 
                x_label=self.x_label, 
                plot_name=f"Измерение", 
                x_pts=canvas_points
            )
        self.start_time = time.time()

    def _handle_sigint(self, signum, frame):
        print("Программа остановлена пользователем")
        if self.Plots:
            self.Plots.save_figure(self.file_path.replace('.txt', ''))
        os._exit(0)

    def run_measurement_loop(self, num_points):
        """
        Основной цикл измерений.
        """
        try:
            with open(self.file_path, self.file_mode, encoding='utf-8') as file:
                if self.file_mode == 'w':
                    file.write(build_file_header(data_keys=self.Instruments.device_data_keys, prefix=self.header_prefix))
                    file.flush()  # Заголовок сбрасываем сразу
                last_flush_minute = 0
                for point_idx in range(num_points):
                    t_measure_start = time.perf_counter()
                    if self.row_prefix_callback:
                        prefix = self.row_prefix_callback(point_idx)
                    else:
                        prefix = ""
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
                    measurement_time = time.time() - self.start_time
                    device_results_line = ""
                    for device_name in self.Instruments.devices.keys():
                        results = thread_results.get(device_name)
                        for key in self.Instruments.device_data_keys[device_name]:
                            val = results.get(key) if results else float('nan')
                            device_results_line += f'\t{val:.3e}'
                    to_write = f'{measurement_time:.3f}{prefix}{device_results_line}'
                    print(to_write)
                    file.write(to_write + '\n')
                    # Сбрасываем буфер на диск раз в минуту
                    current_minute = int(measurement_time) // 60
                    if current_minute != last_flush_minute:
                        file.flush()
                        last_flush_minute = current_minute
                    if self.Plots:
                        # Для графика берём X из callback'а или используем время
                        x = self.x_callback() if self.x_callback is not None else measurement_time
                        self.Plots.plot_routine(point_idx, x, thread_results)
                    t_fact = time.perf_counter() - t_measure_start
                    # Ожидание: либо внешний коллбэк, либо стандартный период из args
                    if self.wait_callback is not None:
                        self.wait_callback()
                    else:
                        t_sleep = self.args.period - t_fact
                        if t_sleep > 0:
                            time.sleep(t_sleep)
                        else:
                            print(f"[WARNING] Итерация {point_idx} не уложилась в период! Затрачено: {t_fact:.3f} с из {self.args.period} с.")
        except KeyboardInterrupt:
            # Фолбэк, если сигнал не успел сработать
            print("Программа остановлена пользователем")
            import sys
            sys.exit(0)
        finally:
            if self.Plots:
                self.Plots.save_figure(self.file_path.replace('.txt', ''))