import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# 1. Загрузка данных из файла
# Укажите имя вашего файла вместо 'experiment_data.txt'
file_path = "experiment_data.txt"

# delimiter='\t' жестко задает разделение по табуляции
# skiprows=1 пропускает строку с названиями колонок
data = np.loadtxt(file_path, delimiter="\t", skiprows=1)

# 2. Сбор значений координат и тока в массивы NumPy по индексам колонок
apt = data[:, 1]  # 2-я колонка
apl = data[:, 2]  # 3-я колонка
apr = data[:, 3]  # 4-я колонка
apb = data[:, 4]  # 5-я колонка
curr = data[:, 12]  # 13-я колонка (последняя)

# 3. Расчет координат x и y
x = (apr - apl) / 2
y = (apt - apb) / 2

# 4. Подготавливаем данные для построения
df = pd.DataFrame({'x': x, 'y': y, 'curr': curr})
pivot_df = df.pivot(index='y', columns='x', values='curr')

# 5. Построение хитмапа
# Создаём фигуру и оси
fig = plt.figure(num='Current Map', figsize=(12, 9))
ax = plt.gca()

# Делаем область построения квадратной
ax.set_aspect('equal')

# Строим сетку (хитмап)
plt.pcolormesh(pivot_df.columns, pivot_df.index, pivot_df.values, cmap='viridis', edgecolors='k', lw=0.1)

# Настройка оформления графика
cbar = plt.colorbar()
cbar.set_label("Ток TH2690A_1.CURR, А", fontsize=11)
plt.xlabel("x, мм", fontsize=11)
plt.ylabel("y, мм", fontsize=11)
plt.title("Карта значений тока", fontsize=12)
plt.grid(True, linestyle="--", alpha=0.5)

# Автоматически подгоняем размеры фигуры, чтобы всё влезло
plt.tight_layout()

# Сохранение графика в файл
plt.savefig(fname=file_path.split('.')[0] + '.png', dpi=300, bbox_inches='tight', format='png')

# Отображаем график на экране
plt.show()
