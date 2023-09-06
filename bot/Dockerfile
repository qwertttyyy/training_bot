FROM python:3.11

WORKDIR /app/bot/

ENV PYTHONPATH "${PYTHONPATH}:/app"
ENV TZ=Europe/Moscow

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

COPY requirements.txt .

RUN pip install -r requirements.txt --no-cache-dir
RUN apt update && apt install nano

COPY . .

CMD ["python", "main.py"]