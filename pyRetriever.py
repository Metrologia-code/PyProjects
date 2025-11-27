import tkinter as tk
import os, time, sys, ctypes
from datetime import datetime
import configparser

#Set process DPI awareness (Windows-specific)
ctypes.windll.shcore.SetProcessDpiAwareness(1)

'''user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
hWnd = kernel32.GetConsoleWindow()
user32.ShowWindow(hWnd, 3)'''

#пользовательские библиотеки
from Retriever_libs import retriever_tools, retriever_widgets
from User_libs import PlotterClass, CreateSavePath
#библиотеки управления приборами
from Tonghui_libs import tonghui_TH1992B, tonghui_TH2690A

#временно добавляем текущую директорию в PATH
CurrentDirectory = os.path.dirname(os.path.abspath(__file__))
#путь к папке с .ini конфигурациями
ConfigDirectory = CurrentDirectory + '\\Retriever_libs\\config\\'
#генератор пути к папке, в которую будут сохраняться данные
#если путь не существует, то быстрая запись будет вестись в местную директорию Data
SavePath = CreateSavePath(__file__, LAN_Path='\\\\MetroBulk\\Public\\EXP_DATA')

#версия программы для отображения в шапке, размер окна программы
version_txt, root_size = 'pyRetriever v0.6.0 _ 2025.11.24', '1050x720'

#загружаем файл с пресетами свипов
sweep_config = configparser.ConfigParser()
sweep_config.optionxform = str
sweep_config.read(ConfigDirectory + 'sweep_config.ini')

#считываем файл с пресетами
DeviceConfigs = configparser.ConfigParser()
DeviceConfigs.optionxform = str
#путь к конфигурационному файлу
FileName = 'Tonghui_TH1992B_config.ini'
FilePath = os.path.dirname(os.path.abspath(__file__)) + '\\Tonghui_libs\\config\\'
if not DeviceConfigs.read(FilePath + FileName):
    print(f'Не удалось считать файл: {FilePath + FileName}')
DeviceConfigNames = DeviceConfigs.sections()

#создаем объект фреймворка tkinter
root = tk.Tk()
#создаем объект класса интерфейса
gui = retriever_widgets.Widget(root, version_txt, root_size, sweep_config, DeviceConfigNames, )
#создаем объект класса управления прибором
DEVICE = tonghui_TH1992B.Device()
#создаем объект класса измерения ВАХ
Sweeper = retriever_tools.Sweeper()
SweeperData = retriever_tools.Data()

dependent_names = ['Source start', 'Source stop', 'Source p-ts', 'Meas. p-ts', 'Step sleep', ]

def step_val_udpate(name, index, mode):
    #посчитаем и выведем информационные значения
    param = {}
    try:
        for p in dependent_names:
            param[p] = float(gui.msweep_input_boxes[p].get())
    except ValueError:
        gui.msweep_input_boxes['Step_val'].set('_')
        gui.msweep_input_boxes['T expected'].set('_')
    else:
        #деление на ноль
        try:
            step_val = (param['Source stop']-param['Source start']) / (param['Source p-ts']-1)
        except:
            gui.msweep_input_boxes['Step_val'].set('_')
        else:
            gui.msweep_input_boxes['Step_val'].set(f'{step_val:.1e}')
        delta_t1, delta_t2 = Sweeper.trigger_delta, Sweeper.processing_delta
        #*********************************НУЖНО СЧИТАТЬ РЕАЛЬНУЮ АПЕРТУРУ!!!111111**************************************
        aperture_plug = 0.02
        T_expected = param['Step sleep'] + aperture_plug * param['Meas. p-ts'] + delta_t1+delta_t2
        gui.msweep_input_boxes['T expected'].set(f'{T_expected:.2f}')

def preset_select_event(name, index, mode):
    selected_preset = gui.sweep_preset_var.get()
    for parameter, box in Sweeper.sweep_parameter_names.items():
        gui.msweep_input_boxes[box].set(sweep_config.get(selected_preset, parameter))
    #блокируем поля ввода информационных значений
    block_names = ['Step_val', 'T expected', 'I_range', ]
    for name in block_names:
        gui.msweep_input_boxes[name].config(state='disabled')

gui.sweep_preset_var.trace('w', preset_select_event)
#дефолтный пресет
gui.sweep_presets_select.current(0)
#следим за изменением параметров, по которым считается шаг свипа
for name in dependent_names:
    gui.msweep_input_vars[name].trace('w', step_val_udpate)
    value = gui.msweep_input_boxes[name].get()
    gui.msweep_input_boxes[name].set(value)

def tonghui_connect_pressed():
    if DEVICE.Initialize(ConnectionMethod='TCPIP', DeviceAddress='192.168.88.11', DevicePort='45454'):
        if 'TH1992B' in DEVICE.GetIDN():
            try:
                CH1_state = int(DEVICE.GetParameter('ChannelState', ch='1'))
                CH2_state = int(DEVICE.GetParameter('ChannelState', ch='2'))
            except Exception as e:
                print(e)
            else:
                gui.connection_status_lab.config(text='подключено')
                gui.Ch1_toggle_btn.config(state='enabled')
                gui.Ch2_toggle_btn.config(state='enabled')
                gui.Ch1_toggle_var.set(CH1_state), gui.Ch2_toggle_var.set(CH2_state)
                gui.tonghui_disconnect_but.config(state='enabled')
                #gui.get_data_but.config(state='enabled')
                gui.tonghui_connect_but.config(state='disabled')

gui.tonghui_connect_but.configure(command=tonghui_connect_pressed)

def tonghui_disconnect_pressed():
    DEVICE.Close()
    gui.connection_status_lab.config(text='отключено')
    gui.tonghui_connect_but.config(state='enabled')
    gui.Ch1_toggle_btn.config(state='disabled')
    gui.Ch2_toggle_btn.config(state='disabled')
    #gui.get_data_but.config(state='disabled')
    gui.tonghui_disconnect_but.config(state='disabled')

gui.tonghui_disconnect_but.configure(command=tonghui_disconnect_pressed)

def get_data_pressed():
    #не использовать
    SweeperData.values = DEVICE.Get_data()
    gui.plot_routine(SweeperData.values['V'], SweeperData.values['A'], )
    n = len(SweeperData.values['V'])
    length = range(n)
    #разделитель данных для записи в файл
    delim = '\t'
    #собираем заголовок
    header = ''
    data_keys = list(SweeperData.values.keys())
    for data_key in data_keys:
        header = header + data_key + delim
    SweeperData.output = ''
    SweeperData.output = SweeperData.output + header[:-1] + '\n'
    #собираем данные в строку
    for i in length:
        ci = length.index(i)
        SweeperData.output = SweeperData.output + str(SweeperData.values['V'][ci]) + delim + str(SweeperData.values['A'][ci]) + delim + str(SweeperData.values['T'][ci]) + '\n'

gui.get_data_but.configure(command=get_data_pressed)



#переключатель канала
#словарь с переменными переключаталей
ChToggle_vars = {'1':gui.Ch1_toggle_var, '2':gui.Ch2_toggle_var}
#переключатель галочки tkinter, когда мы нажимаем на него, сначала меняет значение, а потом выполняет код
#поэтому сравниваем переменную переключателя с инвертированным значением считанного статуса канала
#это ломает мозг, ну и что ж
def Channel_toggle_btn_pressed(channel):
    CH_state = int(DEVICE.GetParameter('ChannelState', ch=channel))
    CH_desired = CH_state^1
    if CH_desired == ChToggle_vars[channel].get():
        if DEVICE.SetParameter('ChannelState', str(CH_desired), ch=channel):
            ChToggle_vars[channel].set(CH_desired)
    else:
        print(f'!!! ОШИБКА!!! Что-то пошло не так с каналом {channel}')

gui.Ch1_toggle_btn.configure(command=lambda: Channel_toggle_btn_pressed('1'))
gui.Ch2_toggle_btn.configure(command=lambda: Channel_toggle_btn_pressed('2'))



def set_y_scale():
    scale = gui.set_y_ax_select.get()
    linthresh = gui.linthresh_input.get()
    linscale = gui.linscale_input.get()
    gui.update_y_scale(scale, linthresh, linscale)

gui.set_y_ax_button.configure(command=set_y_scale)


def debug_pressed():
    #Clear any existing text in the Text widget
    gui.text_output.delete("1.0", tk.END) 
    #Insert new text
    gui.text_output.insert(tk.END, SweeperData.output)
    gui.plot_debug(SweeperData.values)

gui.debug_but.configure(command=debug_pressed)




def save_file_quick():
    #генерируем уникальное имя файла
    file_name = DEVICE.Name + ' VA ' + datetime.now().strftime("%Y-%m-%d %H-%M-%S")
    #путь к файлу
    file_path = SavePath + file_name + '.txt'
    with open(file_path, 'x') as file:
        file.write(SweeperData.output)
        print(f"Data saved successfully to: {file_path}")

gui.qsave_data_but.configure(command=save_file_quick)

def save_file_dialog():
    # Open the save file dialog
    file_path = tk.filedialog.asksaveasfilename(
        initialdir=SavePath[:-2],
        defaultextension=".txt",
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        title="Сохранить как..."
    )
    if file_path:
        try:
            with open(file_path, "w") as file:
                file.write(SweeperData.output)
            print(f"Data saved successfully to: {file_path}")
        except Exception as e:
            print(f"Error saving file: {e}")

gui.msave_data_but.configure(command=save_file_dialog)


#*********************НЕ ИСПРАВЛЕНО*****************************

#установка одного параметра прибора (берет имя команды из названия элемента интерфейса)
def set_button_pressed(name):
    parameter = gui.manual_input_boxes[name].get()
    check = DEVICE.Set_parameter(name, parameter)
    gui.manual_input_boxes[name].set(check)

#присваиваем команды кнопкам установки параметров свипа
for button_name in gui.manual_input_buttons:
    gui.manual_input_buttons[button_name].configure(command=lambda val=button_name: set_button_pressed(val))

#считывание всех параметров свипа и вывод в интерфейс
def get_all_manual_params():
    for name in gui.manual_input_boxes:
        parameter = DEVICE.Get_parameter(name)
        gui.manual_input_boxes[name].set(parameter)

gui.manual_control_buttons['get_all'].configure(command=get_all_manual_params)



def run_sweep_preset(channel):
    '''программное измерение по точкам'''
    
    DevicePreset = gui.device_preset_var.get()
    if not DevicePreset:
        print('Пресет прибора не выбран')
        return
        
    #печать разделителя для красоты
    border = ''
    for i in range(80):
        border += '_'
    preset = gui.sweep_preset_var.get()
    print(border), print(f'{preset}: старт...')
    
    #получаем значение галочки очищать ли плот
    #получить бы все параметры в дикт, эх
    if_plot_clear = gui.raw_check_var.get()
    
    #ЭТО ВСЕ НАПИСАНО ДЛЯ ТОЛСТОГО ТОНГХУЯ
    #конфигурируем прибор по пресету из ini-файла
    if not DEVICE.ConfigureDevice(ConfigName={channel:DevicePreset}, ):
        return
    print('Настройка источника, формы сигнала и ограничений: успешно')
    #ждем, пока значение вывода источника установится
    time.sleep(float(gui.msweep_input_vars['Init. sleep'].get()))
    #если выбрана опция очищать, то стираем все, что было в данных
    if if_plot_clear == 1:
        SweeperData.values = {}
    #генерируем имя набора данных
    new_data_name = preset + ' : ' + datetime.now().time().strftime("%H:%M:%S")
    #запускаем измерение
    got_me_some_data = Sweeper.Manual_sweep_stepbystep(DEVICE, gui, new_data_name, if_plot_clear, root, )
    #got_me_some_data = TH1992B.Manual_sweep(gui.msweep_input_vars)
    SweeperData.values[new_data_name] = got_me_some_data
    ###################################################################
    #формирование строк данных для сохранения
    n = len(SweeperData.values[new_data_name]['V'])
    length = range(n)
    #разделитель данных для записи в файл
    delim = '\t'
    #собираем заголовок
    header = ''
    data_keys = list(SweeperData.values[new_data_name].keys())
    for data_key in data_keys:
        header = header + data_key + delim
    SweeperData.output = ''
    SweeperData.output = SweeperData.output + header[:-1] + '\n'
    #собираем данные в строку
    for i in length:
        ci = length.index(i)
        V_str = str(SweeperData.values[new_data_name]['V'][ci])
        I_str = str(SweeperData.values[new_data_name]['I'][ci])
        SweeperData.output = SweeperData.output + V_str + delim + I_str + '\n'
    ###################################################################
    #DEVICE.ConfigureDevice() должен был включить канал
    #а Sweeper.Manual_sweep_stepbystep() - выключить
    #проверяем статус канала и обновляем галочку
    CH_state = int(DEVICE.GetParameter('ChannelState', ch=channel))
    ChToggle_vars[channel].set(CH_state)
    print(f'{preset}: выполнен')

gui.src_sweep_but.configure(command=lambda: run_sweep_preset(gui.sweep_channel_var.get()[-1]))


def save_as_new_sweep():
    cv = gui.sweep_presets_select['values']
    file_path = ConfigDirectory + 'sweep_config.ini'
    #new_preset_name = 'sweep '+datetime.now().strftime("%Y-%m-%d %H-%M-%S")
    selected_preset = gui.sweep_preset_var.get()
    diag_text = 'Укажите название нового пресета:     '
    new_preset_name = tk.simpledialog.askstring('Preset name', diag_text, initialvalue=selected_preset)
    if len(new_preset_name) > 0 and new_preset_name not in cv:
        with open(file_path, 'a+') as file:
            file.write(f'\n\n\n[{new_preset_name}]\n')
            for p, val_name in Sweeper.sweep_parameter_names.items():
                p_value = gui.msweep_input_vars[val_name].get()
                line = f'\n{p} = {p_value}'
                file.write(line)
            print(f'Новый пресет сохранен как: {new_preset_name}')
        #считываем ini файл заново и обновляем список элементов в поле выбора пресета
        sweep_config.read(ConfigDirectory + 'sweep_config.ini')
        gui.sweep_presets_select.configure(values=sweep_config.sections())
        gui.sweep_presets_select.current(len(cv))
    else:
        print('Что-то пошло не так с сохранением нового пресета\nНе ввели название или такое уже есть')

gui.save_as_new_sweep_but.configure(command=save_as_new_sweep)


#888888888888888888888888888888888888888888888888888888888888888888888888888888888888888888

def root_close():
    #убиваем окно
    root.quit()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", root_close)

#Start the Tkinter event loop
root.mainloop()