import logging
import os
from http import HTTPStatus

import requests
import sys
import telegram
import time

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

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)


class ResponseError(Exception):
    pass


def send_message(bot, message):
    try:
        message = bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Бот отправил сообщение {message}')
    except Exception as error:
        logger.error(f'Сообщение - {message} - отправить не удалось, {error}')


def get_api_answer(current_timestamp):
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': 0}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            raise ResponseError
    except ResponseError as error:
        logger.error(f'Эндпоинт {ENDPOINT} недоступен. Код ответа API:'
                     f'{error}')
    except Exception as error:
        logger.error(f'Эндпоинт {ENDPOINT} недоступен. Код ответа API:'
                     f'{error}')
    else:
        return response.json()


def check_response(response):
    try:
        if isinstance(response, dict):
            if len(response['homeworks']) == 0:
                raise IndexError
        else:
            raise TypeError
    except IndexError as error:
        logger.error(f'Index error {error}')
    except TypeError as error:
        logger.error(f'Type Error {error}')
    except Exception as error:
        logger.error(f'HZ error {error}')
    else:
        return response.get('homeworks')


def parse_status(homework):
    try:
        homework_name = homework.get('homework_name')
        homework_status = homework.get('status')
        verdict = HOMEWORK_STATUSES[homework_status]
        if homework_name is None or homework_status is None:
            raise KeyError
    except KeyError as error:
        logger.error(f'{error} -> неизвестный ключ {homework_name}')
    except Exception as error:
        logger.error(f'Что-то пошло не так с {homework_name}, {error}')
    else:
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    if (PRACTICUM_TOKEN is None or TELEGRAM_TOKEN is None or
            TELEGRAM_CHAT_ID is None):
        return False
    else:
        return True


def main():
    """Основная логика работы бота."""

    ...

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    ...

    while True:
        try:
            check_tokens()
            response = get_api_answer(current_timestamp)
            check_response(response)
            homework = check_response(response)[0]
            parse_status(homework)
            message = parse_status(homework)
            send_message(bot, message)

            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            time.sleep(RETRY_TIME)
        except KeyboardInterrupt as error:
            error = f'Сбой в работе программы: {error}'
        else:
            pass


if __name__ == '__main__':
    main()
