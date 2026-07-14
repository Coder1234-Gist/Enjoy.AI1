FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# SQLite file lives outside the image so it survives container rebuilds
VOLUME ["/app/data"]
ENV DB_PATH=/app/data/bot_data.db

CMD ["python", "main.py"]
