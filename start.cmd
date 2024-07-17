@echo off
REM Перейти в директорию скрипта
cd /d %~dp0

REM Активировать виртуальное окружение
call venv\Scripts\activate

REM Запустить python main.py
python main.py