@echo off
cls
set "SCRIPT_DIR=%~dp0"

:: Используемый прибор
:: tonghui_TH2690A, tonghui_TH1992B
:: Соответствует названию библиотеки прибора
set DeviceName=DeviceName:tonghui_TH1992B
:: Тип используемого подключения
:: TCPIP, USBTCM
set ConnectionMethod=ConnectionMethod:TCPIP
:: IP-адрес, установленный на приборе
set DeviceAddress=DeviceAddress:192.168.88.11
:: Порт подключения по TCPIP
set DevicePort=DevicePort:45454
:: Серийный номер прибора для подключения по USBTCM
set DeviceSerial=DeviceSerial:W152230156
:: Имя пресета настроек из ini файла
:: Для TH1992B - НомерКанала:ИмяПресета, получится dict
:: Измерения будут сниматься только с указанных каналов
set ConfigName=ConfigName:1:Pt100_4w,2:Pt100_2w
:: Желаемое время одного измерения, сек
:: Логгер будет рассчитывать и добавлять такую паузу,
:: чтобы время измерения получалось желаемым
:: Время одного запроса примерно равно 0.15 сек, 
:: отрисовки плота - примерно 0.1 сек
:: t_расч = t_одногозапроса + t_плота + aperture_прибора
set MeasTime=MeasTime:0.5
:: Количество измерений (точек) на эксперимент
set MeasPoints=MeasPoints:72001
:: Количество точек по оси х на графике
set CanvasPoints=CanvasPoints:300
:: Создавать ли график
:: TRUE, FALSE
set EnablePlot=EnablePlot:TRUE
:: Имена данных, которые будут записаны в файл
:: Для TH1992B полный набор данных с двух каналов выглядит так:
:: VOLTage1,CURR1,RES1,VOLTage2,CURR2,RES2
set DataNames=DataNames:VOLTage1,CURR1,RES1,VOLTage2,CURR2,RES2
:: Имена данных, которые будут на графике
:: Для TH1992B добавить номер канала -  VOLTage1,CURR1,..
set LineNames=LineNames:RES1,RES2
:: Название оси у на графике
set YLabel=YLabel:Temp,C
:: Преобразовывать ли измеренные данные
:: TRUE, FALSE
set YTransform=YTransform:FALSE

python "%SCRIPT_DIR%pyLogger.py" ^
%DeviceName% ^
%ConnectionMethod% ^
%DeviceAddress% ^
%DevicePort% ^
%DeviceSerial% ^
%ConfigName% ^
%MeasTime% ^
%MeasPoints% ^
%CanvasPoints% ^
%EnablePlot% ^
%DataNames% ^
%LineNames% ^
%YLabel% ^
%YTransform%

pause