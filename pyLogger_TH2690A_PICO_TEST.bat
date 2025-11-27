@echo off
cls
set "SCRIPT_DIR=%~dp0"

:: Используемый прибор
:: tonghui_TH2690A, tonghui_TH1992B
:: Соответствует названию библиотеки прибора
set DeviceName=DeviceName:tonghui_TH2690A
:: Тип используемого подключения
:: TCPIP, USBTCM
set ConnectionMethod=ConnectionMethod:TCPIP
:: IP-адрес, установленный на приборе
set DeviceAddress=DeviceAddress:192.168.88.12
:: Порт подключения по TCPIP
set DevicePort=DevicePort:45454
:: Серийный номер прибора для подключения по USBTCM
set DeviceSerial=DeviceSerial:W152230156
:: Имя пресета настроек из ini файла
:: Для TH1992B - НомерКанала:ИмяПресета, получится dict
:: Измерения будут сниматься только с указанных каналов
:: ConfigName=ConfigName:1:TEST_VOLT,2:TEST_CURR
set ConfigName=ConfigName:PICOAMMETER_TEST_1
:: Желаемое время одного измерения, сек
:: Логгер будет рассчитывать и добавлять такую паузу,
:: чтобы время измерения получалось желаемым
:: Время одного запроса примерно равно 0.15 сек, 
:: отрисовки плота - примерно 0.1 сек
:: t_расч = t_одногозапроса + t_плота + aperture_прибора
set MeasTime=MeasTime:1
:: Количество измерений (точек) на эксперимент
set MeasPoints=MeasPoints:61
:: Количество точек по оси х на графике
set CanvasPoints=CanvasPoints:30
:: Создавать ли график
:: TRUE, FALSE
set EnablePlot=EnablePlot:TRUE
:: Имена данных, которые будут записаны в файл (VOLTage,CURR)
set DataNames=DataNames:VOLTage,CURR
:: Имена данных, которые будут на графике
set LineNames=LineNames:CURR
:: Название оси у на графике
set YLabel=YLabel:I,A
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