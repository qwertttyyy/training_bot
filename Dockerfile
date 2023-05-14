FROM python:3.11

COPY . /training_bot

WORKDIR /training_bot

ENV TZ=Europe/Moscow
ENV PYTHONPATH "${PYTHONPATH}:/training_bot"

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN pip install -r requirements.txt
RUN apt-get update && apt install nano && apt install sqlite3

CMD python3 bot/main.py