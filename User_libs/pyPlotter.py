import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MaxNLocator, FixedLocator

# Глобальный паспорт физических размерностей измерительного комплекса
UNITS = {'CURR': 'I', 'VOLT': 'V', 'RES': 'Ohm'}
xLabel, plotName, plotPoints = 'x', 'Test', 100

class Plotter:
    def __init__(self, args, x_label=xLabel, plot_name=plotName, x_pts=plotPoints):
        self.x_pts = int(x_pts)
        self.lines = {}
        self.colors = ['b', 'r', 'g', 'm', 'c', 'k']

        # Счетчики для определения стороны оси y
        axis_w = 65
        left_limit = (len(args) + 1) // 2
        left_count, right_count = 0, 0

        # Парсинг приборов/каналов и определение их размерностей
        for idx, item in enumerate(args):
            unit = ''
            for token, u in UNITS.items():
                if token in item: unit = u; break

            # Последовательное распределение осей по сторонам на основе лимита половин
            is_left = (idx < left_limit)
            offset = left_count * axis_w if is_left else right_count * axis_w
            
            if is_left: left_count += 1
            else: right_count += 1

            # Жестко фиксируем цвет линии по ее порядковому индексу в списке аргументов
            line_color = self.colors[idx % len(self.colors)]

            self.lines[item] = {'source': item, 'label': item,  'unit': unit, 'color': line_color,
                                'ydata': [], 'line_obj': None,
                                'is_left': is_left, 'offset': offset}

        # Инициализация графического окна
        plt.ion()
        self.fig, self.base_ax = plt.subplots(figsize=(9, 5))
        self.base_ax.set_title(label=plot_name, fontname='Arial', fontsize=12)
        self.base_ax.set_xlabel(xlabel=x_label, fontname='Arial', fontsize=12)
        self.xdata = []

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
                if item == list(self.lines.keys())[0]:
                    target_ax = self.base_ax
                else:
                    target_ax = self.base_ax.twinx()
                    side = 'left' if cfg['is_left'] else 'right'
                    target_ax.yaxis.set_label_position(side)
                    target_ax.yaxis.set_ticks_position(side)
                    target_ax.spines[side].set_position(('outward', cfg['offset']))

                cfg['line_obj'], = target_ax.plot(self.xdata, cfg['ydata'], label=cfg['label'], color=cfg['color'])
                
                valid_data = [abs(y) for y in cfg['ydata'] if not np.isnan(y) and y != 0]
                max_val = max(valid_data) if valid_data else 1.0
                raw_order = int(np.floor(np.log10(max_val))) if max_val > 0 else 0
                order_val = raw_order if abs(raw_order) >= 3 else 0
                
                target_ax.yaxis.set_major_formatter(FuncFormatter(lambda y, pos, o=order_val: f"{y/(10**o):.3g}" if o != 0 else f"{y:.3g}"))
                
                if order_val != 0:
                    unit_label = f"{item}, {cfg['unit']} (1e{order_val})"
                else:
                    unit_label = f"{item}, {cfg['unit']}" if cfg['unit'] else item
                    
                target_ax.set_ylabel(ylabel=unit_label, fontname='Arial', fontsize=10)
                target_ax.yaxis.label.set_color(cfg['line_obj'].get_color())
                target_ax.tick_params(axis='y', labelcolor=cfg['line_obj'].get_color(), labelsize=9)
                target_ax.spines[target_ax.yaxis.get_label_position()].set_color(cfg['line_obj'].get_color())
                
                target_ax.yaxis.set_major_locator(MaxNLocator(nbins=8, prune=None))
                
                self.fig.tight_layout()

            cfg['line_obj'].set_xdata(self.xdata)
            cfg['line_obj'].set_ydata(cfg['ydata'])
            
            ax_obj = cfg['line_obj'].axes
            ax_obj.relim()
            ax_obj.autoscale_view()

        # Жесткая привязка тиков оси X к фактическим точкам массива времени
        self.base_ax.xaxis.set_major_locator(FixedLocator(self.xdata))

        if len(self.xdata) >= self.x_pts:
            self.base_ax.set_xlim(self.xdata[0], self.xdata[-1])

        all_handles = [cfg['line_obj'] for cfg in self.lines.values() if cfg['line_obj']]
        all_labels = [h.get_label() for h in all_handles]
        self.base_ax.legend(all_handles, all_labels, loc='upper left', fontsize='x-small')

        self.fig.canvas.draw()
        self.fig.canvas.flush_events()


    def save_figure(self, file_path):
        plt.savefig(file_path + '.png')
