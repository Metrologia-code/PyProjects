import pyvisa
#import time

class Device():
    
    def __init__(self, ):
        
        rm = pyvisa.ResourceManager()
        
        DeviceAddress = '192.168.88.11'
        DevicePort = '45454' #'45454'
        TCPIP = f'TCPIP0::{DeviceAddress}::{DevicePort}::SOCKET'
        
        DeviceSerial = 'W152230154'
        #'ASRL5::INSTR'
        #USB0::0x1105::0x1992::W152230154::INSTR
        USB, USBtype = '', ''
        res = rm.list_resources()
        #print(res)
        for i in res:
            if DeviceSerial in i:
                USB, USBtype = i, 'USB TCM'
            else:
                #предполагаем, что наш девайс - первый в списке
                USB, USBtype = res[0], 'USB CDC'
        
        try:
            self.tonghui = rm.open_resource(TCPIP, read_termination='\n')
            print(f'{self.tonghui.query("*IDN?")} - подключено по TCPIP')
        except:
            try:
                self.tonghui = rm.open_resource(USB, )
                print(f'{self.tonghui.query("*IDN?")} - подключено по {USBtype}')
                #self.tonghui.baud_rate = 115200
            except:
                print('не подключено')

        self.commands = {'V1':'VOLT? (@1)', 'C1':'CURR? (@1)', 'R1':'RES? (@1)',
                         'V2':'VOLT? (@2)', 'C2':'CURR? (@2)', 'R2':'RES? (@2)',}

    
    def Measure(self, measures, ):

        results = []
        
        for m in measures:
            command = ':MEAS:'+self.commands[m]
            results.append(float(self.tonghui.query(command)))
            #time.sleep(sleep)
        return results

    def Close(self):

        self.tonghui.close()