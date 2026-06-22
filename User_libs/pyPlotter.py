import numpy as np
import matplotlib.pyplot as plt

class PlotTransformation():
    def __init__(self):
        self.Transforms = {'T': self.Trasform_RES_to_Temp}
        self.SensorsConfig = {
            'Pt100_default':  {'R0': 100.0,  'Rc': 0.0},
            'Pt100_cable_1':  {'R0': 100.0,  'Rc': 0.25},
            'Pt1000_stand_3': {'R0': 1000.0, 'Rc': 0.12}
        }

    def Trasform_RES_to_Temp(self, y_val, sensor_preset='Pt100_default'):
        if sensor_preset not in self.SensorsConfig:
            sensor_preset = 'Pt100_default'
        cfg = self.SensorsConfig[sensor_preset]
        return self._RTD_Pt_res_to_temp(y_val, R0=cfg['R0'], Rc=cfg['Rc'])

    @staticmethod
    def _RTD_Pt_res_to_temp(R, /, R0=100, Rc=0):
        a = 3.9083 * 10 ** -3
        b = -5.775 * 10 ** -7
        c = -4.183 * 10 ** -12

        scale = R0 / 100.0
        R_norm = R / scale
        Rc_norm = Rc / scale
        R0_base = 100.0

        if R_norm >= R0_base:
            d = a ** 2 - 4 * b * (R0_base - R_norm + Rc_norm) / R0_base
            if d < 0: return float('nan')
            t = (d ** 0.5 - a) / (2 * b)
            return t.real if isinstance(t, complex) else t
        else:
            t = (R_norm - Rc_norm - R0_base) / (a * R0_base)
            iter_count = 0
            while True:
                f_t = (c * t ** 4 - 100 * c * t ** 3 + b * t ** 2 + a * t + 1) * R0_base + Rc_norm - R_norm
                df_dt = (4 * c * t ** 3 - 300 * c * t ** 2 + 2 * b * t + a) * R0_base
                if df_dt == 0: return float('nan')
                delta = f_t / df_dt
                t -= delta
                iter_count += 1
                if abs(delta) < 0.0001: return t
                if iter_count > 20: return float('nan')

class Plotter():
    def __init__(self, raw_graph_lines, x_label='x', plot_name='Real-time Scan', pts=None):
        self.pts = pts
        self.colors = ['b', 'g', 'r', 'c', 'm', 'y', 'k']
        
        # Единый гибкий паспорт физических размерностей стенда
        self.UnitsPassport = {
            'CURR': 'А',
            'VOLT': 'В',
            'RES':  'Ом',
            'T':    '°C',
            'P':    'Па',
            'RATIO': 'безразмерно'
        }
        
        plt.ion()
        self.fig, self.base_ax = plt.subplots(figsize=(9, 5))
        self.base_ax.set_title(label=plot_name, fontname='Arial', fontsize=12)
        self.base_ax.set_xlabel(xlabel=x_label, fontname='Arial', fontsize=12)
        
        if self.pts and self.pts.get('x_pts', 0) > 0:
            self.x_step = self.pts['x_step']
            self.x_pts = self.pts['x_pts']
            self.base_ax.set_xlim([0, self.x_step * self.x_pts])
            
        self.xdata = []
        self.axes_pool = {}
        self.transformer = PlotTransformation()

        # Вызываем изолированный метод парсинга аргументов -g
        self.lines_config = self._parse_graph_arguments(raw_graph_lines)

    def _parse_graph_arguments(self, raw_graph_lines):
        parsed_config = {}
        
        for index, item in enumerate(raw_graph_lines):
            if '=' in item:
                source_key, v_channel_part = item.split('=', 1)
                device_prefix = source_key.split('.')[0]
                
                if ':' in v_channel_part:
                    v_short_name, preset_key = v_channel_part.split(':', 1)
                else:
                    v_short_name, preset_key = v_channel_part, 'Pt100_default'
                
                v_channel_name = f"{device_prefix}.{v_short_name}"
                v_magnitude_letter = ''.join([char for char in v_short_name if not char.isdigit()])
                
                transform_func = self.transformer.Transforms.get(v_magnitude_letter)
                display_label = v_channel_name
                unit_name = self.UnitsPassport.get(v_magnitude_letter, 'ед.')
            else:
                source_key, v_channel_name, preset_key = item, item, None
                transform_func = None
                display_label = item
                p_suffix = source_key.split('.')[-1]
                p_magnitude_letter = ''.join([char for char in p_suffix if not char.isdigit()])
                unit_name = self.UnitsPassport.get(p_magnitude_letter, 'ед.')

            color = self.colors[index % len(self.colors)]
            
            parsed_config[item] = {
                'source_key': source_key,
                'transform_func': transform_func,
                'preset_key': preset_key,
                'display_label': display_label,
                'unit': unit_name,
                'color': color,
                'ydata': [],
                'line_obj': None,
                'current_ax': None
            }
            
        return parsed_config

    def plot_routine(self, i, x, results):
        self.xdata.append(x)
        
        if self.pts and self.pts.get('x_pts', 0) > 0:
            if i + 1 > self.x_pts:
                self.xdata = self.xdata[1:]

        # Шаг 2. Вычисляем физические и виртуальные значения
        current_max_values = {}
        for item, cfg in self.lines_config.items():
            dev_part, key_part = cfg['source_key'].split('.', 1)
            dev_data = results.get(dev_part, {})
            raw_val = dev_data.get(key_part, float('nan'))
            
            if cfg['transform_func']:
                final_val = cfg['transform_func'](raw_val, cfg['preset_key'])
            else:
                final_val = raw_val
            
            cfg['ydata'].append(final_val)
            if self.pts and self.pts.get('x_pts', 0) > 0 and (i + 1 > self.x_pts):
                cfg['ydata'] = cfg['ydata'][1:]
                
            valid_data = [abs(y) for y in cfg['ydata'] if not np.isnan(y) and y != 0]
            current_max_values[item] = max(valid_data) if valid_data else 1.0

        # Шаг 3. Динамическая балансировка осей Y строго по физическому смыслу (размерности)
        assigned_axes_this_step = {}
        
        # Счётчики для каскадного смещения дополнительных шкал наружу
        left_axis_count = 0
        right_axis_count = 0
        
        # Списки физических величин для разделения по сторонам холста
        left_units = ['В', 'Ом', 'ед.']
        right_units = ['А', '°C', 'Па', 'безразмерно']
        
        # Пул для сбора линий, сидящих на каждой уникальной оси на текущем шаге
        axis_lines_map = {}

        for item, cfg in self.lines_config.items():
            max_val = current_max_values[item]
            raw_order = int(np.floor(np.log10(max_val))) if max_val > 0 else 0
            order_of_magnitude = raw_order if abs(raw_order) >= 3 else 0
            axis_signature = f"{cfg['unit']}_10^{order_of_magnitude}"
            
            if axis_signature not in assigned_axes_this_step:
                is_left_side = cfg['unit'] in left_units
                
                if is_left_side and left_axis_count == 0:
                    target_ax = self.base_ax
                    target_ax.get_yaxis().set_visible(True)
                    left_axis_count += 1
                else:
                    if axis_signature not in self.axes_pool:
                        target_ax = self.base_ax.twinx()
                        self.axes_pool[axis_signature] = target_ax
                    else:
                        target_ax = self.axes_pool[axis_signature]
                    
                    target_ax.get_yaxis().set_visible(True)
                    
                    if is_left_side:
                        target_ax.yaxis.set_label_position('left')
                        target_ax.yaxis.set_ticks_position('left')
                        target_ax.spines['left'].set_position(('outward', left_axis_count * 65))
                        left_axis_count += 1
                    else:
                        target_ax.yaxis.set_label_position('right')
                        target_ax.yaxis.set_ticks_position('right')
                        target_ax.spines['right'].set_position(('outward', right_axis_count * 65))
                        right_axis_count += 1

                assigned_axes_this_step[axis_signature] = target_ax
                axis_lines_map[axis_signature] = []
            else:
                target_ax = assigned_axes_this_step[axis_signature]

            if cfg['current_ax'] != target_ax:
                if cfg['line_obj'] is not None:
                    cfg['line_obj'].remove()
                cfg['line_obj'], = target_ax.plot([], [], c=cfg['color'], label=cfg['display_label'])
                cfg['current_ax'] = target_ax

            cfg['line_obj'].set_xdata(self.xdata)
            cfg['line_obj'].set_ydata(cfg['ydata'])
            
            # Сохраняем конфигурацию линии в пуле текущей оси для последующей подписи
            axis_lines_map[axis_signature].append(cfg)

        # Шаг 4. Настройка цветов и многокомпонентных подписей осей Y
        for axis_signature, target_ax in assigned_axes_this_step.items():
            associated_lines = axis_lines_map[axis_signature]
            
            # Извлекаем метаданные размерности
            base_unit = associated_lines[0]['unit']
            order_str = axis_signature.split('_')[-1]
            order_val = int(order_str.split('^')[-1])
            unit_label = f"{base_unit} (10^{order_val})" if order_val != 0 else base_unit

            if len(associated_lines) == 1:
                # Если линия одна: красим ось в цвет линии
                single_cfg = associated_lines[0]
                target_ax.set_ylabel(ylabel=unit_label, color=single_cfg['color'], fontname='Arial')
                target_ax.tick_params(axis='y', labelcolor=single_cfg['color'])
                target_ax.spines[target_ax.yaxis.get_label_position()].set_color(single_cfg['color'])
            else:
                # Если линий две и более: делаем ось нейтрально-чёрной с Multi-label
                labels_parts = []
                for cfg in associated_lines:
                    # Извлекаем чистое имя канала (например, VOLT1)
                    short_name = cfg['display_label'].split('.')[-1]
                    labels_parts.append(short_name)
                
                # Собираем чистую подпись без лишних буквенных кодов цветов
                combined_label = " | ".join(labels_parts) + f", {unit_label}"
                
                target_ax.set_ylabel(ylabel=combined_label, color='black', fontname='Arial', fontsize=9)
                target_ax.tick_params(axis='y', labelcolor='black')
                target_ax.spines[target_ax.yaxis.get_label_position()].set_color('black')

        for sig, ax_obj in self.axes_pool.items():
            if ax_obj not in assigned_axes_this_step.values():
                ax_obj.get_yaxis().set_visible(False)

        if self.pts and self.pts.get('x_pts', 0) > 0 and len(self.xdata) > 1:
            self.base_ax.set_xlim(min(self.xdata), max(self.xdata))

        for ax_obj in assigned_axes_this_step.values():
            ax_obj.relim()
            ax_obj.autoscale_view()

        all_handles = [cfg['line_obj'] for cfg in self.lines_config.values() if cfg['line_obj']]
        all_labels = [h.get_label() for h in all_handles]
        self.base_ax.legend(all_handles, all_labels, loc='upper left', fontsize='x-small')

        # Автоматически и безопасно подгоняем рамки живого окна под все оси Y
        self.fig.tight_layout()

        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

    def save_figure(self, file_path):
        plt.savefig(file_path + '.png')



