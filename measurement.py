import sys
import time
import threading
import signal
import os
from User_libs import build_file_header, Plotter, PlotConfig

#---ПАРАМЕТРЫ ВОССТАНОВЛЕНИЯ СВЯЗИ (общие для логгера и сканера)---
RECONNECT_TIMEOUT = 30 * 24 * 3600   # окно попыток восстановления связи, сек (~месяц по умолчанию)
RECONNECT_RETRY_INTERVAL = 5.0       # пауза между попытками переподключения, сек
RECONNECT_FAIL_THRESHOLD = 2         # число подряд неудачных измерений до перехода в lost


class MeasurementSession:
    def __init__(self, args, instruments, file_path, file_mode='w', header_prefix='time, s',
                 row_prefix_callback=None, canvas_points=20000, task_info="", wait_callback=None,
                 x_callback=None, x_label='t, сек',
                 reconnect_timeout=RECONNECT_TIMEOUT,
                 reconnect_retry_interval=RECONNECT_RETRY_INTERVAL,
                 reconnect_fail_threshold=RECONNECT_FAIL_THRESHOLD):
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
        # Параметры восстановления связи
        self.reconnect_timeout = reconnect_timeout
        self.reconnect_retry_interval = reconnect_retry_interval
        self.reconnect_fail_threshold = reconnect_fail_threshold
        # Состояние приборов: ok / lost / dropped
        self._state_lock = threading.Lock()
        self._dev_state = {name: 'ok' for name in instruments.devices}
        self._fail_count = {name: 0 for name in instruments.devices}
        self._lost_at = {}
        self._last_attempt = {}
        self._dropped = set()
        self._fatal_error = None
        self._reconnect_thread = None
        # Установка обработчика Ctrl+C на уровне ОС
        self._original_sigint = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, self._handle_sigint)
        # Подготовка графика
        self.Plots = None
        noplot = getattr(args, 'noplot', False)
        if args.graph and not noplot:
            plot_config = PlotConfig.from_cli(getattr(args, 'plot', None) or [])
            import matplotlib.pyplot as plt
            plt.close('all')
            time.sleep(0.5)
            print(f"График сохраняем в: {file_path.replace('.txt', '.png')}")
            self.Plots = Plotter(
                args=args.graph,
                x_label=self.x_label,
                plot_name=f"Измерение",
                x_pts=canvas_points,
                config=plot_config
            )
        elif args.graph and noplot:
            print("Построение графиков отключено (-np)")
        self.start_time = time.time()

    def _handle_sigint(self, signum, frame):
        print("Программа остановлена пользователем")
        if self.Plots:
            self.Plots.save_figure(self.file_path.replace('.txt', ''))
        os._exit(0)

    #---СОСТОЯНИЕ ПРИБОРОВ И ВОССТАНОВЛЕНИЕ СВЯЗИ---
    def _mark_lost(self, device_name):
        with self._state_lock:
            if self._dev_state.get(device_name) == 'ok':
                self._dev_state[device_name] = 'lost'
                self._lost_at[device_name] = time.time()
                print(f"[WARNING] Прибор {device_name}: связь потеряна, начинаю восстановление")
        self._ensure_reconnect_thread()

    def _ensure_reconnect_thread(self):
        if self._reconnect_thread is None or not self._reconnect_thread.is_alive():
            self._reconnect_thread = threading.Thread(target=self._reconnect_loop, daemon=True)
            self._reconnect_thread.start()

    def _reconnect_loop(self):
        while True:
            with self._state_lock:
                lost = [n for n, s in self._dev_state.items() if s == 'lost']
            if not lost:
                time.sleep(self.reconnect_retry_interval)
                continue
            now = time.time()
            for name in lost:
                with self._state_lock:
                    if self._dev_state.get(name) != 'lost':
                        continue
                    lost_at = self._lost_at.get(name)
                    last_attempt = self._last_attempt.get(name, 0.0)
                if now - lost_at >= self.reconnect_timeout:
                    self._drop_device(name)
                    continue
                if now - last_attempt < self.reconnect_retry_interval:
                    continue
                self._last_attempt[name] = now
                ok = self.Instruments.reconnect(name)
                with self._state_lock:
                    if ok:
                        self._dev_state[name] = 'ok'
                        self._fail_count[name] = 0
                        print(f"[RECONNECT] Прибор {name}: связь восстановлена")
                    else:
                        print(f"[RECONNECT] Прибор {name}: попытка восстановления не удалась")
            time.sleep(self.reconnect_retry_interval)

    def _drop_device(self, device_name):
        with self._state_lock:
            if self._dev_state.get(device_name) == 'dropped':
                return
            self._dev_state[device_name] = 'dropped'
            self._dropped.add(device_name)
            print(f"[ERROR] Прибор {device_name}: окно восстановления истекло, прибор отключён")
            active = [n for n, s in self._dev_state.items() if s in ('ok', 'lost')]
            if not active:
                self._fatal_error = (
                    f"Все приборы потеряли связь и не восстановились за отведённое время "
                    f"(последний — {device_name})"
                )
                print(f"[ERROR] {self._fatal_error}")

    def run_measurement_loop(self, num_points):
        """
        Основной цикл измерений.
        """
        try:
            with open(self.file_path, self.file_mode, encoding='utf-8') as file:
                if self.file_mode == 'w':
                    file.write(build_file_header(data_columns=self.Instruments.device_columns, prefix=self.header_prefix))
                    file.flush()  # Заголовок сбрасываем сразу
                last_flush_minute = 0
                for point_idx in range(num_points):
                    if self._fatal_error:
                        break
                    t_measure_start = time.perf_counter()
                    if self.row_prefix_callback:
                        prefix = self.row_prefix_callback(point_idx)
                    else:
                        prefix = ""
                    with self._state_lock:
                        ok_names = [n for n, s in self._dev_state.items() if s == 'ok']
                    thread_results = {}
                    threads = []
                    def worker(d_name, d_obj):
                        try:
                            thread_results[d_name] = d_obj.SingleMeasure()
                        except Exception:
                            thread_results[d_name] = None
                    for device_name in ok_names:
                        t_thread = threading.Thread(target=worker, args=(device_name, self.Instruments.devices[device_name]))
                        threads.append(t_thread)
                        t_thread.start()
                    for thread in threads:
                        thread.join()
                    # Учёт успешных/неудачных измерений для живых приборов
                    for device_name in ok_names:
                        result = thread_results.get(device_name)
                        if isinstance(result, dict):
                            self._fail_count[device_name] = 0
                        else:
                            self._fail_count[device_name] += 1
                            if self._fail_count[device_name] >= self.reconnect_fail_threshold:
                                self._mark_lost(device_name)
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
                        plot_results = {n: (r if isinstance(r, dict) else {}) for n, r in thread_results.items()}
                        self.Plots.plot_routine(point_idx, x, plot_results)
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
            sys.exit(0)
        finally:
            if self.Plots:
                self.Plots.save_figure(self.file_path.replace('.txt', ''))

        if self._fatal_error:
            print(f"[ERROR] Завершение программы: {self._fatal_error}")
            sys.exit(1)
