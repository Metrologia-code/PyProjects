import matplotlib.pyplot as plt
from datetime import datetime
import time, sys
import numpy as np
from Tonghui_libs import tonghui_TH1992B, tonghui_TH2690A
from Motion_control import Controller

#пользовательские библиотеки
from User_libs import CreateSavePath

def pos_to_x(axes, pos):
    '''Метод получает список осей с их атрибутами и список их координат и 
    возвращает значение координаты Х для графика. Если оси перекрыты, возвращается ноль. 
    1) Если используется одна ось возвращается ее координата. 
    2) Если используются только горизонтальные или только вертикальные оси 
    возвращается координата середины окошка: отрицательное значение если окошко 
    слева или снизу по пучку и положительное в противном случае.
    3)Если используются все оси возвращается площадь окошка.'''
    conf=0
    for axis in axes:
        conf += 2 ** axis['number'] * axis['is_used']
    if conf in [1,2,4,8]:
        for i, v in zip(bin(conf)[-1:-5:-1],pos):
            if i == '1':
                return v
    elif conf == 6:
        return (pos[2] - pos[1]) / 2 if pos[2] + pos[1] > 0 else 0
    elif conf == 9:
        return (pos[0] - pos[3]) / 2 if pos[0] + pos[3] > 0 else 0
    elif conf == 15:
        w = pos[2] + pos[1] if pos[2] + pos[1] > 0 else 0
        h = pos[0] + pos[3] if pos[0] + pos[3] > 0 else 0
        return w*h

#Выбор прибора 'tonghui_TH2690A' либо 'tonghui_TH1992B'
device_name = 'tonghui_TH1992B' #Менять строку 
exec(f'DEVICE = {device_name}.Device()')
#адрес подключенияк к tonghui
ConnectionDetails = {'ConnectionMethod':'TCPIP',
                     'DeviceAddress':'192.168.88.11',
                     'DevicePort':'45454', }
'''ConnectionDetails = {'ConnectionMethod':'TCPIP',
                     'DeviceAddress':'192.168.88.11',
                     'DevicePort':'45454', }'''

#для TH1992B - словарь из одного элемента (также определяет канал)
#для TH2690A - просто название пресета
#!!!!!ACHTUNG!!!!! проверь пресет перед запуском !!!!!ACHTUNG!!!!!
tonghui_preset = {'1':'TEST_CURR', }
#Выбираем, что писать в файл и строить на графике
#для TH1992B - с указанием канала, например, CURR1
graph_data = 'CURR1'

#пробуем подключиться к tonghui
if not DEVICE.Initialize(**ConnectionDetails):
    sys.exit(1)
#конфигурируем tonghui по пресету из ini-файла
if not DEVICE.ConfigureDevice(ConfigName=tonghui_preset, ):
    sys.exit(1)

#подключаемся к контроллеру моторов осей
acs = Controller(ip="192.168.88.10", port=701)

#Списки для постраения графика
FPosition = list()
Current = list()

#Задержка перед измерением после остановки осей
t = 1

#Настройка осей. Для каждой оси нужно установить начальное и конечное положение.
#Если они совпадают, ось приедет туда и дальше использоваться не будет.
axes= [
       {'name':     'APT',  #не менять
       'number':    0,      #не менять
       'start':     -1.5,
       'end':       3.5}, 
       
       {'name':     'APL',  #не менять
       'number':    1,      #не менять
       'start':     0.5,
       'end':       5.5}, 
       
       {'name':     'APR',  #не менять
       'number':    2,      #не менять
       'start':     -0.5,
       'end':       4.5}, 
       
       {'name':     'APB',  #не менять
       'number':    3,      #не менять
       'start':     1.5,
       'end':      6.5}
       ]
#Количество интервалов (установить требуемое значение)
intervals = 100

#Добовляем к словарям осей массивы координат и информацию об их использовании
for ax in axes:
    ax['pos'] = np.linspace(ax['start'], ax['end'], intervals +1)
    ax['is_used'] = ax['start'] != ax['end']

#Открываем окно графика
fig = plt.figure(1, figsize=(8, 6))
fig.clf()

#генератор пути к папке, в которую будут сохраняться данные
SavePath = CreateSavePath(__file__, LAN_Path='\\\\MetroBulk\\Public\\EXP_DATA1')
#генерируем уникальное имя файла и добавляем путь к нему
FilePath = SavePath + DEVICE.Name + ' ' + datetime.now().strftime("%Y-%m-%d %H-%M-%S") + '_axes_scan'

try:

    #Подключаемся, устанавливаем оси в начальное положение и ненужные отключаем
    acs.connect()
    for ax in axes:
        acs.enable_axis(ax['number'])
        time.sleep(0.30) #Надо внести задержку либо проверку статуса в метод enable_axis() класса Controller
        acs.ptp(ax['number'], ax['start'])
    time.sleep(0.01) #Надо внести в метод wait() класса Controller
    acs.wait()
    for ax in axes:
        if not ax['is_used']:
            acs.disable_axis(ax['number'])

    #Время начала измерений
    start_time = time.time()

    with open(FilePath+'.txt', 'x') as file:
        #Подгатавливаем и записываем шапку в файл
        header = 'time, s\t'
        for ax in axes:
            header += ax['name'] + ' position, mm\t'
        header += graph_data

        #разделитель данных для записи в файл
        #Delimiter = '\t'
        #формируем заголовок
        #Header = Delimiter.join(['time'] + Arguments['DataNames']) + '\n'
        
        file.write(header + '\n')

        for cpos in range(intervals + 1):
            #Отправляем используемые оси в следущую точку
            for ax in axes:
                if ax['is_used']:
                    acs.ptp(ax['number'], ax['pos'][cpos])
            time.sleep(0.01) #Надо внести в метод wait() класса Controller
            acs.wait()

            #Опрашиваем положение всех осей
            FP = []
            for ax in axes:
                FP.append(acs.get_fpos(ax['number']))
            
            #Ждем, измеряем прибором Tonghui и время с начала эксперимента
            time.sleep(t)
            #DEVICE.SingleMeasure() возвращает словарь вида {'VOLTage':value,'CURR':value,}
            results = DEVICE.SingleMeasure()
            result_time = time.time() - start_time
            print(*FP, *results)
            
            #выполняем, если прибор вернул измерения
            if results:
                
                #формируем строку из списка данных и записываем в файл
                to_write = f'{result_time:.3f}\t{FP[0]:.3f}\t{FP[1]:.3f}\t{FP[2]:.3f}\t{FP[3]:.3f}\t'
                to_write = to_write + str(results[graph_data])
                file.write(to_write+'\n')
            #Записываем данные в файл, добавляем к спискам для графика и перестраиваем график
            FPosition.append(pos_to_x(axes, FP))
            Current.append(results[graph_data])
            plt.plot(FPosition, Current, color='#000066', lw=0.8, marker='o', markersize=1.5)
            plt.draw()
            plt.pause(0.01)

    if 'TH1992B' in DEVICE.Name:
        DEVICE.ChannelsTurnOff()
    
    #прерываем связь с прибором
    DEVICE.Close()
    plt.show()

except KeyboardInterrupt:
    file.close()
    if 'TH1992B' in DEVICE.Name:
        DEVICE.ChannelsTurnOff()
    #прерываем связь с прибором
    DEVICE.Close()
