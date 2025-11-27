import time
import numpy as np

class Data():

    def __init__(self, ):
        
        self.output = 'placeholder'
        self.values = {}
        
class Sweeper():
    
    def __init__(self, ):
        
        self.output = 'placeholder'
        self.values = {}
        
        #параметры измерения триггером
        self.trigger_delta = 0.1
        self.processing_delta = 0.4
        
        #словарь, который соотносит имя параметра в .ini файле с названием элементов интерфейса
        #список в retriever_widgets.py использует такие же имена
        self.sweep_parameter_names = {  
                    'source_output_start_value'    : 'Source start',
                    'source_output_stop_value'     : 'Source stop',
                    'number_of_sweep_points'       : 'Source p-ts',
                    'current_value_limit'          : 'I_limit',
                    'current_measurement_range_isauto' : 'I_rng_AUTO',
                    'current_measurement_range'    : 'I_range',
                    'initial_establishing_sleep'   : 'Init. sleep',
                    'source_output_step_sleep'     : 'Step sleep',
                    'n_of_measurement_points'      : 'Meas. p-ts',
                    'operation_time'               : 'T operation',
                 }
        

    def Manual_sweep_stepbystep(self, DEVICE, gui, name, if_plot_clear, root, ):

        ##############################################################################
        #если выбрана опция очищать, то удаляем все предыдущие линии
        if if_plot_clear == 1:
            for line_name in gui.raw_lines:
                gui.raw_lines[line_name].remove()
            gui.raw_lines = {}

        #создаем список цветов существующих линий
        colors = []
        if len(gui.raw_lines) > 0:
            for line_name in gui.raw_lines:
                colors.append(gui.raw_lines[line_name].get_color())
        
        #выбираем цвет новой линии
        color_collection = ['b', 'k', 'r', 'm', 'g', 'c',]
        new_color = ''
        for c in color_collection:
            if c not in colors:
                new_color = c
                break
        if len(new_color) == 0:
            new_color = 'b'

        #создаем новую линию
        line_options = {'linestyle':'solid', 'linewidth':0.3, 'marker':'.', 'markersize':1, 'c':new_color}
        gui.raw_lines[name], = gui.ax.plot([], [], **line_options, label=name)

        gui.ax.legend(loc='best', fontsize='x-small', markerscale=2.5)
        ##############################################################################
        
        parameters = gui.msweep_input_vars
        
        source_start = float(parameters['Source start'].get())
        source_stop = float(parameters['Source stop'].get())
        source_points = int(parameters['Source p-ts'].get())
        source_step = (source_stop-source_start)/(source_points-1)
        measurement_points = int(parameters['Meas. p-ts'].get())

        initial_sleep = float(parameters['Init. sleep'].get())
        
        T_operation = float(parameters['T operation'].get())
        T_after_step_sleep = float(parameters['Step sleep'].get())
        #******************НУЖНО СЧИТАТЬ РЕАЛЬНУЮ АПЕРТУРУ!!!111111******************
        T_trigger_expected = measurement_points * 0.02 + self.trigger_delta

        ch = DEVICE.ChannelsList[0]

        #устанавливаем значение первой точки сканирования
        if not DEVICE.SetParameter('SOURCE-value', str(source_start), mode='VOLT', ch=ch):
            return False
        #и ждём, пока сигнал установится...
        time.sleep(initial_sleep)
        
        data = {'V':[], 'I':[]}
        
        if T_operation > T_after_step_sleep + T_trigger_expected + self.processing_delta:
            for n in range(source_points):
                
                t1 = time.perf_counter()
                
                #если мы в первой точке свипа, то шаг не добавляем
                if n != 0:
                    #устанавливаем следующее значение источника
                    source_value = source_start + source_step * n
                    DEVICE.tonghui.write(f':SOUR{ch}:VOLT {source_value}')
                    #step sleep
                    time.sleep(T_after_step_sleep)
                
                #запускаем триггер
                #self.tonghui.write(':INIT:IMM:ACQ (@1)')
                #time.sleep(T_trigger_expected)
                
                #забираем буфер прибора
                #got_data = self.tonghui.query(':SENS1:DATA?') #STAR,201
                #print(got_data)
                #if len(got_data) > 1:
                
                '''data_list = list(map(float, got_data.split(',')))
                data_lines = []
                line_length = len(self.sweep_data_format.split(','))
                for i in range(0, len(data_list), line_length):
                    data_lines.append(data_list[i:i + line_length])
                #print(data_lines)
                data_points = {'V':[], 'I':[]}
                for line in data_lines:
                    data_points['V'].append(line[0])
                    data_points['I'].append(line[1])
                    #results['T'].append(data[2])'''

                got_data = ''
                data_points = {'V':[], 'I':[]}
                for m in range(measurement_points):
                    try:
                        #got_data = DEVICE.tonghui.query(f':MEAS? (@{ch})').split(',')
                        got_data = DEVICE.SingleMeasure()
                    except Exception as e:
                        print(e)
                        time.sleep(1)
                        break
                    else:
                        V_name, I_name = f'VOLTage{ch}', f'CURR{ch}'
                        data_points['V'].append(float(got_data[V_name]))
                        data_points['I'].append(float(got_data[I_name]))
                
                if len(data_points['V']) > 1:
                
                    #обработка
                    V_mean, V_deviation = np.mean(data_points['V']), np.std(data_points['V'])
                    I_mean, I_deviation = np.mean(data_points['I']), np.std(data_points['I'])
                    data['V'].append(V_mean), data['I'].append(I_mean)
    
                    #плот шага
                    #подставляем значения данных в оси
                    gui.raw_lines[name].set_xdata(data['V'])
                    gui.raw_lines[name].set_ydata(data['I'])
                    #выводим график
                    gui.ax.relim(), gui.ax.autoscale_view()
                    gui.canvas.draw()
                    #обновляем интерфейс, чтобы обновился плот
                    root.update()
                    
                    t2 = time.perf_counter()
                    T_remainder = T_operation - (t2 - t1)
                    try:
                        time.sleep(T_remainder)
                    except:
                        print_t = f' _ Время операции вревысило заданное {T_remainder:.4f}!'
                    else:
                        print_t = f' _ T_remainder = {T_remainder:.4f} s'
                    finally:
                        print(f'{V_mean:.4e} +-{V_deviation:.1e} : {I_mean:.4e} +-{I_deviation:.1e}' + print_t)
                else:
                    print('Пусто, точку пропускаем')
        else:
            print('Заданное время операции T_operation слишком малое!')

        #gui.ax.relim(), gui.ax.autoscale_view()
        gui.ax.legend(loc='best', fontsize='x-small', markerscale=2.5)
        gui.canvas.draw_idle()

        if 'TH1992B' in DEVICE.Name:
            DEVICE.ChannelsTurnOff()
        
        return data

    