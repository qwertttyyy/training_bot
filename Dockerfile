FROM python:3.11

COPY . /training_bot

WORKDIR /training_bot

ENV PYTHONPATH "${PYTHONPATH}:/training_bot"

RUN pip install -r requirements.txt
RUN python3 bot/create_database.py
RUN apt-get update && apt install nano && apt install sqlite3


CMD python3 bot/main.py