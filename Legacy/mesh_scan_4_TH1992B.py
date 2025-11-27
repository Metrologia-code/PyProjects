import numpy as np
import matplotlib.pyplot as plt
import time
from tonghui_TH1992B import Device
TH1992B = Device()
from Controller import Controller
acs = Controller(ip="192.168.88.10", port=701)
acs.connect()

# Параметры скана
X1, Xm, M = -10, 10, 11
Z1, Zn, N = 10, -10, 11
Gap = 2
t = 1

FileName = '20250913_FDUK2_afterM1_test.txt'

file = open(FileName, 'w')
# Создание координатных массивов
X = np.linspace(X1, Xm, M)
Z = np.linspace(Z1, Zn, N)
# Рассчет границ для центровки
dx = (X[1] - X[0]) if M > 1 else 1.0
dz = (Z[1] - Z[0]) if N > 1 else 1.0
# Граничные точки
X_edges = np.linspace(X[0] - dx/2, X[-1] + dx/2, M + 1)
Z_edges = np.linspace(Z[0] - dz/2, Z[-1] + dz/2, N + 1)

# Инициализация массива сигналов
Signal = np.zeros((N, M))

# Создание фигуры
fig = plt.figure(num=10, figsize=(10, 8), clear=True)  # clear=True для очистки предыдущего содержимого
ax = plt.gca()
ax.set(xlim=(X_edges[0], X_edges[-1]), ylim=(Z_edges[-1], Z_edges[0]), xlabel='X', ylabel='Z')
ax.set_aspect('equal') 
im = ax.pcolormesh(X_edges, Z_edges, Signal, shading='flat', cmap='hot', edgecolor='k', lw=0.1)
plt.tight_layout()
plt.draw()
plt.pause(0.1)

# Обход массива "змейкой"
for i in range(N):
    cols = range(M) if i % 2 == 0 else range(M-1, -1, -1)
    for j in cols:
        x=X[j]
        z=Z[i]
        acs.ptp(0, z+Gap/2)
        acs.ptp(3,-z+Gap/2) 
        acs.ptp(1,-x+Gap/2) 
        acs.ptp(2, x+Gap/2) 
        acs.wait()
        
        # Signal[i, j]=np.random.rand()
        Signal[i, j] = TH1992B.Measure(['R2'])[0]
        time.sleep(5)
        # Обновление графика
        im.set_array((Signal.ravel()))
        im.set_clim(Signal.min(), Signal.max())
        fig.canvas.draw_idle()
        plt.pause(0.01)
        
        # Вывод в консоль и файл
        print(f"({X[j]:.2f}, {Z[i]:.2f}): {Signal[i, j]:.3e}")
        file.write(f'{X[j]}\t{Z[j]}\t{Signal[i, j]}\n')
        #time.sleep(t)
    print()
    
cbar = fig.colorbar(im, ax=ax)
plt.show()
file.close()
np.savetxt('Matrix_'+FileName, Signal)
file.close()
