import logging
import os
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

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
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)


def get_api_answer(current_timestamp):
    """Делает запрос, возвращает JSON."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}

    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception as error:
        logging.error('Ошибка при запросе к API')
        raise Exception(f'Ошибка при запросе к API: {error}')

    if response.status_code != 200:
        logging.error('Страница по адресу ENDPOINT не отвечает')
        raise Exception(f'Страница не найдена, ответ: {response.status_code}')
    else:
        return response.json()


def check_response(response):
    """Проверяет ответ API, возвращает список работ по ключу 'homeworks'."""
    try:
        type(response) is not dict
    except ImportError:
        logger.error('Ответ API не яаляется типом данных Python')
        raise TypeError('Ответ API не яаляется типом данных Python')
    try:
        worklist = response['homeworks']
    except KeyError:
        logger.error('Ошибка ключа <homeworks>. Передан несуществующий ключ')
        raise KeyError('Ошибка ключа <homeworks>. Передан несуществующий ключ')
    try:
        new_homework = worklist[0]
    except IndexError:
        logger.error('Получен пустой список работ')
        raise IndexError('Получен пустой список работ')

    return new_homework


def parse_status(homework):
    """Извлекает статус работы. Возвращает значение HOMEWORK_STATUSES."""
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует ключ "homework_name" в ответе API')

    try:
        homework_name = homework['homework_name']
    except KeyError:
        logger.error(
            'Ошибка ключа <homework_name>. Передан несуществующий ключ')
        raise KeyError(
            'Ошибка ключа <homework_name>. Передан несуществующий ключ')

    try:
        homework_status = homework['status']
    except KeyError:
        logger.error('Ошибка ключа <status>. Передан несуществующий ключ')
        raise KeyError('Ошибка ключа <status>. Передан несуществующий ключ')

    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    environ_tokens = [
            'PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID',
    ]
    for environ_tocken in environ_tokens:
        if environ_tocken not in os.environ.keys():
            logging.critical(
                f'Отсутствует переменная окружения: {environ_tocken}')

    if all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        return True


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    old_message = ''

    while True:
        try:
            current_timestamp = int(datetime.now().timestamp())
            work_response = check_response(get_api_answer(current_timestamp))
            bot_message = send_message(bot, parse_status(work_response))
            if bot_message != old_message:
                old_message = bot_message
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            time.sleep(RETRY_TIME)
        else:
            pass


if __name__ == '__main__':
    main()
