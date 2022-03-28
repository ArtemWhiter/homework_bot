"""Телеграм бот для проверки статуса домашних работ."""
import logging
import os
import time
from logging.handlers import RotatingFileHandler

import requests
import telegram
from dotenv import load_dotenv
from settings import RETRY_TIME, ENDPOINT, HOMEWORK_STATUSES

from http import HTTPStatus
load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

"""Запуск логирования."""
logging.basicConfig(
    level=logging.DEBUG,
    filename='homework_bot.log',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s',
    encoding='UTF-8',
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler('homework_bot.log',
                              maxBytes=50000000,
                              backupCount=5
                              )
logger.addHandler(handler)

formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)


def send_message(bot, message):
    """Функция отсылает сообщение в бота."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except requests.exceptions.RequestException as err_requests:
        logging.error(f'Ошибка отправки сообщения: {err_requests}')
        raise Exception(f'Ошибка отправки сообщения: {err_requests}')


def get_api_answer(current_timestamp):
    """Делает запрос, возвращает JSON."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}

    try:
        response = requests.get(
            ENDPOINT,
            headers={'Authorization': f'OAuth {PRACTICUM_TOKEN}'},
            params=params)
    except Exception as error:
        logging.error('Ошибка при запросе к API')
        raise Exception(f'Ошибка при запросе к API: {error}')

    if response.status_code != HTTPStatus.OK:
        logging.error('Страница по адресу ENDPOINT не отвечает')
        raise Exception(f'Страница не найдена, ответ: {response.status_code}')

    try:
        print(response.json())
        return response.json()
    except ValueError:
        logging.error('Не возможно привести ответ к формату Python.')
        raise Exception('Не возможно привести ответ к формату Python')


def check_response(response):
    """Проверяет ответ API, возвращает список работ по ключу 'homeworks'."""
    if type(response) is not dict:
        logger.error('Ответ API не яаляется типом данных Python')
        raise TypeError('Ответ API не яаляется типом данных Python')

    worklist = response.get('homeworks')
    if worklist is None:
        logger.error('Ошибка ключа <homeworks>. Передан несуществующий ключ')
        raise KeyError('Ошибка ключа <homeworks>. Передан несуществующий ключ')

    if len(worklist) == 0:
        logger.error('Получен пустой список работ')
        raise IndexError('Получен пустой список работ')

    return worklist[0]


def parse_status(homework):
    """Извлекает статус работы. Возвращает значение HOMEWORK_STATUSES."""
    if 'homework_name' not in homework:
        logger.error('Отсутствует ключ <homework_name> в ответе API')
        raise KeyError('Отсутствует ключ <homework_name> в ответе API')
    """Оставил проверку выше, иначе тесты не проходит.
    Хз как исправить пока."""

    homework_name = homework.get('homework_name')
    if homework_name is None:
        logger.error(
            'Ошибка ключа <homework_name>. Передан несуществующий ключ')
        raise KeyError(
            'Ошибка ключа <homework_name>. Передан несуществующий ключ')

    homework_status = homework.get('status')
    if homework_status is None:
        logger.error('Ошибка ключа <status>. Передан несуществующий ключ')
        raise KeyError('Ошибка ключа <status>. Передан несуществующий ключ')

    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Отсутствует переменные окружения')
        raise Exception('Отсутствует переменные окружения')

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    old_response = ''
    """Для работы от конкретной точки использовать
    current_timestamp = int(datetime(*START_DATE).timestamp()).
    """
    while True:
        try:
            current_timestamp = int(time.time())
            work_response = check_response(get_api_answer(current_timestamp))
            if work_response != old_response:
                send_message(bot, parse_status(work_response))
                old_response = work_response
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
