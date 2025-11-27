# import matplotlib.pyplot as plt

from Controller import Controller
acs = Controller(ip="192.168.88.10", port=701)
acs.connect()

#  Присвоение значение в крайней позиции FPOS


Top = -28.40 # Axis 0    ---- Position in a left limit!!!!
Left = -21.35 # Axis 1   ---- Position in a left limit!!!!
Right = -28.83 # Axis 2  ---- Position in a left limit!!!!
Bottom = -23.00 # Axis 3 ---- Position in a left limit!!!!

SetFPOS = (Top, Left, Right, Bottom)

LLsafini=[0,0,0,0];
RLsafini=[0,0,0,0];
LLfmask=[0,0,0,0];
RLfmask=[0,0,0,0];

for axis_index in [0,1,2,3]:
    # Проверка инверсии в значениях FAULT, правильное значение - 1 (True)
    safini_state = acs.get_safini(axis_index)
    nonzero_safini_state_bits=len(safini_state)-2
    LLsafini[axis_index]=safini_state[-2]
    RLsafini[axis_index]=safini_state[-1]
    print(f'Inversion state for axis {axis_index}: \nLeft limit is {LLsafini[axis_index]} \nRight limit is {RLsafini[axis_index]}')
    
    # Проверка "маски" в значениях FAULT, правильное значение - 1 (True)
    fmask_state = acs.get_fmask(axis_index)
    LLfmask[axis_index]=fmask_state[-2]
    RLfmask[axis_index]=fmask_state[-1]
    print(f'FMask state for axis {axis_index}: \nLeft limit is {LLfmask[axis_index]} \nRight limit is {RLfmask[axis_index]}')

if LLsafini==['1','1','1','1'] and RLsafini==['1','1','1','1'] and LLfmask==['1','1','1','1'] and RLfmask==['1','1','1','1']:
    print('SAFINI & FMASK STATE CHECKED')
    for axis_index in [0,1,2,3]:
        # СМЕНА НАПРАВЛЕНИЯ ДВИЖЕНИЯ: '+' полностью открыть и '-' полностью закрыть
        acs.jog_all(axis_index, direction='-')
        # acs.jog_ax(axis_index, direction='+')
    acs.wait()
    for axis_index in [0,1,2,3]:    
        acs.set_fpos(axis_index, SetFPOS[axis_index])


