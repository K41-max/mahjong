# ベースイメージを指定
FROM python:3.9-slim

# 作業ディレクトリを設定
WORKDIR /app

# 必要なパッケージ情報をコピー
COPY requirements.txt .

# 依存関係をインストール
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# アプリケーションのソースコードをコピー
COPY . .

# ポートを公開
EXPOSE 8000

# アプリケーションを起動
CMD ["uvicorn", "run:sio_app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
