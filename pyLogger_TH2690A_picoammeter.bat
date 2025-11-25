@echo off
cls

:: Используемый прибор
:: "tonghui_TH2690A" либо "tonghui_TH1992B"
set NAME="tonghui_TH2690A"

:: Для tonghui_TH2690A заполнять только PRESET1, второй должен быть, но неиспользуется
set PRESET1="PICOAMMETER_TEST_1"
set PRESET2="DEFAULT"

:: период опроса прибора
set T_OP="1"

:: количество точек в течении эксперимента
set PTS="2161"

:: количество точек, отображаемых на графике
set X_PTS="120"

:: Отбражать ли график
:: TRUE, FALSE
set T_PLOT="TRUE"

:: пересчет  сопротивления в температуру для отображения на графики для tonghui_TH1992B
:: "RES2T, 0, 7.8", "FALSE"
set TFORM="FALSE"

set FORMAT="VOLT,CURR"
set CHANNELS="@1"

set Y_LABEL="Current, A"
set Y_DATA="CURR1"

pushd %~dp0

python .\pyLogger.py %NAME% %PRESET1% %PRESET2% %T_OP% %PTS% %X_PTS% %T_PLOT% %TFORM% %Y_LABEL% %Y_DATA% %FORMAT% %CHANNELS%
popd
pause