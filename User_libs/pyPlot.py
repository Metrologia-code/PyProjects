import os
import sys
import time
import numpy as np
import matplotlib.pyplot as plt

class Transformation():
    def __init__(self):
        # Привязываем физическую букву вычисляемой величины к конкретной функции
        self.Transforms = {'T': self.Trasform_RES_to_Temp}
        
        # Конфигурация констант для любых датчиков и процессов зашита внутри класса
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

        if R >= R0:
            d = a ** 2 - 4 * b * (R0 - R + Rc) / R0
            t = (d ** 0.5 - a) / (2 * b)
            return t
        else:
            t = (R - Rc - R0) / (a * R0)
            while True:
                f_t = (c * t ** 4 - 100 * c * t ** 3 + b * t ** 2 + a * t + 1) * R0 + Rc - R
                df_dt = (4 * c * t ** 3 - 300 * c * t ** 2 + 2 * b * t + a) * R0
                t -= f_t / df_dt
                if abs(f_t / df_dt) < 0.0001:
                    return t

class PlotterClass():
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
        self.transformer = Transformation()

        # Вызываем изолированный метод парсинга аргументов -g
        self.lines_config = self._parse_graph_arguments(raw_graph_lines)

    def _parse_graph_arguments(self, raw_graph_lines):
        # Внутренний метод: превращает сырой список строк -g в паспорт конфигурации линии
        parsed_config = {}
        
        for index, item in enumerate(raw_graph_lines):
            if '=' in item:
                # Распиливаем по знаку равенства
                source_key, v_channel_part = item.split('=', 1)
                
                # Автоматически вытаскиваем имя прибора из левой части (например, "TH1992B_1")
                device_prefix = source_key.split('.')[0]
                
                # Распиливаем виртуальную часть по двоеточию на короткое имя канала и ключ констант
                if ':' in v_channel_part:
                    v_short_name, preset_key = v_channel_part.split(':', 1)
                else:
                    v_short_name, preset_key = v_channel_part, 'Pt100_default'
                
                # Склеиваем имя прибора и короткое виртуальное имя, данное пользователем
                v_channel_name = f"{device_prefix}.{v_short_name}"
                
                # Извлекаем суффикс вычисляемой величины (из T2 получаем чистую букву T)
                v_magnitude_letter = ''.join([char for char in v_short_name if not char.isdigit()])
                
                transform_func = self.transformer.Transforms.get(v_magnitude_letter)
                display_label = v_channel_name
                # Вытаскиваем размерность по букве виртуальной величины из паспорта
                unit_name = self.UnitsPassport.get(v_magnitude_letter, 'ед.')
            else:
                source_key, v_channel_name, preset_key = item, item, None
                transform_func = None
                display_label = item
                # Извлекаем суффикс физической величины (например, из TH1992B_1.CURR1 вытащит CURR)
                p_suffix = source_key.split('.')[-1]
                p_magnitude_letter = ''.join([char for char in p_suffix if not char.isdigit()])
                # Вытаскиваем размерность физического канала из паспорта
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
            raw_val = results.get(cfg['source_key'], float('nan'))
            
            # Если задана функция, прокидываем туда сырое число и сохраненный ключ констант
            if cfg['transform_func']:
                final_val = cfg['transform_func'](raw_val, cfg['preset_key'])
            else:
                final_val = raw_val
            
            cfg['ydata'].append(final_val)
            if self.pts and self.pts.get('x_pts', 0) > 0 and (i + 1 > self.x_pts):
                cfg['ydata'] = cfg['ydata'][1:]
                
            valid_data = [abs(y) for y in cfg['ydata'] if not np.isnan(y) and y != 0]
            current_max_values[item] = max(valid_data) if valid_data else 1.0

        # Шаг 3. Динамическая живая перегруппировка и расселение осей Y
        assigned_axes_this_step = {}
        axis_index = 0
        
        for item, cfg in self.lines_config.items():
            max_val = current_max_values[item]
            order_of_magnitude = int(np.floor(np.log10(max_val))) if max_val > 0 else 0
            axis_signature = f"{cfg['unit']}_10^{order_of_magnitude}"
            
            if axis_signature not in assigned_axes_this_step:
                if axis_index == 0:
                    target_ax = self.base_ax
                    target_ax.get_yaxis().set_visible(True)
                else:
                    if axis_signature not in self.axes_pool:
                        target_ax = self.base_ax.twinx()
                        self.axes_pool[axis_signature] = target_ax
                    else:
                        target_ax = self.axes_pool[axis_signature]
                    
                    target_ax.get_yaxis().set_visible(True)
                    if axis_index > 1:
                        target_ax.spines['right'].set_position(('outward', (axis_index - 1) * 45))

                target_ax.set_ylabel(ylabel=f"{cfg['unit']} (10^{order_of_magnitude})", color=cfg['color'], fontname='Arial')
                target_ax.tick_params(axis='y', labelcolor=cfg['color'])
                
                assigned_axes_this_step[axis_signature] = target_ax
                axis_index += 1
            else:
                target_ax = assigned_axes_this_step[axis_signature]

            if cfg['current_ax'] != target_ax:
                if cfg['line_obj'] is not None:
                    cfg['line_obj'].remove()
                
                # Привязываем к линии её красивое виртуальное или физическое имя для легенды
                cfg['line_obj'], = target_ax.plot([], [], c=cfg['color'], label=cfg['display_label'])
                cfg['current_ax'] = target_ax

            cfg['line_obj'].set_xdata(self.xdata)
            cfg['line_obj'].set_ydata(cfg['ydata'])

        for sig, ax_obj in self.axes_pool.items():
            if ax_obj not in assigned_axes_this_step.values():
                ax_obj.get_yaxis().set_visible(False)

        if self.pts and self.pts.get('x_pts', 0) > 0 and len(self.xdata) > 1:
            self.base_ax.set_xlim(min(self.xdata), max(self.xdata))

        for ax_obj in assigned_axes_this_step.values():
            ax_obj.relim()
            ax_obj.autoscale_view()

        all_handles, all_labels = [], []
        for cfg in self.lines_config.values():
            if cfg['line_obj']:
                all_handles.append(cfg['line_obj'])
                all_labels.append(cfg['line_obj'].get_label())
        self.base_ax.legend(all_handles, all_labels, loc='upper left', fontsize='x-small')

        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

    def save_figure(self, file_path):
        plt.savefig(file_path + '.png')
