FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt --no-cache-dir

COPY . .

CMD bash -c "sleep 3 && \
             python manage.py makemigrations && \
             python manage.py migrate && \
             python manage.py runserver 0.0.0.0:8000"