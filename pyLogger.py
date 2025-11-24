from datetime import datetime
import time, sys

#пользовательские библиотеки
from User_libs import PlotterClass, ParseLoggerArguments, CreateSavePath, FormatTime

print('pyLogger v0.8.3 - 2025.11.24')

#структура стартовых аргументов:
''' DeviceName,        str,    имя используемого прибора
    ConnectionMethod,  str,    тип подключения
    DeviceAddress,     str,    ip-адрес прибора
    DevicePort,        str,    порт
    DeviceSerial,      str,    серийный номер прибора
    ConfigName,        str/dict, имя пресета из ini файла
    MeasTime,          float,  желаемое время одного измерения, сек
    MeasPoints,        int,  количество измерений (точек)
    CanvasPoints,      int,    количество точек по оси х на графике
    EnablePlot,        bool,   Включение графика
    DataNames,         list,   имена данных, которые будут записаны в файл
    LineNames,         list,   имена данных, которые будут на графике
    YLabel,            str,    название оси у для графика
    YTransform,        bool,   Пересчет оси у '''

#парсим строковые аргументы, получаются словари (аргументы см. выше):
#Arguments = {'ArgumentName':ArgumentValue, ...}
Arguments = ParseLoggerArguments(LaunchArguments=sys.argv[1:], )
#список имен аргументов, относящихся к установке соединения с прибором
ConnectNames = ['ConnectionMethod', 'DeviceAddress', 'DevicePort', 'DeviceSerial', ]
#словарь с аргументами для установки соединения, передается в Device.Initialize()
ConnectionDetails = {name: Arguments[name] for name in ConnectNames if name in Arguments}

#библиотеки управления приборами
from Tonghui_libs import tonghui_TH1992B, tonghui_TH2690A
#создаем объект класса из библиотеки, соответствующей заданному имени прибора
exec(f"DEVICE = {Arguments['DeviceName']}.Device()")

'''#пробуем подключиться к прибору
if not DEVICE.Initialize(**ConnectionDetails):
    sys.exit(1)
#конфигурируем прибор по пресету из ini-файла
if not DEVICE.ConfigureDevice(ConfigName=Arguments['ConfigName'], ):
    sys.exit(1)'''

#генератор пути к папке, в которую будут сохраняться данные
SavePath = CreateSavePath(__file__, LAN_Path='\\\\MetroBulk\\Public\\EXP_DATA1')
#генерируем уникальное имя файла и добавляем путь к нему
FilePath = SavePath + DEVICE.Name + ' ' + datetime.now().strftime("%Y-%m-%d %H-%M-%S")

#разделитель данных для записи в файл
Delimiter = '\t'
#формируем заголовок
Header = Delimiter.join(['time'] + Arguments['DataNames']) + '\n'

#вывод параметров эксперимента
WholeTime = (Arguments['MeasPoints'] - 1) * Arguments['MeasTime']
print(f'''\
Желаемое время измерения\t= {Arguments['MeasTime']} сек
Количество измерений (точек)\t= {Arguments['MeasPoints']}
Ожидаемое время выполнения\t= {FormatTime(WholeTime)}
Сохраняем данные в {SavePath}
...........
Время начала измерений: \t{datetime.now().strftime('%Y-%m-%d %H:%M')}''')

if Arguments['EnablePlot']:
    #создаем объект класса из pyTools.py, если выбрана опция строить график
    PlotterArguments = { 'x_label' : 't, сек', 
                         'y_label' : Arguments['YLabel'], 
                         'plot_name' : Arguments['DeviceName'], 
                         'pts' : {'x_step' : Arguments['MeasTime'], 
                                  'x_pts'  : Arguments['CanvasPoints'],
                                 }, 
                       }
    Plotter = PlotterClass(Arguments['LineNames'], **PlotterArguments)



ttc = {'t_op_start':0, 't_op_finish':0, 't_op_fact':0, }

def correct_sleep():
    
    #всратое говно уже не помню как работает. но работает

    #время, затраченное с момента начала измерений
    ttc['t_op_finish'] = time.time() - tt1
    ttc['t_op_fact'] = ttc['t_op_finish'] - ttc['t_op_start']

    time_to_sleep = Arguments['MeasTime'] - ttc['t_op_fact'] - 0.0036 #0.0066
    
    t_temp = ttc['t_op_finish'] #костыль
    if (i/int(t_when/Arguments['MeasTime'])) % 1 == 0 and i > 0:
        print(f" -- time_sofar={t_temp}")
        print(f" -- time_expected={(i+1)*Arguments['MeasTime'] - time_to_sleep}")
    
    if time_to_sleep > 0.001:
        time.sleep(time_to_sleep)
    else:
        #time.sleep(1)
        print(' _ ' + f'{datetime.now()}'[11:22]
              + f" - время итерации превышено (sleep = {time_to_sleep:.3f})")

try:
    
    file = open(FilePath + '.txt', 'x')
    
    #записываем заголовок лог-файла
    file.write(Header)
    #интервал вывода промежуточного времени в секундах
    t_when = 21600

    #записываем время начала выполнения программы
    tt1 = time.time()
    
    PointsList = range(Arguments['MeasPoints'])
    
    for i in PointsList:

        ttc['t_op_start'] = time.time() - tt1

        #индекс текущей точки (для отладки)
        meas_index = PointsList.index(i)

        #измерение
        results = DEVICE.SingleMeasure()
        #время измерения
        result_time = time.time() - tt1

        #выполняем, если прибор вернул измерения
        if results:
            
            #формируем строку из списка данных и записываем в файл
            #можно поменять местами с плотом и дописать трансформ
            to_write = f'{result_time:.3f}' + Delimiter
            for _, result in results.items():
                to_write = to_write + str(result) + Delimiter
            file.write(to_write[:-1]+'\n')
    
            #плот, если вкл выше
            if Arguments['EnablePlot']:

                PlotResults = {k: results[k] for k in Arguments['LineNames'] }

                if Arguments['YTransform']:
                    pass
                
                #plot_args = {'x':[], 'results':{}, }
                Plotter.plot_routine(i, result_time, PlotResults, )

            correct_sleep()

    #считаем время, затраченное на выполнение программы
    tt2 = time.time()-tt1
    #вывод текущего времени
    print('...........')
    print('Время окончания измерений: \t'+f'{datetime.now()}'[:16])
    print(f'Полное время\t= {tt2:.3f} сек')
    print(f'Ожидаемое время\t= {t_calc:.3f} сек')          

except KeyboardInterrupt:
    #CTRL+C
    pass

finally:
    #закрываем текстовый файл
    file.close()
    #сохраняем график
    if 'Plotter' in globals():
        Plotter.save_figure(FilePath)
    #прерываем связь с прибором
    #DEVICE.Close()
    