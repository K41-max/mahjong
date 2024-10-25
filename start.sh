#!/bin/bash

# 仮想環境が存在するか確認
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Please run ./build.sh first."
    exit 1
fi

# 仮想環境を有効化
source venv/bin/activate

# アプリケーションを起動
echo "Starting the application with Uvicorn..."
uvicorn run:sio_app --host 0.0.0.0 --port 8000 --reload
