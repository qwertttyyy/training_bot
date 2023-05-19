FROM python:3.11

WORKDIR /app/bot/

ENV PYTHONPATH "${PYTHONPATH}:/app"

COPY requirements.txt .

RUN pip install -r requirements.txt --no-cache-dir

COPY . .


CMD ["python", "main.py"]