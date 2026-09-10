import numpy as np

x = (-4.0, 8.0)
y = (-5.0, 7.0)
intervals = (48, 48)
gap = (0.5, 0.5)
delay = 0.0

intvls = intervals[0]
APL_S, APL_E = -x[0]+gap[0]/2, -x[1]+gap[0]/2
APR_S, APR_E = x[0]+gap[0]/2, x[1]+gap[0]/2

res = '#APT\tAPL\tAPR\tAPB\tintvls\tpost_delay\tfilename\n'


for z in np.linspace(y[0], y[1], intervals[1]+1):
    APT = z + gap[1]/2
    APB = -z + gap[1]/2
    res += f'{APT}\t{APL_S}:{APL_E}\t{APR_S}:{APR_E}\t{APB}\t{intvls}\t{delay}\t\n'
    APL_S, APL_E = APL_E, APL_S
    APR_S, APR_E = APR_E, APR_S

with open('EXP3_MAPPING_test.txt', 'w') as file:
    file.write(res)

