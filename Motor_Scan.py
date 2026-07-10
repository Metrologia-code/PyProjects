import matplotlib.pyplot as plt
from datetime import datetime
import time, sys
import numpy as np
import Tonghui_libs
from StepMotor_libs import StepMotor, RunCommand
from User_libs import CreateSavePath

DEVICE = Tonghui_libs.tonghui_TH2690A.Device()

# адрес подключенияк к tonghui_TH2690A
ConnectionDetails = {'ConnectionMethod': 'TCPIP',
                     'DeviceAddress': '192.168.88.12',
                     'DevicePort': '45454', }
# просто название пресета
tonghui_preset = 'FDUK'
# Выбираем, что писать в файл и строить на графике (VOLTage, CURR, RES)
graph_data = 'CURR'
save_data = (graph_data,)  # не менять

# пробуем подключиться к tonghui
if not DEVICE.Initialize(**ConnectionDetails):
    sys.exit(1)
# конфигурируем tonghui по пресету из ini-файла
if not DEVICE.ConfigureDevice(ConfigName=tonghui_preset, ):
    sys.exit(1)

# Списки для построения графика
FPosition = list()
Current = list()

# Задержка перед измерением после остановки мотора
t = 0.1

# Настройка движения в микрошагах
start_pos = - 5 * 400 * 8
end_pos = 5 * 400 * 8

# Количество интервалов (установить требуемое значение)
intervals = 1000

# Список координат
pos_list = np.linspace(start_pos, end_pos, intervals + 1)

# Открываем окно графика
fig = plt.figure(1, figsize=(8, 6))
fig.clf()

# генератор пути к папке, в которую будут сохраняться данные
# ВНИМАНИЕ! если путь не существует, то запись будет вестись в местную директорию Data
# SavePath = CreateSavePath(__file__, LAN_Path='\\\\MetroBulk\\Public\\EXP_DATA')
SavePath = CreateSavePath(LAN_Path='\\\\MetroBulk\\Public\\EXP_DATA', )
# генерируем уникальное имя файла и добавляем путь к нему
FilePath = SavePath + DEVICE.Name + ' ' + datetime.now().strftime("%Y-%m-%d %H-%M-%S") + '_motor_scan'

try:

    with open(FilePath + '.txt', 'x') as file, StepMotor() as motor:
        # Подготавливаем и записываем шапку в файл
        header = 'time, s\tposition, u_steps\t'
        header += '\t'.join(save_data)
        file.write(header + '\n')

        # Сбрасываем текущую позицию
        motor.reset_current_position()

        # Время начала измерений
        start_time = time.time()

        for cpos in pos_list:

            # Отправляем мотор в следущую точку
            motor.go_to(int(cpos))

            # Опрашиваем положение
            fpos = motor.current_position

            # Ждем, измеряем прибором Tonghui и время с начала эксперимента
            time.sleep(t)

            results = DEVICE.SingleMeasure()
            result_time = time.time() - start_time

            # выполняем, если прибор вернул измерения
            if results:
                # формируем строку из списка данных и записываем в файл
                to_write = f'{result_time:.3f}\t{fpos}'
                for el in save_data:
                    to_write += f'\t{results[el]:.3e}'
                print(to_write)
                file.write(to_write + '\n')



            # Записываем данные в файл, добавляем к спискам для графика и перестраиваем график

            FPosition.append(fpos)
            Current.append(results[graph_data])
            plt.clf()
            plt.plot(FPosition, Current, color='#000066', lw=0.8, marker='o', markersize=1.5)
            plt.draw()
            plt.pause(0.01)

    motor.go_home()

    # сохраняем рисунок
    plt.savefig(FilePath + '.png', dpi=600, bbox_inches='tight')

    #Записываем RUN в CMD-регистр.
    motor.command = RunCommand.RUN

except KeyboardInterrupt:
    print("Программа остановлена пользователем")

finally:
    DEVICE.Close()

    plt.show()
