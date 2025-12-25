import matplotlib.pyplot as plt
from datetime import datetime
import time, sys
import numpy as np
from Tonghui_libs import tonghui_TH1992B, tonghui_TH2690A
from Motion_control import Controller

#пользовательские библиотеки
from User_libs import CreateSavePath

def InitSpeed():
    for ax in range(3):
        acs.set_vel(ax,1)    # скорость
        acs.set_acc(ax,5)    # ускорение/торможение
        acs.set_jerk(ax,25)  # скорость изменения ускорения

def PrintPosition():
    print('APT/APL/APR/APB = ', round(acs.get_fpos(0), 3), '/',
                                round(acs.get_fpos(1), 3), '/',
                                round(acs.get_fpos(2), 3), '/',
                                round(acs.get_fpos(3), 3))
    print()

def StartMove(used_axis: int, to_go: int):
    acs.enable_axis(used_axis)
    if abs(acs.get_fpos(used_axis) - to_go) > 0.001:
        acs.ptp(used_axis, to_go)
        print('Ось', used_axis, 'движется в ', to_go)
    else:
        print('Ось', used_axis, 'уже в позиции ', to_go, '±0.001')

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
#device_name = 'tonghui_TH2690A' #Менять строку 
device_name = 'tonghui_TH1992B' #Менять строку 
exec(f'DEVICE = {device_name}.Device()')
#адрес подключенияк к tonghui_TH1992B
if device_name == 'tonghui_TH1992B':
    ConnectionDetails = {'ConnectionMethod':'TCPIP',
                         'DeviceAddress':'192.168.88.11',
                         'DevicePort':'45454', }
    #для TH1992B - словарь из одного элемента (также определяет канал)
    tonghui_preset = {'2':'APL_I', }
    #Выбираем, что писать в файл и строить на графике (VOLTage, CURR, RES)
    #для TH1992B - с указанием канала, например, CURR1
    graph_data = 'CURR2'
    
#адрес подключенияк к tonghui_TH2690A
if device_name == 'tonghui_TH2690A':
    ConnectionDetails = {'ConnectionMethod':'TCPIP',
                         'DeviceAddress':'192.168.88.12',
                         'DevicePort':'45454', }
    #для TH2690A - просто название пресета
    tonghui_preset = 'PICOAMMETER_TEST_1'
    #Выбираем, что писать в файл и строить на графике (VOLTage, CURR, RES)
    graph_data = 'CURR'

#пробуем подключиться к tonghui
if not DEVICE.Initialize(**ConnectionDetails):
    sys.exit(1)
#конфигурируем tonghui по пресету из ini-файла
if not DEVICE.ConfigureDevice(ConfigName=tonghui_preset, ):
    sys.exit(1)

#подключаемся к контроллеру моторов осей и устанавливаем скорости движения
acs = Controller(ip="192.168.88.10", port=701)
acs.connect()
InitSpeed()
 
#Списки для построения графика
FPosition = list()
Current = list()

#Задержка перед измерением после остановки осей
t = 0.1

#Настройка осей. Для каждой оси нужно установить начальное и конечное положение.
#Если они совпадают, ось приедет туда и дальше использоваться не будет.
axis_toX = 0
axes= [
       {'name':     'APT',  #не менять
       'number':    0,      #не менять
       'start':     -10,
       'end':       10}, 
       
       {'name':     'APL',  #не менять
       'number':    1,      #не менять
       'start':     2,
       'end':       2}, 
       
       {'name':     'APR',  #не менять
       'number':    2,      #не менять
       'start':     2,
       'end':       2}, 
       
       {'name':     'APB',  #не менять
       'number':    3,      #не менять
       'start':     10,
       'end':       10}
       ]
#Количество интервалов (установить требуемое значение)
intervals = 80

#Добавляем к словарям осей массивы координат и информацию об их использовании
for ax in axes:
    ax['pos'] = np.linspace(ax['start'], ax['end'], intervals + 1)
    ax['is_used'] = ( ax['start'] != ax['end'] )

#Открываем окно графика
fig = plt.figure(1, figsize=(8, 6))
fig.clf()

#генератор пути к папке, в которую будут сохраняться данные
#ВНИМАНИЕ! если путь не существует, то запись будет вестись в местную директорию Data
#SavePath = CreateSavePath(__file__, LAN_Path='\\\\MetroBulk\\Public\\EXP_DATA')
SavePath = CreateSavePath(LAN_Path='\\\\MetroBulk\\Public\\EXP_DATA', )
#генерируем уникальное имя файла и добавляем путь к нему
FilePath = SavePath + DEVICE.Name + ' ' + datetime.now().strftime("%Y-%m-%d %H-%M-%S") + '_axes_scan'

try:

    #Устанавливаем оси в начальное положение и ненужные отключаем
    print()
    print('Текущее положение осей')
    PrintPosition()
    print('Перемещаемся в начальную точку...') 
    for ax in axes:
        acs.enable_axis(ax['number'])
        time.sleep(0.30) #Надо внести задержку либо проверку статуса в метод enable_axis() класса Controller
        acs.ptp(ax['number'], ax['start'])
    time.sleep(0.01) #Надо внести в метод wait() класса Controller
    acs.wait()
    for ax in axes:
        if not ax['is_used']:
            acs.disable_axis(ax['number'])

    time.sleep(4)
    print('Стартуем из')
    PrintPosition()

    
    #Время начала измерений
    start_time = time.time()

    with open(FilePath+'.txt', 'x') as file:
        #Подготавливаем и записываем шапку в файл
        header = 'time, s\t'
        for ax in axes:
            header += ax['name'] + ' position, mm\t'
        header += graph_data
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
            #DEVICE.SingleMeasure() возвращает словарь вида {'VOLTage':value, }
            results = DEVICE.SingleMeasure()
            result_time = time.time() - start_time
            print(*FP, results[graph_data])
            
            #выполняем, если прибор вернул измерения
            if results:
                #формируем строку из списка данных и записываем в файл
                to_write = f'{result_time:.3f}\t{FP[0]:.3f}\t{FP[1]:.3f}\t{FP[2]:.3f}\t{FP[3]:.3f}\t'
                to_write = to_write + str(results[graph_data])
                file.write(to_write+'\n')
            #Записываем данные в файл, добавляем к спискам для графика и перестраиваем график
            #FPosition.append(pos_to_x(axes, FP))
            #FPosition.append(cpos)  #это будет график от номера в цикле
            FPosition.append(acs.get_fpos(axis_toX))
            Current.append(results[graph_data])
            plt.clf()
            plt.plot(FPosition, Current, color='#000066', lw=0.8, marker='o', markersize=1.5)
            plt.draw()
            plt.pause(0.01)
    
    #для TH1992B - отключаем канал
    if 'TH1992B' in DEVICE.Name:
        DEVICE.ChannelsTurnOff()
    #прерываем связь с прибором
    DEVICE.Close()
    
    plt.show()

except KeyboardInterrupt:
    file.close()
    #для TH1992B - отключаем канал
    if 'TH1992B' in DEVICE.Name:
        DEVICE.ChannelsTurnOff()
    #прерываем связь с прибором
    DEVICE.Close()
