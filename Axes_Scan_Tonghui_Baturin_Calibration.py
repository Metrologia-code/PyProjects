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

def WriteHeaderToFile(file, axes, graph_data):
    header = 'time, s\t'
    for ax in axes:
        header += ax['name'] + ' position, mm\t'
    header += graph_data
    file.write(header + '\n')

def AxesToStart(axes):
    print()
    print('Текущее положение')
    PrintPosition()
    #Устанавливаем оси в начальное положение и ненужные отключаем
    for ax in axes:
        acs.enable_axis(ax['number'])
        time.sleep(0.30) #Надо внести задержку либо проверку статуса в метод enable_axis() класса Controller
        acs.ptp(ax['number'], ax['start'])
    time.sleep(0.01) #Надо внести в метод wait() класса Controller
    print('Движемся в начальное положение...')
    acs.wait()
    for ax in axes:
        if not ax['is_used']:
            acs.disable_axis(ax['number'])
    print('Стартуем из')
    PrintPosition()

def PosToAxis(axes, intervals):
    #Добавляем к словарям осей массивы координат и информацию об их использовании
    for ax in axes:
        ax['pos'] = np.linspace(ax['start'], ax['end'], intervals + 1)
        ax['is_used'] = ( ax['start'] != ax['end'] )

def MainMeasure(axes, intervals, axisX = 0):
    #Списки для построения графика
    FPosition = list()
    Current_TH1992B = list()
    Current_TH2690A = list()

    #Открываем окно графика
    fig, (axTH1992B, axTH2690A) = plt.subplots(2, 1, figsize=(8, 6))

    #генерируем уникальное имя файла и добавляем путь к нему
    FilePath = SavePath + 'Baturin_Calibration_' + datetime.now().strftime("%Y-%m-%d %H-%M-%S")

    try:
        AxesToStart(axes)
        #Время начала измерений
        start_time = time.time()

        with open(FilePath+'.txt', 'x') as file:
            #Подготавливаем и записываем шапку в файл
            WriteHeaderToFile(file, axes, 'APT current, A\tPhotodiode current, A')

            for cpos in range(intervals + 1):
                #Отправляем используемые оси в следущую точку
                for ax in axes:
                    if ax['is_used']:
                        acs.ptp(ax['number'], ax['pos'][cpos])
                time.sleep(0.01) #Надо внести в метод wait() класса Controller
                acs.wait()

                #Опрашиваем положение всех осей
                FP = [acs.get_fpos(ax['number']) for ax in axes]
                
                #Ждем, измеряем прибором Tonghui и время с начала эксперимента
                #Задержка перед измерением после остановки осей
                time.sleep(0.1)
                #DEVICE.SingleMeasure() возвращает словарь вида {'VOLTage':value, }
                dataTH1992B = eTH1992B.SingleMeasure()
                dataTH2690A = eTH2690A.SingleMeasure()
                result_time = time.time() - start_time
                to_write = f'{result_time:.3f}\t'          
                to_write = to_write + f'{FP[0]:.3f}\t{FP[1]:.3f}\t{FP[2]:.3f}\t{FP[3]:.3f}\t'
                to_write = to_write + str(dataTH1992B['CURR2']) + '\t'
                to_write = to_write + str(dataTH2690A['CURR'])
                print(to_write)
                file.write(to_write+'\n')

                #fig.clf()
                FPosition.append(FP[axisX])
                # На график выводим показания TH1992B, а по оси абсцисс axisX
                Current_TH1992B.append(dataTH1992B['CURR2'])
                # На график выводим показания TH2690A, а по оси абсцисс axisX
                Current_TH2690A.append(dataTH2690A['CURR'])
                #plt.show()
                #fig.canvas.draw()
                #fig.canvas.flush_events()
                
        axTH1992B.plot(FPosition, Current_TH1992B, 
                       color='#000066', lw=0.8, marker='o', markersize=1.5)
        axTH2690A.plot(FPosition, Current_TH2690A, 
                       color='#000066', lw=0.8, marker='o', markersize=1.5)
        plt.show()
        plt.pause(0.1)
        print('Закончил серию')
        file.close()
    except KeyboardInterrupt:
        file.close()
        print('У нас ошибка...')


eTH1992B = tonghui_TH1992B.Device()
ConnectionDetails = {'ConnectionMethod':'TCPIP',
                     'DeviceAddress':'192.168.88.11',
                     'DevicePort':'45454', }
tonghui_preset = {'2':'APL_I', }
if not eTH1992B.Initialize(**ConnectionDetails):
    sys.exit(1)
if not eTH1992B.ConfigureDevice(ConfigName=tonghui_preset, ):
    sys.exit(1)  

  
eTH2690A = tonghui_TH2690A.Device()
ConnectionDetails = {'ConnectionMethod':'TCPIP',
                     'DeviceAddress':'192.168.88.12',
                     'DevicePort':'45454', }
tonghui_preset = 'PICOAMMETER_TEST_1'
if not eTH2690A.Initialize(**ConnectionDetails):
    sys.exit(1)
if not eTH2690A.ConfigureDevice(ConfigName=tonghui_preset, ):
    sys.exit(1)  


#подключаемся к контроллеру моторов осей и устанавливаем скорости движения
acs = Controller(ip="192.168.88.10", port=701)
acs.connect()
InitSpeed()

#генератор пути к папке, в которую будут сохраняться данные
#ВНИМАНИЕ! если путь не существует, то запись будет вестись в местную директорию Data
#SavePath = CreateSavePath(__file__, LAN_Path='\\\\MetroBulk\\Public\\EXP_DATA')
SavePath = CreateSavePath(LAN_Path='\\\\MetroBulk\\Public\\EXP_DATA', )
    
#Настройка осей. Для каждой оси нужно установить начальное и конечное положение.
#Если они совпадают, ось приедет туда и дальше использоваться не будет.
axes= [
       {'name':     'APT',  #не менять
       'number':    0,      #не менять
       'start':     -6,
       'end':       6}, 
       
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
       'start':     2,
       'end':       2}
       ]
PosToAxis(axes, intervals = 60)
MainMeasure(axes, intervals = 60, axisX = 0)

axes= [
       {'name':     'APT',  #не менять
       'number':    0,      #не менять
       'start':     -6,
       'end':       6}, 
       
       {'name':     'APL',  #не менять
       'number':    1,      #не менять
       'start':     20,
       'end':       20}, 
       
       {'name':     'APR',  #не менять
       'number':    2,      #не менять
       'start':     20,
       'end':       20}, 
       
       {'name':     'APB',  #не менять
       'number':    3,      #не менять
       'start':     20,
       'end':       20}
       ]
PosToAxis(axes, intervals = 60)
MainMeasure(axes, intervals = 60, axisX = 0)

axes= [
       {'name':     'APT',  #не менять
       'number':    0,      #не менять
       'start':     6,
       'end':       6}, 
       
       {'name':     'APL',  #не менять
       'number':    1,      #не менять
       'start':     -10,
       'end':       20}, 
       
       {'name':     'APR',  #не менять
       'number':    2,      #не менять
       'start':     20,
       'end':       20}, 
       
       {'name':     'APB',  #не менять
       'number':    3,      #не менять
       'start':     20,
       'end':       20},
       ]
PosToAxis(axes, intervals = 60)
MainMeasure(axes, intervals = 60, axisX = 1)

axes= [
       {'name':     'APT',  #не менять
       'number':    0,      #не менять
       'start':     0,
       'end':       0}, 
       
       {'name':     'APL',  #не менять
       'number':    1,      #не менять
       'start':     -10,
       'end':       20}, 
       
       {'name':     'APR',  #не менять
       'number':    2,      #не менять
       'start':     6,
       'end':       6}, 
       
       {'name':     'APB',  #не менять
       'number':    3,      #не менять
       'start':     6,
       'end':       6}
       ]
PosToAxis(axes, intervals = 60)
MainMeasure(axes, intervals = 60, axisX = 1)

axes= [
       {'name':     'APT',  #не менять
       'number':    0,      #не менять
       'start':     0,
       'end':       0}, 
       
       {'name':     'APL',  #не менять
       'number':    1,      #не менять
       'start':     6,
       'end':       6}, 
       
       {'name':     'APR',  #не менять
       'number':    2,      #не менять
       'start':     -10,
       'end':       20}, 
       
       {'name':     'APB',  #не менять
       'number':    3,      #не менять
       'start':     6,
       'end':       6}
       ]
PosToAxis(axes, intervals = 60)
MainMeasure(axes, intervals = 60, axisX = 2)

#для TH1992B - отключаем канал
eTH1992B.ChannelsTurnOff()
#прерываем связь с прибором
eTH1992B.Close()
eTH2690A.Close()
