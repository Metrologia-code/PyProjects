import pyvisa
import time

class Device():
    
    def __init__(self, formatdata=[], ):
        
        rm = pyvisa.ResourceManager()
        
        DeviceAddress = '192.168.88.12'
        DevicePort = '45454'
        TCPIP = f'TCPIP0::{DeviceAddress}::{DevicePort}::SOCKET'
        
        #DeviceSerial = 'R10B230127'
        #'ASRL5::INSTR'
        #USB0::0x1105::0x1992::R10B230127::INSTR
        
        try:
            self.tonghui = rm.open_resource(TCPIP, read_termination='\n')
            print(f'{self.tonghui.query("*IDN?")} - подключено по TCPIP')
        except:
            #self.tonghui = rm.open_resource(USB, )
            #print(f'{self.tonghui.query("*IDN?")} - подключено по {USBtype}')
            print('не подключено')
    
    
    def Setup(self, ):
        
        #MeasSet
        #Function 'FUNC:FUNC RES|VOLT|CURR|SRC'
        self.tonghui.write('FUNC:FUNC CURR')
        #Range 'RES|VOLT|CURR:RANGE <>'
        #self.tonghui.write('CURR:RANGE 5')
        #Speed 'RES|VOLT|CURR:SPEED FAST|MID|SLOW'
        self.tonghui.write('CURR:SPEED MID')
        
        
    def Start(self, ):
        
        #Source switch 'FUNC:SRC ON|OFF'
        self.tonghui.write('FUNC:SRC OFF')
        #Ammeter switch 'FUNC:AMMET ON|OFF'
        self.tonghui.write('FUNC:AMMET ON')
        #Run/Stop measurement 'FUNC:RUN|STOP'
        time.sleep(1) #если не подождать, то измерение стартанет, но кнопка не загорится
        self.tonghui.write('FUNC:RUN')
        
        self.tonghui.write('DISP:PAGE MEAS')

    
    def Measure(self, ):
        
        all_results = self.tonghui.query('FETCH:ALL?').split(',')
        
        results = {'volt':all_results[0],
                   'curr':all_results[1],
                   'char':all_results[2],
                   'time':all_results[3],
                   'vsource':all_results[4],
                   'math':all_results[5],
                   'temp':all_results[6],
                   'hum':all_results[7],
                  }
            
        return results
        
    
    def Close(self):

        time.sleep(1)
        self.tonghui.write('FUNC:STOP')
        time.sleep(1)
        self.tonghui.write('FUNC:AMMET OFF')
        time.sleep(1)
        self.tonghui.write('FUNC:SRC OFF')
        time.sleep(1)
        
        self.tonghui.close()