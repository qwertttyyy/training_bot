FROM python:3.11

COPY . /training_bot

WORKDIR /training_bot

ENV TZ=Europe/Moscow
ENV PYTHONPATH "${PYTHONPATH}:/training_bot"

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN pip install -r requirements.txt
# RUN apt-get update && apt install nano && apt install sqlite3

RUN python bot/create_database.py
RUN python strava_app/manage.py migrate

# CMD ["gunicorn", "--bind", "0.0.0.0:8000", "strava_app.strava_app.wsgi"]
CMD ["python", "bot/main.py", "&&", "python", "strava_app/manage.py", "runserver", "0.0.0.0:8000"]
