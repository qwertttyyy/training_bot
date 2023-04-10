from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    Filters,
)

from constants import TRAINER_ID

FEEl, PULS = range(2)


def send_report(update, context):
    # TODO: добавить проверку, что должен быть зареган
    #  отчёт отправляется тренеру в чат бота
    #  отдельная команда для вводы отчёта после тренировки, текст + фото
    if update.effective_chat.id != TRAINER_ID:
        update.message.reply_text(
            'Отправь отчёт о своём состоянии.\n'
            'Как ты себя сейчас чувствуешь (от 1 до 10) ?'
        )
        return FEEl
    update.message.reply_text('Ты тренер, тебе не нужно отправлять отчёты)')
    return ConversationHandler.END


def get_feeling(update, _):
    print(update.message.text)
    update.message.reply_text('Какой у тебя пульс?')
    return PULS


def get_puls(update, _):
    print(update.message.text)
    update.message.reply_text('Отчёт отправлен тренеру!')
    return ConversationHandler.END


def invalid_report(bot, _):
    bot.message.reply_text('Вводи только цифры соответствующие цифры!')


report_handler = ConversationHandler(
    entry_points=[CommandHandler('report', send_report)],
    states={
        FEEl: [MessageHandler(Filters.regex(r'^([1-9]|10)$'), get_feeling)],
        PULS: [MessageHandler(Filters.regex(r'^\d{2,3}$'), get_puls)],
    },
    fallbacks=[MessageHandler(Filters.regex, invalid_report)],
)
