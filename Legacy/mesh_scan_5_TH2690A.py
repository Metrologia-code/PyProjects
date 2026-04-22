import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import time
from datetime import datetime
import tonghui_TH2690A
from Controller import Controller

TH2690A = tonghui_TH2690A.Device()
acs = Controller(ip="192.168.88.10", port=701)

now = datetime.now().strftime("%Y%m%d_%H%M%S_")

# Параметры скана
X1, Xm, M = -6, 5, 12
Z1, Zn, N = 4, -6, 11
Gap = 1
t = 0.1

FileName = now + 'FDUK100uv_XUV.txt'
FileName1 = FileName[:-4] + '_coord' + '.txt'

# Создание координатных массивов
X = np.linspace(X1, Xm, M)
Z = np.linspace(Z1, Zn, N)

# Рассчет границ для центровки
dx = (X[1] - X[0]) if M > 1 else 1.0
dz = (Z[1] - Z[0]) if N > 1 else 1.0

# Граничные точки
X_edges = np.linspace(X[0] - dx / 2, X[-1] + dx / 2, M + 1)
Z_edges = np.linspace(Z[0] - dz / 2, Z[-1] + dz / 2, N + 1)

# Инициализация массива сигналов и таблицы с измерениями
Signal = np.full((N, M), np.nan)
Matrix = pd.DataFrame(Signal, columns=X, index=Z, copy=False)

# Создание фигуры
fig = plt.figure(num='Current Map', figsize=(10, 8), clear=True)  # clear=True для очистки предыдущего содержимого
ax = plt.gca()
ax.set(xlim=sorted([X_edges[0], X_edges[-1]]), ylim=sorted([Z_edges[-1], Z_edges[0]]), xlabel='X', ylabel='Z')
ax.set_aspect('equal')
im = ax.pcolormesh(X_edges, Z_edges, Signal, shading='flat', cmap='hot', edgecolor='k', lw=0.1)
plt.tight_layout()
plt.draw()
plt.pause(0.1)

try:

    acs.connect()
    TH2690A.Setup()
    TH2690A.Start()

    with open(FileName, 'w') as file, open(FileName1, 'w') as file_coord:

        # Обход массива "змейкой"
        for i in range(N):
            cols = range(M) if i % 2 == 0 else range(M - 1, -1, -1)
            for j in cols:
                x, z = X[j], Z[i]
                apt = z + Gap / 2
                apb = -z + Gap / 2
                apl = -x + Gap / 2
                apr = x + Gap / 2
                acs.ptp(0, apt)
                acs.ptp(3, apb)
                acs.ptp(1,apl)
                acs.ptp(2, apr)
                acs.wait()
                time.sleep(t)
                # Signal[i, j]=np.random.rand()
                Signal[i, j] = float(TH2690A.Measure()['curr'])

                # Обновление графика
                im.set_array((Signal.ravel()))
                im.set_clim(np.nanmin(Signal), np.nanmax(Signal))
                fig.canvas.draw_idle()
                plt.pause(0.01)

                # Вывод в консоль и файл
                print(f"({X[j]:.2f}, {Z[i]:.2f}): {Signal[i, j]:.3e}")
                file.write(f'{X[j]}\t{Z[i]}\t{Signal[i, j]}\n')
                file_coord.write(f'{apt}\t{apl}\t{apr}\t{apb}\t{Signal[i, j]}\n')

            print()

    Matrix.sort_index(ascending=False, inplace=True)
    Matrix.to_csv('Matrix_' + FileName, sep='\t')

    cbar = fig.colorbar(im, ax=ax)
    plt.savefig(FileName[:-4] + '.png', dpi=600, bbox_inches='tight')
    plt.show()

except KeyboardInterrupt:
    print("Программа остановлена пользователем")

finally:
    TH2690A.Close()
