#!/bin/bash

# Путь к виртуальному окружению (опционально)
VENV_PATH="./venv"

# Проверяем, существует ли виртуальное окружение и активируем его
if [ -d "$VENV_PATH" ]; then
    source "$VENV_PATH/bin/activate"
fi

# Запускаем бота
python main.py

# Если произошла ошибка, выводим сообщение
if [ $? -ne 0 ]; then
    echo "Ошибка при запуске бота"
    exit 1
fi