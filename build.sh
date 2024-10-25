#!/bin/bash

# 仮想環境が存在しない場合は作成
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# 仮想環境を有効化
source venv/bin/activate

# 依存関係をインストール
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Build completed."
