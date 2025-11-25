from datetime import datetime
import time
import numpy as np
from Motion_control import Controller

acs = Controller(ip="192.168.88.10", port=701)

#Задержка перед измерением после остановки осей
t = 1

#Настройка осей. Для каждой оси нужно установить начальное и конечное положение.
#Если они совпадают, ось приедет туда и дальше использоваться не будет.
axes= [
       {'name':     'APT',  #не менять
       'number':    0,      #не менять
       'start':     3,
       'end':       7}, 
       
       {'name':     'APL',  #не менять
       'number':    1,      #не менять
       'start':     3,
       'end':       7}, 
       
       {'name':     'APR',  #не менять
       'number':    2,      #не менять
       'start':     3,
       'end':       7}, 
       
       {'name':     'APB',  #не менять
       'number':    3,      #не менять
       'start':     3,
       'end':       7}
       ]

#Количество интервалов (установить требуемое значение)
intervals = 20


ttc = {'t_op_start':0, 't_op_finish':0, 't_op_fact':0, }
meas_time = 2
t_calc = (intervals + 1) * meas_time

print(f'''\
Желаемое время измерения\t= {meas_time} сек
Количество измерений (точек)\t= {intervals + 1}
Ожидаемое время выполнения\t= {t_calc}
...........''')

def correct_sleep():

    #время, затраченное с момента начала измерений
    ttc['t_op_finish'] = time.time() - tt1
    ttc['t_op_fact'] = ttc['t_op_finish'] - ttc['t_op_start']

    time_to_sleep = meas_time - ttc['t_op_fact']
    
    if time_to_sleep > 0.001:
        time.sleep(time_to_sleep)
    else:
        #time.sleep(1)
        print(' _ ' + f'{datetime.now()}'[11:22]
              + f" - время итерации превышено (sleep = {time_to_sleep:.3f})")


#Добовляем к словарям осей массивы координат и информацию об их использовании
for ax in axes:
    
    ax['pos'] = np.linspace(ax['start'], ax['end'], intervals +1)
    ax['is_used'] = ax['start'] != ax['end']

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
    print(f"Время начала измерений: \t{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    tt1 = time.time()

    for cpos in range(intervals + 1):

        ttc['t_op_start'] = time.time() - tt1
        
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

        result_time = time.time() - tt1
        
        #Ждем, измеряем прибором Tonghui и время с начала эксперимента
        #time.sleep(t)
        correct_sleep()

    #считаем время, затраченное на выполнение программы
    tt2 = time.time()-tt1
    #вывод текущего времени
    print('...........')
    print('Время окончания измерений: \t'+f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f'Полное время\t= {tt2:.3f} сек')
    print(f'Ожидаемое время\t= {t_calc:.3f} сек')

except KeyboardInterrupt:

    pass
