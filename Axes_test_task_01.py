TH1992B_datanames = ('CURR1', 'CURR2')
TH2690A_datanames = ('CURR',)

EXPERIMENTS = [
    
    #******************************************************
    #Эксперимент №1
    {
        'APT': (-20, 20),
        'APL': (20, 20),
        'APR': (20, 20),
        'APB': (20, 20),
        
        'intervals': 800,
        
        'devices': {
            'tonghui_TH1992B': {
                'config': {'1': 'FDUCK_I', '2': 'APL_I'},
                'datanames': TH1992B_datanames
            },
            'tonghui_TH2690A': {
                'config': 'PICOAMMETER_TEST_1',
                'datanames': TH2690A_datanames
            }
        }
    },
    
    
    #******************************************************
    #Эксперимент №2
    {
        'APT': (20, 20),
        'APL': (20, -20),
        'APR': (20, 20),
        'APB': (20, 20),
        
        'intervals': 800,
        
        'devices': {
            'tonghui_TH1992B': {
                'config': {'1': 'FDUCK_I', '2': 'APL_I'},
                'datanames': TH1992B_datanames
            },
            'tonghui_TH2690A': {
                'config': 'PICOAMMETER_TEST_1',
                'datanames': TH2690A_datanames
            }
        }
    },
    
    
    
]