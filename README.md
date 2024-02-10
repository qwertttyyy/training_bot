# TrainingBot

## Описание проекта

TrainingBot - это бот для тренера и спортсменов в области легкой атлетики. Этот бот, созданный на Python и интегрированный с Telegram, позволяет спортсменам легко регистрироваться, вводить и отправлять данные о своем самочувствии и тренировках, а также автоматически синхронизировать данные о тренировках через сайт Strava. Для удобства хранения и анализа данных используется Google Sheets, где каждому спортсмену автоматически создается именной лист. Тренер может назначать задачи и просматривать данные о самочувствии и результаты тренировок своих подопечных, что делает процесс тренировки более организованным и эффективным.

### Основные функции:

- **Регистрация спортсменов** с созданием именного листа в Google Sheets.
- **Отправка данных о самочувствии** утром (оценка самочувствия, пульс, количество часов сна).
- **Отправка данных после тренировки** (дистанция, средний темп, средний пульс).
- **Автоматическая синхронизация данных тренировок** через сайт Strava.
- **Возможность тренера назначать задачи** на день или на неделю через интерфейс бота.

### Технологический стек:

- Python
- Python Telegram Bot
- Django
- django-social-auth
- Google API Python Client
- PostgreSQL
- Docker


### В планах
На данные момент в разработке находится новая версия бота с использованием асинхронности и бэкендом на Django.
