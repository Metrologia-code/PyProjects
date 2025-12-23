import cv2
from datetime import datetime, timedelta
import time
import numpy as np

rtsp_url = "rtsp://admin:yDAPqf31@192.168.88.22:554/cam/realmonitor?channel=1&subtype=0"
camera_name = "Dahua_192.168.88.22"

# здесь задать продолжительность работы
delta = timedelta(days=0, seconds=0, minutes=2, hours=0)
stop_datetime = datetime.now() + delta
print('Автозапись изображений в файлы до ', stop_datetime)

cv2.namedWindow(camera_name, cv2.WINDOW_NORMAL)
while datetime.now() < stop_datetime:
    cap = cv2.VideoCapture(rtsp_url)
    if not cap.isOpened():
        print("Error: Could not open camera.")
        break
    ret, frame = cap.read()
    if not ret:
        print("Error: Could not read frame.")
        break

    current_datetime = datetime.now()
    f_time = current_datetime.strftime("%d-%B-%Y_%H-%M-%S")
    fname = "DAHUA_" + f_time + ".jpg"
    # можно изменить расширение, если нужен другой формат файла
    cv2.imwrite(fname, frame)
    print('Записан файл: ', fname)

    cv2.imshow(camera_name, frame)
    # print(np.size(frame))
    cv2.resizeWindow(camera_name, 640, 480)
    cv2.waitKey(25)
    cap.release()

    time.sleep(3)  # установить здесь период записи файлов в секундах

cv2.destroyAllWindows()
