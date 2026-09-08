import matplotlib.pyplot as plt
import numpy as np

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

# Опционально: переводим ток в наноамперы (нА) для удобства отображения порядка величин
curr_nA = curr * 1e9

# 4. Построение хитмапа
plt.figure(figsize=(8, 6))

# plt.tripcolor строит сетку (хитмап) по произвольным/неравномерным координатам x, y
heatmap = plt.tripcolor(x, y, curr_nA, cmap="viridis", shading="flat")

# Наносим точки измерений поверх, чтобы видеть, где физически проходил датчик
plt.scatter(
    x, y, c=curr_nA, cmap="viridis", edgecolors="black", linewidths=0.5, s=50
)

# Настройка оформления графика
cbar = plt.colorbar(heatmap)
cbar.set_label("Ток TH2690A_1.CURR (нА)", fontsize=11)

plt.xlabel("x = (APR - APL) / 2, мм", fontsize=11)
plt.ylabel("y = (APT - APB) / 2, мм", fontsize=11)
plt.title("Карта значений тока в координатах позиционирования", fontsize=12)
plt.grid(True, linestyle="--", alpha=0.5)

plt.tight_layout()
plt.show()
