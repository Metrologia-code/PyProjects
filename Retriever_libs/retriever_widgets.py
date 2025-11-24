import tkinter as tk
from tkinter import ttk, filedialog

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk)

import itertools

class Widget:
    
    def __init__(self, root, version, rsize, sweep_config, ):
        
        self.root = root
        self.root.title(f'TH1992B Trigger retriever _ {version}')
        self.root.geometry(rsize)
        

        #****************************************** __фреймы__ ******************************************
        
        #парсим размеры окна
        rsize_list = rsize.split('x')
        rwidth, rheight, pdelta = int(rsize_list[0]), int(rsize_list[1]), 15

        '''style = ttk.Style()
        style.configure("Toolbutton", borderwidth=2, relief="solid", highlightthickness=2, highlightbackground="red")
        style.map("Toolbutton", 
              background=[("active", "lightgray")],
              relief=[("active", "raised")],
              bordercolor=[("active", "red")]) '''
        
        #настройки
        mainframes_pad = {'padx':5, 'pady':5}
        options = {'padx':2, 'pady':1}
        pads = {'padx':1, 'pady':1}
        border = {'highlightbackground':'black', 'highlightthickness':1}
        plotframe_size = {'height':rheight-pdelta-150, 'width':rwidth-pdelta}
        ctrlframe_size = {'height':150, 'width':rwidth-pdelta}
        combo_options, combo_size = {'padx': 2, 'pady': 2, }, {'width': 7, }
        sweep_combo_size = {'width': 9, }
        sety_options = {'padx': 3, 'pady': 3, }
        #check_button_size = {'height':1, 'width':1}

        #главный фрейм
        mainframe = tk.Frame(self.root, **mainframes_pad, )
        mainframe.grid(column=0, row=0, sticky='nw',)

        #фреймы плотов
        plotting_frame = tk.Frame(mainframe, **options, **border, **plotframe_size, )
        plotting_frame.grid_propagate(0)
        plotting_frame.grid(column=0, row=0, **pads, sticky='nw', )

        #ноутбук
        notebook = ttk.Notebook(plotting_frame, )
        notebook.grid(column=0, row=0, **pads, sticky='nw', )

        #фреймы ноутбука
        fig_raw_frame = ttk.Frame(notebook, )
        fig_raw_frame.grid(column=0, row=0, sticky='nw', )
        
        fig_detail_frame = ttk.Frame(notebook, )
        fig_detail_frame.grid(column=0, row=0, sticky='nw', )

        #настраиваем стиль вкладок
        style = ttk.Style()
        style.configure("TNotebook.Tab", padding=[20, 0], )

        #добавляем вкладки
        notebook.add(fig_raw_frame, text='V - I')
        notebook.add(fig_detail_frame, text='Detail')

        #фреймы кнопочек
        toolbar_frame = tk.Frame(mainframe, **options, **border, **ctrlframe_size, )
        toolbar_frame.grid_propagate(0)
        toolbar_frame.grid(column=0, row=1, **pads, sticky='nw',)


        #************************************** __фигурирование__ ***************************************

        #plt.ion()
        #plt.ioff()
        
        #счетчик линий
        self.lines_names = []

        #размеры
        px = 1/plt.rcParams['figure.dpi']
        figsize, figsize_d = [800*px, 500*px], [620*px, 200*px]

        #фигуры
        self.fig, self.ax = plt.subplots(figsize=(figsize[0], figsize[1]), constrained_layout=True)
        self.dfig1, self.dax1 = plt.subplots(figsize=(figsize_d[0], figsize_d[1]), constrained_layout=True)
        self.dfig2, self.dax2 = plt.subplots(figsize=(figsize_d[0], figsize_d[1]), constrained_layout=True)
        
        #self.ax.patch.set_linewidth(1)

        #настраиваем деления
        def set_minorticks(ax: plt.axes) -> None: 
            ax.grid(axis='both', which='both', ls='--', lw='0.5', c='#808080')
            ax.minorticks_on()
            ax.ticklabel_format(axis='y', scilimits=[-3,3])
            ax.ticklabel_format(axis='x', useOffset=False)

        for ax in [self.ax, self.dax1, self.dax2]:
            set_minorticks(ax)

        #подписываем оси
        self.label_opt = {'labelpad':4, 'fontsize':10, }
        def set_ax_label(ax: plt.axes, x, y) -> None:
            ax.set_xlabel(x, fontname='Arial', **self.label_opt, )
            ax.set_ylabel(y, fontname='Arial', **self.label_opt, )
        
        set_ax_label(self.ax, 'V', 'I', )
        set_ax_label(self.dax1, '', 'V', )
        set_ax_label(self.dax2, '', 'I', )

        #меняем шрифт тиков
        ticks_font = font_manager.FontProperties(family='Arial', size=8, weight='light')
        xticks, yticks = self.ax.get_xticklabels(), self.ax.get_yticklabels()
        dxticks1, dyticks1 = self.dax1.get_xticklabels(), self.dax1.get_yticklabels()
        dxticks2, dyticks2 = self.dax2.get_xticklabels(), self.dax2.get_yticklabels()
        for xtick, ytick in itertools.product(xticks, yticks):
            xtick.set_fontproperties(ticks_font)
            ytick.set_fontproperties(ticks_font)
        for xtick, ytick in itertools.product(dxticks1, dyticks1):
            xtick.set_fontproperties(ticks_font)
            ytick.set_fontproperties(ticks_font)
        for xtick, ytick in itertools.product(dxticks2, dyticks2):
            xtick.set_fontproperties(ticks_font)
            ytick.set_fontproperties(ticks_font)
        
        titles = ['Вольт-амперная характеристика', 'График 1', 'График 2']
        self.ax.set_title(label=titles[0], fontname='Arial', fontsize=11, loc='center') #color='blue',
        self.dax1.set_title(label=titles[1], fontname='Arial', fontsize=9, loc='center')
        self.dax2.set_title(label=titles[2], fontname='Arial', fontsize=9, loc='center')
        
        #creating the Tkinter canvas containing the Matplotlib figure
        self.canvas = FigureCanvasTkAgg(self.fig, master = fig_raw_frame)
        self.canvas_d1 = FigureCanvasTkAgg(self.dfig1, master = fig_detail_frame)
        self.canvas_d2 = FigureCanvasTkAgg(self.dfig2, master = fig_detail_frame)
        
        #self.canvas.draw()
        
        #placing the canvas on the Tkinter window
        self.canvas.get_tk_widget().grid(column=0, row=0, sticky='nw', **options)
        self.canvas_d1.get_tk_widget().grid(column=0, row=0, sticky='nw', **options)
        self.canvas_d2.get_tk_widget().grid(column=0, row=1, sticky='nw', **options)
        
        raw_options = {'linestyle':'solid', 'linewidth':0.2, 'marker':'.', 'markersize':1, 'c':'b'}
        
        #self.plot1, = self.ax.plot([], [], **raw_options, label='raw')
        self.raw_lines = {}
        
        self.plot2, = self.dax1.plot([], [], **raw_options, label='detail_1')
        self.plot3, = self.dax2.plot([], [], **raw_options, label='detail_1')
        
        

        #***************************************** __виджеты__ ******************************************

        #подпись статуса подключения
        self.connection_status_lab = ttk.Label(toolbar_frame, text=f'не подкл.',)
        self.connection_status_lab.grid(column=0, row=0, sticky='nw',)
        
        #кнопка подключения
        self.tonghui_connect_but = ttk.Button(toolbar_frame, text='подключить', width=12, state='enabled')
        self.tonghui_connect_but.grid(column=0, row=1, **options, sticky='nw',)
        
        #кнопка отключения
        self.tonghui_disconnect_but = ttk.Button(toolbar_frame, text='отключить', width=12, state='disabled')
        self.tonghui_disconnect_but.grid(column=0, row=2, **options, sticky='nw',)
        
        #кнопка забора данных
        self.get_data_but = ttk.Button(toolbar_frame, text='получить', width=12, state='disabled')
        self.get_data_but.grid(column=0, row=3, **options, sticky='nw',)

        #кнопка вкл/выкл канала 1
        self.Ch1_toggle_var = tk.IntVar()
        self.Ch1_toggle_btn = ttk.Checkbutton(toolbar_frame, text="Канал 1  ", variable=self.Ch1_toggle_var, state='disabled')
        self.Ch1_toggle_btn.grid(column=1, row=1, **sety_options, sticky='nw',)

        #кнопка вкл/выкл канала 2
        self.Ch2_toggle_var = tk.IntVar()
        self.Ch2_toggle_btn = ttk.Checkbutton(toolbar_frame, text="Канал 2  ", variable=self.Ch2_toggle_var, state='disabled')
        self.Ch2_toggle_btn.grid(column=1, row=2, **sety_options, sticky='nw',)
        
        #галочка для выбора сохранения предыдущих данных
        self.raw_check_var = tk.IntVar()
        self.raw_check_button = tk.Checkbutton(toolbar_frame, text='Ощичать?', variable=self.raw_check_var, )
        self.raw_check_var.set(1)
        self.raw_check_button.grid(column=5, row=0, columnspan=2, sticky='nw',)
        
        #выбор шкалы y
        self.set_y_ax_var = tk.StringVar()
        yscales = ['linear', 'log', 'symlog']
        self.set_y_ax_select = ttk.Combobox(toolbar_frame, textvariable=self.set_y_ax_var, width=9, values=yscales)
        self.set_y_ax_select.set(yscales[0])
        self.set_y_ax_select.grid(column=5, row=1, columnspan=2, sticky='nw', **sety_options)

        #выбор параметров symlog
        self.linthresh_input = tk.Entry(toolbar_frame, width=5)
        self.linthresh_input.grid(column=5, row=2, sticky='nw', **sety_options)
        self.linthresh_input.insert(0, '1e-8')
        self.linscale_input = tk.Entry(toolbar_frame, width=5)
        self.linscale_input.grid(column=6, row=2, sticky='nw', **sety_options)
        self.linscale_input.insert(0, '0.2')

        #кнопка установки оси y
        self.set_y_ax_button = ttk.Button(toolbar_frame, text='Выбор шкал', width=12, state='enabled')
        self.set_y_ax_button.grid(column=5, row=3, columnspan=2, **options, sticky='nw',)

        #кнопка сохранения данных автомат
        self.qsave_data_but = ttk.Button(toolbar_frame, text='сохр. авто', width=12, state='enabled')
        self.qsave_data_but.grid(column=7, row=1, **options, sticky='nw',)

        #кнопка сохранения данных с диалогом
        self.msave_data_but = ttk.Button(toolbar_frame, text='сохр. выбор', width=12, state='enabled')
        self.msave_data_but.grid(column=7, row=2, **options, sticky='nw',)
        
        #кнопка отладки
        self.debug_but = ttk.Button(toolbar_frame, text='отладка', width=12, state='disabled')
        self.debug_but.grid(column=8, row=1, **options, sticky='nw',)

        #поле вывода считанных данных
        self.text_output = tk.Text(fig_detail_frame, height=33, width=59, font='Arial 8')
        self.text_output.grid(column=1, row=0, rowspan=3, **options, sticky='nw',)



        
        #*************************** __фреймы для свипа__ ***************************
        sweep_toolbar_frame = ttk.Frame(fig_raw_frame, )
        sweep_toolbar_frame.grid(column=1, row=0, sticky='nw', )

        IV_control_frame = ttk.Frame(sweep_toolbar_frame, relief=tk.SOLID, borderwidth=3)
        IV_control_frame.grid(column=0, row=0, sticky='nw', )
        
        source_settings_frame = ttk.Frame(sweep_toolbar_frame, relief=tk.SOLID, borderwidth=3)
        source_settings_frame.grid(column=1, row=0, sticky='nw', )

        #*************************** __фреймы для свипа__ ***************************

        #поля ввода параметров ручного свипа
        self.msweep_input_boxes, self.msweep_input_vars, self.msweep_input_labs = {}, {}, {}
        msweep_input_names = ['Source start',
                              'Source stop',
                              'Source p-ts',
                              'Step_val',
                              'I_limit',
                              'I_range',
                              'I_rng_AUTO',
                              'Init. sleep',
                              'Step sleep',
                              'Meas. p-ts',
                              'T operation',
                              'T expected',
                              ]
        
        IV_frame = IV_control_frame
        manual_sweep_header = ttk.Label(IV_frame, text='Прогр-ное измерение',)
        manual_sweep_header.grid(row=0, column=0, columnspan=2, sticky='nw', )

        
        #выбор канала
        self.sweep_channel_var = tk.StringVar()
        channel_options = ['Канал 1', 'Канал 2', ]
        self.sweep_channel_select = ttk.Combobox(IV_frame, textvariable=self.sweep_channel_var, width=20, values=channel_options, state='readonly', )
        self.sweep_channel_select.set(channel_options[0])
        self.sweep_channel_select.grid(row=1, column=0, columnspan=3, sticky='nw', **combo_options)
        
        #выбор пресета прибора
        self.device_preset_var = tk.StringVar()
        self.device_presets_select = ttk.Combobox(IV_frame, textvariable=self.device_preset_var, width=20, state='readonly', )
        self.device_presets_select.grid(row=2, column=0, columnspan=3, sticky='nw', **combo_options)
        
        #выбор пресета свипа
        self.sweep_preset_var = tk.StringVar()
        presets = sweep_config.sections()
        self.sweep_presets_select = ttk.Combobox(IV_frame, textvariable=self.sweep_preset_var, width=20, values=presets, state='readonly', )
        self.sweep_presets_select.grid(row=3, column=0, columnspan=3, sticky='nw', **combo_options)

        sweep_row_start = 4
        for name in msweep_input_names:
            i = msweep_input_names.index(name)
            self.msweep_input_vars[name] = tk.StringVar()
            self.msweep_input_boxes[name] = ttk.Combobox(IV_frame, 
                                                         textvariable=self.msweep_input_vars[name], **sweep_combo_size, ) #values=options
            self.msweep_input_boxes[name].grid(column=0, row=i+sweep_row_start, sticky='nw', **combo_options)
            self.msweep_input_labs[name] = ttk.Label(IV_frame, text=name,)
            self.msweep_input_labs[name].grid(column=1, row=i+sweep_row_start, sticky='nw', )
        
        #кнопка запуска ручного свипа
        self.src_sweep_but = ttk.Button(IV_frame, text='Запуск измерений', width=22, state='enabled')
        self.src_sweep_but.grid(column=0, row=20, columnspan=2, **options, sticky='nw',)

        #кнопка создания нового пресета
        self.save_as_new_sweep_but = ttk.Button(IV_frame, text='Сохр. как новый', width=22, state='enabled')
        self.save_as_new_sweep_but.grid(column=0, row=21, columnspan=2, **options, sticky='nw',)
        
        #поля ввода параметров для ручного управления
        self.manual_input_boxes, self.manual_input_vars, self.manual_input_buttons = {}, {}, {}
        manual_input_names = ['source', 'limit', ] #'limit', 'MinRng(I)', 'MinRng(V)'
        manual_frame = source_settings_frame
        for name in manual_input_names:
            i = manual_input_names.index(name)
            self.manual_input_vars[name] = tk.StringVar()
            self.manual_input_boxes[name] = ttk.Combobox(manual_frame, textvariable=self.manual_input_vars[name], 
                                                        **combo_size, ) #values=options
            self.manual_input_buttons[name] = ttk.Button(manual_frame, text=name, width=10, state='enabled')
            
            self.manual_input_boxes[name].grid(column=0, row=i, sticky='nw', **combo_options)
            self.manual_input_buttons[name].grid(column=1, row=i, sticky='nw', )
        
        #кнопки ручного управления
        self.manual_control_buttons = {}
        manual_control_names = ['get_all', ]
        manual_frame = source_settings_frame
        for name in manual_control_names:
            i = manual_control_names.index(name)
            self.manual_control_buttons[name] = ttk.Button(manual_frame, text=name, width=9, state='enabled')
            self.manual_control_buttons[name].grid(column=i, row=len(manual_input_names), sticky='nw', padx=1, pady=2)
        
        #обновим объект ткинтера, чтобы получить размеры
        self.root.update()


    
    #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! __методы__ !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    
    #def create_new_line(self, name, ):

        #do nothing
        
    
    def plot_routine(self, x, y, name, if_plot_clear, ):

        if if_plot_clear == 1:
            for line_name in self.raw_lines:
                self.raw_lines[line_name].remove()
            self.raw_lines = {}
            #self.ax.clear()

        colors = []
        if len(self.raw_lines) > 0:
            for line_name in self.raw_lines:
                colors.append(self.raw_lines[line_name].get_color())
        
        color_collection = ['b', 'k', 'r', 'm', 'g', 'c',]
        new_color = ''
        for c in color_collection:
            if c not in colors:
                new_color = c
                break
        if len(new_color) == 0:
            new_color = 'b'
        
        line_options = {'linestyle':'solid', 'linewidth':0.3, 'marker':'.', 'markersize':1, 'c':new_color}
        self.raw_lines[name], = self.ax.plot([], [], **line_options, label=name)

        #подставляем значения данных в оси
        self.raw_lines[name].set_xdata(x)
        self.raw_lines[name].set_ydata(y)

        #лимиты осей
        self.ax.relim()
        self.ax.autoscale_view()

        self.ax.legend(loc='best', fontsize='x-small', markerscale=2.5)

        self.canvas.draw()

    
    def update_y_scale(self, scale, linthresh, linscale):

        try:
            if scale == 'symlog':
                self.ax.set_yscale(scale, linthresh=float(linthresh), linscale=float(linscale), )
            else:
                self.ax.set_yscale(scale, )
            self.canvas.draw()
        except Exception as e:
            print(e)

    
    def plot_debug(self, data, ):

        #подставляем значения данных в оси
        self.plot2.set_xdata(data['T'])
        self.plot2.set_ydata(data['V'])
        self.plot3.set_xdata(data['T'])
        self.plot3.set_ydata(data['A'])

        #лимиты осей
        self.dax1.relim()
        self.dax2.autoscale_view()

        self.canvas_d1.draw()
        self.canvas_d2.draw()