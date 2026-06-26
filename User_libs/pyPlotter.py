import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MaxNLocator, FixedLocator

# Глобальный паспорт физических размерностей измерительного комплекса
# Используется при парсинге args и при формировании подписей осей Y
UNITS = {'CURR': 'I', 'VOLT': 'V', 'RES': 'Ohm'}

# Значения по умолчанию для параметров графика
xLabel, plotName, plotPoints = 'x', 'Test', 100

class Plotter:
    """
    Класс Plotter предназначен для отрисовки графиков в реальном времени на основе данных с измерительных приборов.

    Формат аргументов.
    В конструктор передается список строк вида 'ИмяПрибора.Параметр'.
    Для многоканальных приборов к имени параметра добавляется номер канала: 'TH1992B_1.CURR1', 'TH1992B_1.VOLT2'.
    Для одноканальных приборов суффикс не нужен: 'TH2690A_1.CURR', 'TH2690A_1.VOLT'.
    Имя параметра должно содержать подстроку 'CURR', 'VOLT' или 'RES' — по ней из глобального словаря UNITS берется
    физическая размерность ('I', 'V', 'Ohm'). Если подстроки нет, размерность остается пустой.

    Параметры конструктора.
    - args: список строк 'Прибор.Параметр'.
    - x_label: подпись оси X, по умолчанию 'x'.
    - plot_name: заголовок графика, по умолчанию 'Test'.
    - x_pts: длина скользящего окна по оси X, по умолчанию 100.

    Распределение по осям и цвета.
    Список args делится пополам: первая половина выводится на левую ось Y, вторая — на правую. Если с одной стороны
    несколько линий, их оси раздвигаются рассчитываемым смещением offset (шаг Y_AXIS_WIDTH пикселей), чтобы не перекрываться.
    Цвет линии задается порядковым номером в списке args и берется из палитры класса colors по индексу.

    Поведение при отсутствии данных.
    Если в словаре results нет прибора или параметра, в данные подставляется NaN. Линия в этой точке разрывается.

    Метод plot_routine(i, x, results).
    Принимает номер итерации, значение оси X (время в сек) и словарь вида {'ИмяПрибора': {'Параметр': значение, ...}, ...}.
    Ничего не возвращает, только обновляет график.
    - Ось X начинает скользить, когда количество точек данных превышает x_pts.
    - Для каждой оси Y автоматически подбирает порядок (множитель 1eN), если макс. значение выходит за пределы [1e-3, 1e3].
    - Метки оси X прореживаются до MAX_X_TICKS равномерно через np.linspace, чтобы избежать наложения.
    - После заполнения скользящего окна (len(xdata) >= x_pts) ширина оси X фиксируется на [xdata[0], xdata[-1]].

    Методы save_figure и keep_open.
    - save_figure(file_path): сохраняет текущий график в PNG по пути file_path + '.png'.
    - keep_open(): удерживает окно открытым после завершения программы (переключает mpl в неинтерактивный режим и вызывает show).
    """

    # Ширина отступа оси Y от графика в пикселях
    Y_AXIS_WIDTH = 65
    # Максимальное количество тиков на оси Y
    MAX_Y_TICKS = 12
    # Максимальное количество тиков на оси X
    MAX_X_TICKS = 18
    # Размер фигуры (ширина, высота) в дюймах
    FIGURE_SIZE = (9, 5)
    # Размер шрифта заголовка графика
    FONT_SIZE_TITLE = 12
    # Размер шрифта подписи оси X
    FONT_SIZE_LABEL = 12
    # Размер шрифта тиков (меток делений)
    FONT_SIZE_TICK = 10
    # Размер шрифта легенды
    FONT_SIZE_LEGEND = 'x-small'

    def __init__(self, args, x_label=xLabel, plot_name=plotName, x_pts=plotPoints):
        self.x_pts = int(x_pts)
        self.lines = {}
        self.colors = ['b', 'r', 'g', 'm', 'c', 'k']
         
        left_limit = (len(args) + 1) // 2

        # Парсинг приборов/каналов и определение их размерностей
        for idx, item in enumerate(args):
            unit = ''
            # Размерность определяется по подстроке CURR/VOLT/RES в имени параметра
            for token, u in UNITS.items():
                if token in item: unit = u; break

            is_left = idx < left_limit
            # Для левой стороны offset считается от 0 (idx=0 даёт offset=0),
            # для правой — от границы left_limit, чтобы первая линия правой стороны тоже начиналась с offset=0
            offset = (idx if is_left else idx - left_limit) * self.Y_AXIS_WIDTH

            # Фиксируем цвет линии по ее порядковому индексу в списке аргументов
            line_color = self.colors[idx % len(self.colors)]

            self.lines[item] = {
                'source': item,
                'label': item,
                'unit': unit,
                'color': line_color,
                'ydata': [],
                'line_obj': None,
                'is_left': is_left,
                'offset': offset
            }

        # Инициализация графического окна
        plt.ion()
        self.fig, self.base_ax = plt.subplots(figsize=self.FIGURE_SIZE)
        self.base_ax.set_title(label=plot_name, fontname='Arial', fontsize=self.FONT_SIZE_TITLE)
        self.base_ax.set_xlabel(xlabel=x_label, fontname='Arial', fontsize=self.FONT_SIZE_LABEL)
        self.base_ax.tick_params(axis='x', rotation=65)
        self.base_ax.xaxis.set_major_formatter(FuncFormatter(lambda x, pos: f"{x:.1f}"))
        self.xdata = []

    def _init_axis(self, item, cfg):
        # Создание оси Y и настройка ее форматирования для одной линии
        if item == list(self.lines.keys())[0]:
            target_ax = self.base_ax
        else:
            target_ax = self.base_ax.twinx()
            side = 'left' if cfg['is_left'] else 'right'
            target_ax.yaxis.set_label_position(side)
            target_ax.yaxis.set_ticks_position(side)
            target_ax.spines[side].set_position(('outward', cfg['offset']))

        cfg['line_obj'], = target_ax.plot(self.xdata, cfg['ydata'], label=cfg['label'], color=cfg['color'])
        
        # Порядок оси меняется только если значения выходят за пределы [1e-3, 1e3]
        valid_data = [abs(y) for y in cfg['ydata'] if not np.isnan(y) and y != 0]
        max_val = max(valid_data) if valid_data else 1.0
        raw_order = int(np.floor(np.log10(max_val))) if max_val > 0 else 0
        order_val = raw_order if abs(raw_order) >= 3 else 0
        
        # Делит значения на порядок оси, чтобы подписи были читаемыми, и добавляет множитель (1eN) к подписи оси
        target_ax.yaxis.set_major_formatter(
            FuncFormatter(lambda y, pos, o=order_val: 
                f"{y/(10**o):.3g}" if o != 0 else f"{y:.3g}")
        )
        
        if order_val != 0:
            unit_label = f"{item}, {cfg['unit']} (1e{order_val})"
        else:
            unit_label = f"{item}, {cfg['unit']}" if cfg['unit'] else item
        
        target_ax.set_ylabel(ylabel=unit_label, fontname='Arial', fontsize=self.FONT_SIZE_TICK)
        target_ax.yaxis.label.set_color(cfg['line_obj'].get_color())
        target_ax.tick_params(axis='y', labelcolor=cfg['line_obj'].get_color(), labelsize=9)
        target_ax.spines[target_ax.yaxis.get_label_position()].set_color(cfg['line_obj'].get_color())
        
        target_ax.yaxis.set_major_locator(MaxNLocator(nbins=self.MAX_Y_TICKS, prune=None))
        
        self.fig.tight_layout()

    def plot_routine(self, i, x, results): 
        self.xdata.append(x)
        if len(self.xdata) > self.x_pts:
            self.xdata = self.xdata[1:]

        for item, cfg in self.lines.items():
            dev_part, key_part = cfg['source'].split('.')
            dev_data = results.get(dev_part, {})
            raw_val = dev_data.get(key_part, float('nan'))

            cfg['ydata'].append(raw_val)
            if len(cfg['ydata']) > self.x_pts:
                cfg['ydata'] = cfg['ydata'][1:]

            if cfg['line_obj'] is None:
                self._init_axis(item, cfg)

            cfg['line_obj'].set_xdata(self.xdata) 
            cfg['line_obj'].set_ydata(cfg['ydata'])
            
            ax_obj = cfg['line_obj'].axes
            # relim пересчитывает границы данных, autoscale_view применяет их к осям — нужны оба вызова
            ax_obj.relim()
            ax_obj.autoscale_view()

        # Прореживание тиков оси X с равномерным распределением
        if len(self.xdata) <= self.MAX_X_TICKS:
            tick_data = self.xdata
        else:
            indices = np.linspace(0, len(self.xdata) - 1, self.MAX_X_TICKS, dtype=int)
            tick_data = [self.xdata[idx] for idx in indices]
        
        # FixedLocator фиксирует тики строго в заданных позициях, иначе matplotlib добавит свои
        self.base_ax.xaxis.set_major_locator(FixedLocator(tick_data))
        self.base_ax.xaxis.set_major_formatter(FuncFormatter(lambda x, pos: f"{x:.1f}"))

        # После заполнения окна фиксируем диапазон X, чтобы autoscale_view не растягивал ось за пределы данных
        if len(self.xdata) >= self.x_pts:
            self.base_ax.set_xlim(self.xdata[0], self.xdata[-1])

        all_handles = [cfg['line_obj'] for cfg in self.lines.values() if cfg['line_obj']]
        all_labels = [h.get_label() for h in all_handles]
        self.base_ax.legend(all_handles, all_labels, loc='upper left', fontsize=self.FONT_SIZE_LEGEND)

        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

    def save_figure(self, file_path):
        plt.savefig(file_path + '.png')

    def keep_open(self):
        # Сначала выключаем интерактивный режим, потом show — иначе окно закроется сразу после выхода из программы
        plt.ioff()
        plt.show()