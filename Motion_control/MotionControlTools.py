def InitSpeed(acs):
    for ax in range(4):
        if acs.m_state(ax) == 'OFF':
            acs.enable_axis(ax)
            print(f"Ось {ax} была выключена, включаем")
    for ax in range(4):
        acs.set_vel(ax,1)    # скорость
        acs.set_acc(ax,5)    # ускорение/торможение
        acs.set_jerk(ax,25)  # скорость изменения ускорения

def PrintPosition(acs):
    print('APT/APL/APR/APB = ', round(acs.get_fpos(0), 3), '/',
          round(acs.get_fpos(1), 3), '/',
          round(acs.get_fpos(2), 3), '/',
          round(acs.get_fpos(3), 3))
    print()

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

def MoveBlades(acs, axes, cpos):
    import time
    if cpos == 0:
        # На первом шаге отправляем ВСЕ оси в start
        for ax in axes:
            acs.ptp(ax['number'], ax['pos'][cpos])
    else:
        # На остальных шагах двигаем только используемые оси
        for ax in axes:
            if ax['is_used']:
                acs.ptp(ax['number'], ax['pos'][cpos])
    time.sleep(0.01)
    acs.wait()