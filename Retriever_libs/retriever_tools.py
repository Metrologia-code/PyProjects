

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
        
    def Manual_sweep_prep(self, parameters):

        #накопитель ошибок
        feedback = []

        channel, mode, awg = 1, 'VOLT', 'FIX'

        #проверяем режим источника и меняем на напряжение, если необходимо
        source_mode = self.tonghui.query(f':SOUR{channel}:FUNC:MODE?')
        if source_mode != mode:
            self.tonghui.write(f':SOUR{channel}:FUNC:MODE ' + mode), time.sleep(0.2)
            source_mode = self.tonghui.query(f':SOUR{channel}:FUNC:MODE?')
            if source_mode == mode:
                print('Режим источника изменен на ' + source_mode)
            else:
                print(f':SOUR{channel}:FUNC:MODE?')
                feedback.append(1)
        else:
            print('Режим источника - ' + source_mode)
        
        #проверяем форму сигнала источника и меняем на DC, если необходимо
        volt_mode = self.tonghui.query(f':SOUR{channel}:VOLT:MODE?')
        if volt_mode != awg:
            self.tonghui.write(f':SOUR{channel}:VOLT:MODE ' + awg), time.sleep(0.2)
            volt_mode = self.tonghui.query(f':SOUR{channel}:VOLT:MODE?')
            if volt_mode == awg:
                print('Форма сигнала источника изменена на ' + volt_mode)
            else:
                print(f':SOUR{channel}:VOLT:MODE?')
                feedback.append(1)
        else:
            print('Форма сигнала источника - ' + volt_mode)
        
        time.sleep(0.1)
        I_limit = parameters['I_limit'].get()
        set_I_limit = f':SENS{channel}:CURR:PROT:LEV {I_limit}'
        self.tonghui.write(set_I_limit), time.sleep(0.2)
        if float(self.tonghui.query(f':SENS{channel}:CURR:PROT:LEV?')) != float(I_limit):
            print(f':SENS{channel}:CURR:PROT:LEV?')
            feedback.append(1)

        time.sleep(0.1)
        I_rng_AUTO = parameters['I_rng_AUTO'].get()
        set_I_range_mode = f':SENS{channel}:CURR:RANG:AUTO {I_rng_AUTO}'
        self.tonghui.write(set_I_range_mode), time.sleep(0.2)
        if self.tonghui.query(f':SENS{channel}:CURR:RANG:AUTO?') != I_rng_AUTO:
            print(f':SENS{channel}:CURR:RANG:AUTO?')
            feedback.append(1)

        time.sleep(0.1)
        Aperture = parameters['Aperture'].get()
        set_aperture = f':SENS{channel}:VOLT:APER {Aperture}'
        self.tonghui.write(set_aperture), time.sleep(0.2)
        if float(self.tonghui.query(f':SENS{channel}:VOLT:APER?')) != float(Aperture):
            print(f':SENS{channel}:VOLT:APER?')
            feedback.append(1)

        time.sleep(0.1)
        Source_start = parameters['Source start'].get()
        set_output = f':SOUR{channel}:VOLT {Source_start}'
        self.tonghui.write(set_output), time.sleep(0.2)
        if float(self.tonghui.query(f':SOUR{channel}:VOLT?')) != float(Source_start):
            print(f':SOUR{channel}:VOLT?')
            feedback.append(1)

        time.sleep(0.1)
        measurement_points = int(parameters['Meas. p-ts'].get())
        set_number_of_points = f':TRIG{channel}:ACQ:COUN {measurement_points}'
        self.tonghui.write(set_number_of_points), time.sleep(0.2)
        if int(self.tonghui.query(f':TRIG{channel}:ACQ:COUN?')) != measurement_points:
            print(f':TRIG{channel}:ACQ:COUN?')
            feedback.append(1)

        time.sleep(0.1)
        self.sweep_data_format = 'VOLTage,CURR,RES,TIME'
        set_format = f':FORM:ELEM:SENS {self.sweep_data_format}'
        self.tonghui.write(set_format), time.sleep(0.2)
        if self.tonghui.query(':FORM:ELEM:SENS?') != self.sweep_data_format:
            print(':FORM:ELEM:SENS?')
            feedback.append(1)
        
        return len(feedback) < 1
        

    def Manual_sweep_stepbystep(self, gui, name, if_plot_clear, root, ):

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
        aperture = float(parameters['Aperture'].get())
        measurement_points = int(parameters['Meas. p-ts'].get())
        
        T_operation = float(parameters['T operation'].get())
        T_after_step_sleep = float(parameters['Step sleep'].get())
        T_trigger_expected = measurement_points * aperture + self.trigger_delta
        
        data = {'V':[], 'I':[]}
        
        if T_operation > T_after_step_sleep + T_trigger_expected + self.processing_delta:
            for n in range(source_points):
                
                t1 = time.perf_counter()
                
                #если мы в первой точке свипа, то шаг не добавляем
                if n != 0:
                    #устанавливаем следующее значение источника
                    source_value = source_start + source_step * n
                    set_source_output_value_command = f':SOUR1:VOLT {source_value}'
                    self.tonghui.write(set_source_output_value_command)
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
                        got_data = self.tonghui.query(':MEAS? (@1)').split(',')
                    except Exception as e:
                        print(e)
                        time.sleep(1)
                        break
                    else:
                        data_points['V'].append(float(got_data[0]))
                        data_points['I'].append(float(got_data[1]))
                
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
            
        return data