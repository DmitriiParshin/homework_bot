import logging
import os
import requests
import sys
import telegram
import time

from dotenv import load_dotenv

from exceptions import EndpointConnectionError, StatusCodeNot200

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
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s - %(lineno)s'
)
handler.setFormatter(formatter)


def send_message(bot, message):
    """Отправляет сообщение в Telegram."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Бот отправил сообщение {message}')
    except Exception as error:
        logger.error(f'Сообщение - {message} - отправить не удалось, {error}')


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
        if response.status_code != requests.codes.ok:
            raise StatusCodeNot200('Должен быть 200')
    except Exception:
        raise EndpointConnectionError('Ошибка ответа Ендпоинта')
    else:
        return response.json()


def check_response(response):
    """Проверяет ответ API на корректность."""
    if not response:
        message = 'Нет ответа от сервера'
        logger.error(message)
        raise Exception(message)
    elif isinstance(response, dict):
        return response['homeworks'][0]
    else:
        message = 'Пришел некорректный ответ от сервера'
        logger.error(message)
        raise TypeError(message)


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе её статус."""
    if 'homework_name' not in homework or 'status' not in homework:
        raise KeyError
    homework_name = homework['homework_name']
    homework_status = homework['status']
    try:
        verdict = HOMEWORK_STATUSES[homework_status]
    except IndexError as error:
        logger.error(f'IndexError, {error}')
    else:
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            if not check_tokens():
                logger.critical(f'Отсутствует обязательная переменная '
                                f'окружения: !!!. Программа принудительно '
                                f'остановлена.')
                exit()
            response = get_api_answer(current_timestamp - RETRY_TIME)
            if len(response['homeworks']) == 0:
                raise IndexError
            homework = check_response(response)
            if homework:
                send_message(bot, parse_status(homework))
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)
        except IndexError:
            message = 'Список домашних работ пуст'
            logger.info(message)
            send_message(bot, message)
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            time.sleep(RETRY_TIME)
        else:
            send_message(bot, parse_status(homework))


if __name__ == '__main__':
    main()
