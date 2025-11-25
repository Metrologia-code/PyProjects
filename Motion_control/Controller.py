import socket
from struct import unpack
import numpy as np


class Controller:

    def __init__(self, ip="192.168.88.10", port=701):
        self.ip = ip
        self.port = port
        self.__sock = None
        self.__sock_err = (socket.error, socket.timeout, ConnectionError, TimeoutError)

    def connect(self):
        """Подключение к контроллеру"""
        self.__sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.__sock.connect((self.ip, self.port))
        except self.__sock_err as error:
            print(f"Following error occurred while connecting: <{error}>")

    @staticmethod
    def __command_to_pack(row: str, ans_type: str):
        if ans_type == '4':
            row = '%??\x04' + row
        elif ans_type == '8':
            row = '%??\x08' + row
        msg = b'\xd3\x00' + len(row).to_bytes(1, 'big') + b'\x00' + row.encode() + b'\xd6'
        return msg

    def __request_controller(self, com: str, ans_type='0'):
        msg = self.__command_to_pack(com, ans_type)
        self.__sock.send(msg)
        ans = self.__sock.recv(1024)[4:-1]
        if ans_type != '0':
            return ans

    def __real_feedback(self, msg: str):
        ans = self.__request_controller(msg, ans_type='8')
        return unpack('d', ans)[0]

    def __int_feedback(self, msg: str):
        ans = self.__request_controller(msg, ans_type='4')
        return int.from_bytes(ans, byteorder='little')

    def __get_limits(self, n_axis: int):
        msg = f'FAULT({n_axis},{n_axis})(0,0)'
        ans = self.__int_feedback(msg)
        state = hex(ans)
        left = (state[-1] == '2')
        right = (state[-1] == '1')
        return left, right

    def enable_axis(self, n_axis: int):
        """Включает ось с номером n_axis"""
        msg = f"ENABLE {n_axis}"
        self.__request_controller(msg)

    def kill_all(self):
        """Выключает все оси"""
        msg = f"KILL ALL"
        self.__request_controller(msg)

    def disable_axis(self, n_axis: int):
        """Выключает ось с номером n_axis"""
        msg = f"DISABLE {n_axis}"
        self.__request_controller(msg)

    def disconnect(self):
        """Выключает все оси, закрывает сокет общения с контроллером"""
        msg = 'DISABLE ALL'
        self.__request_controller(msg)
        self.__sock.close()

    def m_state(self, n_axis: int):
        """Возвращает строку-статус оси"""
        msg = f'MST({n_axis},{n_axis})(0,0)'
        ans = self.__int_feedback(msg)
        state = hex(ans)
        if state[-1] == '0':
            return 'OFF'
        else:
            if state[-2] == '1':
                left, right = self.__get_limits(n_axis)
                if left or right:
                    return 'ALARM'
                return 'ON'
            elif state[-2] == '2' or state[-2] == '6':
                return 'MOVING'
            else:
                return 'UNKNOWN'

    def get_fpos(self, n_axis: int):
        """Возвращает float значение текущей позиции оси с номером n_axis"""
        msg = f"FPOS({n_axis},{n_axis})(0,0)"
        return self.__real_feedback(msg)

    def set_fpos(self, n_axis: int, target: float):
        """Задает float значение текущей позиции оси с номером n_axis"""
        msg = f"SET FPOS({n_axis})={target}"
        self.__request_controller(msg)

    def get_apos(self, n_axis: int):
        """Возвращает float значение текущей позиции оси с номером n_axis"""
        msg = f"APOS({n_axis},{n_axis})(0,0)"
        return self.__real_feedback(msg)

    def get_vel(self, n_axis: int):
        """Возвращает float значение скорости оси с номером n_axis"""
        msg = f"VEL({n_axis},{n_axis})(0,0)"
        return self.__real_feedback(msg)

    def set_vel(self, n_axis: int, target: float):
        """Задает float значение скорости оси с номером n_axis"""
        msg = f"IMM VEL({n_axis})={target}"
        self.__request_controller(msg)

    def get_acc(self, n_axis: int):
        """Возвращает float значение ускорения оси с номером n_axis"""
        msg = f"ACC({n_axis},{n_axis})(0,0)"
        return self.__real_feedback(msg)

    def set_acc(self, n_axis: int, target: float):
        """Задает float значение ускорения оси с номером n_axis"""
        msg = f"IMM ACC({n_axis})={target}"
        self.__request_controller(msg)
        msg = f"IMM DEC({n_axis})={target}"
        self.__request_controller(msg)

    def get_jerk(self, n_axis: int):
        msg = f"JERK({n_axis},{n_axis})(0,0)"
        return self.__real_feedback(msg)

    def set_jerk(self, n_axis: int, target: float):
        msg = f"IMM JERK({n_axis})={target}"
        self.__request_controller(msg)
        msg = f"IMM KDEC({n_axis})={target}"
        self.__request_controller(msg)

    def get_limit_l(self, n_axis: int):
        """Возвращает Bool значение состояния концевика левого (True - если замкнут)"""
        return self.__get_limits(n_axis)[0]

    def get_limit_r(self, n_axis: int):
        """Возвращает Bool значение состояния концевика правого (True - если замкнут)"""
        return self.__get_limits(n_axis)[1]

    def to_point(self, n_axis: int, target: float):
        """Движение оси с номером n_axis к точке target"""
        msg = f"PTP {n_axis}, {target}"
        self.__request_controller(msg)
        while (True):
            msg = f'MST({n_axis},{n_axis})(0,0)'
            ans = self.__int_feedback(msg)
            state = hex(ans)
            #print(state[-2])
            if self.m_state(n_axis) == 'ALARM':
                print('some movement error')
                break
            if int(state[-2]) == 1:
                return
    
    def jog_ax(self, n_axis: int, direction='+'):
        """Движение оси с номером n_axis в направлении direction"""
        msg = f"JOG {n_axis},{direction}"
        self.__request_controller(msg)
        while (True):
            msg = f'MST({n_axis},{n_axis})(0,0)'
            ans = self.__int_feedback(msg)
            state = hex(ans)
            #print(state[-2])
            if self.m_state(n_axis) == 'ALARM':
                print('some movement error')
                break
            if int(state[-2]) == 1:
                return

    def halt_ax(self, n_axis: int):
        """Торможение оси с номером n_axis"""
        msg = f"HALT {n_axis}"
        self.__request_controller(msg)
        
    def mv(self,n_axis: int, target: float):
        """ Итеративное движение оси к FPOS - НЕ истользовать в Close-Loop"""
        tolerance = 0.03
        fpos = self.get_fpos(n_axis)
        delta=target-fpos
        while (np.abs(delta)>np.abs(tolerance)):
            msg = f"PTP/r {n_axis}, {delta}"
            self.__request_controller(msg)
            while (True):
                msg = f'MST({n_axis},{n_axis})(0,0)'
                ans = self.__int_feedback(msg)
                state = hex(ans)
                if self.m_state(n_axis) == 'ALARM':
                    print('some movement error')
                    return
                if int(state[-2]) == 1:
                    break
            fpos = self.get_fpos(n_axis)
            delta = target-fpos

    def get_safini(self, n_axis: int):
        msg = f'SAFINI({n_axis},{n_axis})(0,0)'
        ans = self.__int_feedback(msg)
        state = bin(ans)
        return state

    def get_safin(self, n_axis: int):
        msg = f'SAFIN({n_axis},{n_axis})(0,0)'
        ans = self.__int_feedback(msg)
        state = bin(ans)
        return state
        
    def get_fault(self, n_axis: int):
        msg = f'FAULT({n_axis},{n_axis})(0,0)'
        ans = self.__int_feedback(msg)
        state = bin(ans)
        return state

    def get_fmask(self, n_axis: int):
        msg = f'FMASK({n_axis},{n_axis})(0,0)'
        ans = self.__int_feedback(msg)
        state = bin(ans)
        return state
        
    def jog_all(self, n_axis: int, direction='+'):
        """Движение оси с номером n_axis в направлении direction"""
        msg = f"JOG {n_axis},{direction}"
        self.__request_controller(msg)
        
    def wait(self):
        ismov=True
        while (ismov==True):
            state0 = hex(self.__int_feedback('MST(0)'))
            state1 = hex(self.__int_feedback('MST(1)'))
            state2 = hex(self.__int_feedback('MST(2)'))
            state3 = hex(self.__int_feedback('MST(3)'))
            mm0=state0[-2] == '2' or state0[-2] == '6'
            mm1=state1[-2] == '2' or state1[-2] == '6'
            mm2=state2[-2] == '2' or state2[-2] == '6'
            mm3=state3[-2] == '2' or state3[-2] == '6'
            ismov = mm0 or mm1 or mm2 or mm3
            
    def ptp(self, n_axis: int, target: float):
        """Движение оси с номером n_axis к точке target"""
        msg = f"PTP {n_axis}, {target}"
        self.__request_controller(msg)

        
        
       