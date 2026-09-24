import sys
import time
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MaxNLocator, FixedLocator

# Глобальный паспорт физических размерностей измерительного комплекса
# Используется при разборе старых строковых аргументов и при формировании подписей осей Y
UNITS = {'CURR': 'I', 'VOLT': 'V', 'RES': 'Ohm'}

# Значения по умолчанию для параметров графика
xLabel, plotName, plotPoints = 'x', 'Test', 100


class PlotConfig:
    """
    Настройки форматирования окна и полотен (subplots).

    Собраны в одном месте, чтобы в будущем их можно было переопределять
    ключами запуска, передавая их в конструктор: PlotConfig(**overrides).
    """

    def __init__(self, **overrides):
        # Размер окна (ширина, минимальная высота) в дюймах
        self.figure_size = (9, 5)
        # Высота одного полотна в дюймах (используется, если полотен больше одного)
        self.canvas_height = 3.0
        # Раскладка полотен: сейчас всегда один столбец (полотна вертикально)
        self.n_cols = 1
        # Механизм автоматической раскладки и отступы между полотнами
        # ('constrained' резервирует место под подписи, заголовки и легенды сам)
        self.layout_engine = 'constrained'
        self.h_pad = 0.35
        self.w_pad = 0.25
        self.share_x = True
        # Палитра линий
        self.colors = ['b', 'r', 'g', 'm', 'c', 'k']
        # Отступ между соседними осями Y в долях оси (axes-fraction)
        self.y_axis_spacing = 0.09
        # Запас ширины окна на каждую дополнительную ось Y (дюймы)
        self.figure_width_step = 1.2
        # Минимальный интервал между перерисовками (сек). Данные обновляются чаще,
        # экран — не чаще этого интервала. Значение <= 0 означает рисовать каждый кадр
        self.render_period = 0.2
        # Замораживать раскладку после первого расчёта (пересчёт только при изменениях)
        self.freeze_layout = True
        # Максимальное количество тиков на осях
        self.max_y_ticks = 12
        self.max_x_ticks = 18
        # Размеры шрифтов
        self.font_title = 12
        self.font_canvas_title = 11
        self.font_label = 12
        self.font_tick = 10
        self.font_legend = 'x-small'
        # Расположение легенды на полотне
        self.legend_loc = 'upper left'
        # Делить линии полотна на левую/правую половины осей Y
        self.split_left_right = True

        for key, value in overrides.items():
            setattr(self, key, value)

    # Допустимые для ключа -pl габаритные настройки: ключ -> (атрибут, индекс в кортеже, тип)
    CLI_DIMENSIONS = {
        'width': ('figure_size', 0, float),
        'height': ('figure_size', 1, float),
        'canvas_height': ('canvas_height', None, float),
        'n_cols': ('n_cols', None, int),
        'figure_width_step': ('figure_width_step', None, float),
    }

    @classmethod
    def from_cli(cls, options):
        ''' Собирает PlotConfig из списка строк 'key=value' аргумента -pl.
            Разрешены только габаритные настройки (CLI_DIMENSIONS). '''
        overrides = {}
        for option in options:
            if '=' not in option:
                cls._cli_error(f"Настройка графика '{option}' должна быть в формате key=value")
            key, value = option.split('=', 1)
            key, value = key.strip(), value.strip()
            if key not in cls.CLI_DIMENSIONS:
                allowed = ', '.join(cls.CLI_DIMENSIONS.keys())
                cls._cli_error(f"Неизвестная настройка графика '{key}'. Доступны: {allowed}")

            attribute, index, converter = cls.CLI_DIMENSIONS[key]
            try:
                parsed = converter(value)
            except ValueError:
                cls._cli_error(f"Не удалось преобразовать значение '{value}' настройки '{key}'")

            if attribute == 'figure_size':
                # figure_size - кортеж: берём значения по умолчанию и заменяем одну компоненту
                current = overrides.get('figure_size', cls().figure_size)
                new_size = list(current)
                new_size[index] = parsed
                overrides['figure_size'] = tuple(new_size)
            else:
                overrides[attribute] = parsed
        return cls(**overrides)

    @staticmethod
    def _cli_error(message):
        print(f"\n[ОШИБКА]: {message}")
        sys.exit(1)


class Plotter:
    """
    Класс Plotter предназначен для отрисовки графиков в реальном времени на основе данных с измерительных приборов.

    Формат аргументов
    В конструктор передается список описаний кривых. Каждое описание - словарь:
        {'device', 'key', 'channel', 'value', 'unit', 'canvas'}.
    Поле 'canvas' задает имя полотна (subplot) внутри окна. Окно всегда одно,
    полотна располагаются вертикально одно под другим.
    Для обратной совместимости допускаются строки вида 'ИмяПрибора.Параметр'.

    Параметры конструктора
    - args: список описаний кривых.
    - x_label: подпись оси X, по умолчанию 'x'.
    - plot_name: заголовок полотна по умолчанию, по умолчанию 'Test'.
    - x_pts: длина скользящего окна по оси X, по умолчанию 100.
    - config: PlotConfig с настройками форматирования.

    Распределение по осям и цвета
    Кривые каждого полотна делятся пополам: первая половина выводится на левую ось Y, вторая — на правую.
    Внутри одной стороны соседние оси Y раздвигаются на долю оси (config.y_axis_spacing), чтобы не перекрываться.
    Цвет линии задается порядковым номером в общем списке args и берется из палитры config.colors.

    Поведение при отсутствии данных
    Если в словаре results нет прибора или параметра, в данные подставляется NaN. Линия в этой точке разрывается.

    Метод plot_routine(i, x, results)
    Принимает номер итерации, значение оси X и словарь вида {'ИмяПрибора': {'Параметр': значение, ...}, ...}.

    Методы save_figure и keep_open
    - save_figure(file_path): сохраняет текущий график в PNG по пути file_path + '.png'.
    - keep_open(): удерживает окно открытым после завершения программы.
    """

    def __init__(self, args, x_label=xLabel, plot_name=plotName, x_pts=plotPoints, config=None):
        self.config = config if config is not None else PlotConfig()
        self.x_pts = int(x_pts)
        self.x_label = x_label
        self.plot_name = plot_name
        self.lines = {}
        self.line_order = []
        self.canvases = {}
        self.canvas_order = []
        self.canvas_axes = {}
        self.xdata = []

        #1. Нормализуем описания кривых и группируем их по полотнам
        specs = [self._normalize_item(item, plot_name) for item in args]
        for spec in specs:
            if spec['canvas'] not in self.canvases:
                self.canvases[spec['canvas']] = []
                self.canvas_order.append(spec['canvas'])
            self.canvases[spec['canvas']].append(spec)
        if not self.canvas_order:
            self.canvas_order.append(plot_name)
            self.canvases[plot_name] = []

        #2. Инициализация окна с полотнами (один столбец, полотна вертикально).
        #   Ширину окна заранее увеличиваем под дополнительные оси Y, а место под
        #   подписи/заголовки резервирует layout-движок 'constrained'
        n_canvases = len(self.canvas_order)
        height = max(self.config.figure_size[1], self.config.canvas_height * n_canvases)
        max_extra_left, max_extra_right = self._count_extra_axes()
        width = self.config.figure_size[0] + (max_extra_left + max_extra_right) * self.config.figure_width_step
        plt.ion()
        self.fig, axes = plt.subplots(
            n_canvases, self.config.n_cols,
            figsize=(width, height),
            sharex=self.config.share_x, squeeze=False,
            layout=self.config.layout_engine
        )
        engine = self.fig.get_layout_engine()
        if engine is not None:
            engine.set(h_pad=self.config.h_pad, w_pad=self.config.w_pad)
        for row, canvas in enumerate(self.canvas_order):
            base_ax = axes[row][0]
            self.canvas_axes[canvas] = base_ax
            base_ax.set_title(label=canvas, fontname='Arial', fontsize=self.config.font_canvas_title)
            base_ax.tick_params(axis='x', rotation=65)
            base_ax.xaxis.set_major_formatter(FuncFormatter(lambda x, pos: f"{x:.1f}"))
        # Подпись оси X показываем только на нижнем полотне
        axes[-1][0].set_xlabel(xlabel=self.x_label, fontname='Arial', fontsize=self.config.font_label)

        #3. Готовим конфигурацию каждой линии (деление на левую/правую половины - внутри полотна)
        position_counters = {}
        for idx, spec in enumerate(specs):
            canvas_specs = self.canvases[spec['canvas']]
            position = position_counters.get(spec['canvas'], 0)
            position_counters[spec['canvas']] = position + 1
            left_limit = (len(canvas_specs) + 1) // 2
            is_left = (position < left_limit) if self.config.split_left_right else True
            side_index = position if is_left else position - left_limit
            line_color = self.config.colors[idx % len(self.config.colors)]

            self.lines[spec['id']] = {
                'source': spec['id'],
                'device': spec['device'],
                'key': spec['key'],
                'label': spec['label'],
                'unit': spec['unit'],
                'color': line_color,
                'ydata': [],
                'line_obj': None,
                'is_left': is_left,
                'side_index': side_index,
                'order': 0,
                'y_max': 0.0,
                'canvas': spec['canvas'],
                'base_ax': self.canvas_axes[spec['canvas']],
            }
            self.line_order.append(spec['id'])

        #4. Оси и легенды создаём один раз (а не в измерительном цикле)
        for line_id in self.line_order:
            self._init_axis(self.lines[line_id])
        for canvas in self.canvas_order:
            base_ax = self.canvas_axes[canvas]
            handles = [self.lines[spec['id']]['line_obj'] for spec in self.canvases[canvas]
                       if self.lines[spec['id']]['line_obj']]
            labels = [self.lines[spec['id']]['label'] for spec in self.canvases[canvas]
                      if self.lines[spec['id']]['line_obj']]
            if handles:
                base_ax.legend(handles, labels, loc=self.config.legend_loc, fontsize=self.config.font_legend)

        #5. Один расчёт раскладки и её заморозка; дальше рендер дешёвый.
        #   Перед расчётом резервируем место под самую длинную подпись оси Y
        #   (с запасом под экспоненту), чтобы при смене порядка не пересчитывать раскладку
        self._last_render_time = float('-inf')
        self._reserve_ylabel_space()
        self._solve_layout()
        self._restore_ylabels()

    def _set_ylabel(self, cfg, text):
        ax = cfg['line_obj'].axes
        ax.set_ylabel(ylabel=text, fontname='Arial', fontsize=self.config.font_tick)
        ax.yaxis.label.set_color(cfg['line_obj'].get_color())

    def _reserve_ylabel_space(self):
        # Резервируем ширину под подпись с любым возможным порядком (1e-99)
        for line_id in self.line_order:
            cfg = self.lines[line_id]
            if cfg['line_obj'] is not None:
                self._set_ylabel(cfg, self._axis_label(cfg, cfg['order']) + ' (1e-99)')

    def _restore_ylabels(self):
        for line_id in self.line_order:
            cfg = self.lines[line_id]
            if cfg['line_obj'] is not None:
                self._set_ylabel(cfg, self._axis_label(cfg, cfg['order']))

    def _count_extra_axes(self):
        # Максимальное число дополнительных (сверх одной) осей Y слева и справа
        # по всем полотнам. Нужно для запаса ширины окна.
        max_extra_left = 0
        max_extra_right = 0
        for canvas_specs in self.canvases.values():
            count = len(canvas_specs)
            if count == 0:
                continue
            if self.config.split_left_right:
                left_count = (count + 1) // 2
            else:
                left_count = count
            right_count = count - left_count
            max_extra_left = max(max_extra_left, max(0, left_count - 1))
            max_extra_right = max(max_extra_right, max(0, right_count - 1))
        return max_extra_left, max_extra_right

    #---НОРМАЛИЗАЦИЯ ОПИСАНИЙ КРИВЫХ---
    def _normalize_item(self, item, default_canvas):
        if isinstance(item, dict):
            device = item.get('device', '')
            key = item.get('key', '')
            value = item.get('value', key)
            channel = item.get('channel')
            unit = item.get('unit', '') or self._unit_from_key(value)
            canvas = item.get('canvas') or default_canvas
            label = item.get('label') or self._make_label(device, channel, value)
        else:
            #Обратная совместимость: строка 'ИмяПрибора.Параметр'
            source = str(item)
            device, key = source.split('.', 1)
            channel = ''.join(ch for ch in key if ch.isdigit()) or None
            value = ''.join(ch for ch in key if not ch.isdigit()) or key
            unit = self._unit_from_key(value)
            canvas = default_canvas
            label = source

        return {
            'id': f"{device}.{key}",
            'device': device,
            'key': key,
            'value': value,
            'unit': unit,
            'channel': channel,
            'canvas': canvas,
            'label': label,
        }

    @staticmethod
    def _make_label(device, channel, value):
        name = f"{device}.ch{channel}" if channel else device
        return f"{name}={value}"

    @staticmethod
    def _unit_from_key(value):
        legacy_units = {'I': 'A', 'V': 'V', 'Ohm': 'Ohm'}
        for token, unit in UNITS.items():
            if token in value:
                return legacy_units.get(unit, unit)
        return ''

    def _calc_order(self, max_abs):
        # Порядок оси (декада множителя 1eN) по максимуму окна; меняется только если
        # максимум выходит за пределы [1e-3, 1e3]
        if max_abs <= 0:
            return 0, 0.0
        raw_order = int(np.floor(np.log10(max_abs)))
        return (raw_order if abs(raw_order) >= 3 else 0), max_abs

    def _axis_label(self, cfg, order):
        unit = cfg['unit']
        if order != 0:
            return f"{cfg['label']}, {unit} (1e{order})" if unit else f"{cfg['label']} (1e{order})"
        return f"{cfg['label']}, {unit}" if unit else cfg['label']

    def _init_axis(self, cfg):
        # Первая линия полотна использует базовую ось, остальные - twinx с отступом
        canvas_specs = self.canvases[cfg['canvas']]
        if canvas_specs and canvas_specs[0]['id'] == cfg['source']:
            target_ax = cfg['base_ax']
        else:
            target_ax = cfg['base_ax'].twinx()
            side = 'left' if cfg['is_left'] else 'right'
            target_ax.yaxis.set_label_position(side)
            target_ax.yaxis.set_ticks_position(side)
            # Сдвиг оси в долях оси (axes-fraction): не зависит от DPI и размера окна
            if side == 'right':
                spine_pos = ('axes', 1.0 + cfg['side_index'] * self.config.y_axis_spacing)
            else:
                spine_pos = ('axes', -cfg['side_index'] * self.config.y_axis_spacing)
            target_ax.spines[side].set_position(spine_pos)

        cfg['line_obj'], = target_ax.plot(self.xdata, cfg['ydata'], label=cfg['label'], color=cfg['color'])

        # Максимум окна и порядок оси вычисляются из уже накопленных точек
        cfg['y_max'] = 0.0
        for y in cfg['ydata']:
            if not np.isnan(y):
                a = abs(y)
                if a > cfg['y_max']:
                    cfg['y_max'] = a
        cfg['order'], _ = self._calc_order(cfg['y_max'])

        # Делит значения на порядок оси, чтобы подписи были читаемыми, и добавляет множитель (1eN) к подписи оси.
        # Форматтер читает cfg['order'] "на лету" — при смене порядка переустанавливать его не требуется
        target_ax.yaxis.set_major_formatter(
            FuncFormatter(lambda y, pos:
                f"{y/(10**cfg['order']):.3g}" if cfg['order'] != 0 else f"{y:.3g}")
        )

        target_ax.set_ylabel(ylabel=self._axis_label(cfg, cfg['order']), fontname='Arial',
                             fontsize=self.config.font_tick)
        target_ax.yaxis.label.set_color(cfg['line_obj'].get_color())
        target_ax.tick_params(axis='y', labelcolor=cfg['line_obj'].get_color(), labelsize=9)
        target_ax.spines[target_ax.yaxis.get_label_position()].set_color(cfg['line_obj'].get_color())
        target_ax.yaxis.set_major_locator(MaxNLocator(nbins=self.config.max_y_ticks, prune=None))

    def plot_routine(self, i, x, results):
        self.xdata.append(x)
        if len(self.xdata) > self.x_pts:
            self.xdata = self.xdata[1:]

        #1. Обновляем данные и определяем порядок осей (дёшево, без отрисовки)
        for line_id in self.line_order:
            cfg = self.lines[line_id]
            dev_data = results.get(cfg['device'], {})
            raw_val = dev_data.get(cfg['key'], float('nan'))
            if isinstance(raw_val, str):
                try:
                    raw_val = float(raw_val)
                except ValueError:
                    raw_val = float('nan')

            cfg['ydata'].append(raw_val)

            # Инкрементальное ведение максимума окна (O(1) на шаг);
            # полный пересчет по окну — только когда максимум покидает окно (редко)
            if len(cfg['ydata']) > self.x_pts:
                old_head = cfg['ydata'][0]
                cfg['ydata'] = cfg['ydata'][1:]
                if not np.isnan(old_head) and abs(old_head) >= cfg['y_max']:
                    cfg['y_max'] = 0.0
                    for y in cfg['ydata']:
                        if not np.isnan(y):
                            a = abs(y)
                            if a > cfg['y_max']:
                                cfg['y_max'] = a
            raw_abs = abs(raw_val) if not np.isnan(raw_val) else 0.0
            if raw_abs > cfg['y_max']:
                cfg['y_max'] = raw_abs

            if cfg['line_obj'] is None:
                self._init_axis(cfg)

            # Автоподбор порядка оси по текущему максимуму с гистерезисом (мертвая зона x10):
            # порядок меняется только когда максимум вышел за границы соседней декады
            new_order, max_abs = self._calc_order(cfg['y_max'])
            if max_abs > 0 and new_order != cfg['order']:
                cur_pow = 10 ** cfg['order'] if cfg['order'] != 0 else 1.0
                if max_abs >= cur_pow * 10 or max_abs <= cur_pow * 0.1:
                    cfg['order'] = new_order
                    # Место под подпись любого порядка зарезервировано заранее,
                    # поэтому раскладку пересчитывать не нужно
                    self._set_ylabel(cfg, self._axis_label(cfg, cfg['order']))

        #2. Отрисовку выполняем не чаще render_period, чтобы не тормозить цикл измерения
        now = time.perf_counter()
        if now - self._last_render_time < self.config.render_period:
            return
        self._last_render_time = now
        self._render()

    def _render(self):
        # Переносим накопленные данные в линии и обновляем их границы
        for line_id in self.line_order:
            cfg = self.lines[line_id]
            if cfg['line_obj'] is None:
                continue
            cfg['line_obj'].set_xdata(self.xdata)
            cfg['line_obj'].set_ydata(cfg['ydata'])
            ax_obj = cfg['line_obj'].axes
            # relim пересчитывает границы данных, autoscale_view применяет их к осям — нужны оба вызова
            ax_obj.relim()
            ax_obj.autoscale_view()

        self._update_x_axis()

        self.fig.canvas.draw_idle()
        self.fig.canvas.flush_events()

    def _update_x_axis(self):
        # Прореживание тиков оси X с равномерным распределением
        if len(self.xdata) <= self.config.max_x_ticks:
            tick_data = self.xdata
        else:
            indices = np.linspace(0, len(self.xdata) - 1, self.config.max_x_ticks, dtype=int)
            tick_data = [self.xdata[idx] for idx in indices]

        for canvas in self.canvas_order:
            base_ax = self.canvas_axes[canvas]
            # FixedLocator фиксирует тики строго в заданных позициях, иначе matplotlib добавит свои
            base_ax.xaxis.set_major_locator(FixedLocator(tick_data))
            # После заполнения окна фиксируем диапазон X, чтобы autoscale_view не растягивал ось за пределы данных
            if len(self.xdata) >= self.x_pts:
                base_ax.set_xlim(self.xdata[0], self.xdata[-1])

    def _solve_layout(self):
        # Первый расчёт автоматической раскладки; при freeze_layout движок затем выключается,
        # чтобы не решать задачу раскладки на каждом кадре
        if not self.config.freeze_layout:
            return
        self.fig.set_layout_engine(self.config.layout_engine)
        self.fig.canvas.draw()
        self.fig.set_layout_engine('none')

    def save_figure(self, file_path):
        plt.savefig(file_path + '.png')

    def keep_open(self):
        # Сначала выключаем интерактивный режим, потом show — иначе окно закроется сразу после выхода из программы
        plt.ioff()
        plt.show()
