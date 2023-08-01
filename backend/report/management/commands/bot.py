import logging
import requests

from django.core.management.base import BaseCommand
from django.conf import settings
from pathlib import Path
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    CommandHandler,
    CallbackContext,
    ConversationHandler,
    MessageHandler,
    Updater,
    Filters,
)

from report.models import Employee


logging.basicConfig(
    level=logging.INFO,
    filename=Path('program.log'),
    filemode='w',
    format=(
        '%(name)s - %(asctime)s - %(levelname)s - %(lineno)d - %(message)s - %(funcName)s'
    ),
)

EMPLOYEE, ORDER, ITEM_ORDER, EXECUTION_TIME, IMAGE = 'employee', 'order', 'item_order', 'execution_time', 'image'


def start(update: Update, context: CallbackContext) -> int:
    Employee.objects.get_or_create(external_id=update.effective_chat.id)
    button = ReplyKeyboardMarkup(
        [['Отчет о проделанной работе'], ['Отчет об уборке рабочего места']],
        resize_keyboard=True,
    )
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text='Здравствуйте! Пожалуйста, выберите тип отчета',
        reply_markup=button,
    )


def work_report(
        update: Update,
        context: CallbackContext,
) -> int:
    context.user_data[EMPLOYEE] = Employee.objects.get(external_id=update.effective_chat.id).id
    update.message.reply_text(
        'Введите номер счета что бы продолжить',
        reply_markup=ReplyKeyboardRemove(),
    )
    return ORDER


def order_handler(
        update: Update,
        context: CallbackContext
) -> int:
    context.user_data[ORDER] = int(update.message.text)
    update.message.reply_text(
        'Введите порядковый номер позиции из счета',
    )
    return ITEM_ORDER


def item_handler(
        update: Update,
        context: CallbackContext
) -> int:
    context.user_data[ITEM_ORDER] = int(update.message.text)
    update.message.reply_text('Укажите время выполнения в минутах')
    return EXECUTION_TIME


def time_handler(
        update: Update,
        context: CallbackContext
) -> int:
    context.user_data[EXECUTION_TIME] = int(update.message.text)
    update.message.reply_text('Приложите фотографию')
    return IMAGE


def image_handler(
        update: Update,
        context: CallbackContext
) -> int:
    
    context.user_data[IMAGE] = ""
    update.message.reply_text('Спасибо! Отчет отправлен!')
    requests.post(settings.ENDPOINT, json=context.user_data)
    print(context.user_data)
    return ConversationHandler.END


def cancel_handler(
        update: Update,
        context: CallbackContext
) -> int:
    update.message.reply_text('Отчет не отправлен')
    return ConversationHandler.END


def after_work_report(
        update: Update,
        context: CallbackContext,
) -> int:
    chat = update.effective_chat
    context.bot.send_message(
        chat_id=chat.id,
        text='Отчет об уборке рабочего места',
    )


class Command(BaseCommand):
    help = 'Telegram-бот'

    def handle(self, *args, **options):
        updater = (
            Updater(token=settings.TELEGRAM_TOKEN)
        )

        report_handler = ConversationHandler(
            entry_points=[
                MessageHandler(
                    Filters.text('Отчет о проделанной работе'),
                    work_report,
                ),
            ],
            states={
                ORDER: [
                    MessageHandler(
                        Filters.all,
                        order_handler,
                    ),
                ],
                ITEM_ORDER: [
                    MessageHandler(
                        Filters.all,
                        item_handler,
                    ),
                ],
                EXECUTION_TIME: [
                    MessageHandler(
                        Filters.all,
                        time_handler,
                    ),
                ],
                IMAGE: [
                    MessageHandler(
                        Filters.all,
                        image_handler,
                    ),
                ],
            },
            fallbacks=[
                CommandHandler('cancel', cancel_handler),
            ],
        )

        updater.dispatcher.add_handler(CommandHandler('start', start))
        updater.dispatcher.add_handler(report_handler)
        updater.dispatcher.add_handler(
            MessageHandler(
                Filters.text('Отчет об уборке рабочего места'),
                after_work_report,
            ),
         )
        updater.start_polling()
        updater.idle()
