FROM python:3.11

COPY . /training_bot

WORKDIR /training_bot

ENV PYTHONPATH "${PYTHONPATH}:/training_bot"

RUN pip install -r requirements.txt
RUN python3 bot/create_database.py


CMD python3 bot/main.py