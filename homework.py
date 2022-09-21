import logging
import os
import sys

import requests
import telegram
import time

from dotenv import load_dotenv

from exceptions import StatusCodeNot200, EmptyResponseFromApi, NoneTokenError

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

TOKENS = (
    ('PRACTICUM_TOKEN', PRACTICUM_TOKEN),
    ('TELEGRAM_TOKEN', TELEGRAM_TOKEN),
    ('TELEGRAM_CHAT_ID', TELEGRAM_CHAT_ID),
)

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

logger = logging.getLogger(__name__)
c_handler = logging.StreamHandler(sys.stdout)
f_handler = logging.FileHandler(os.path.join(BASE_DIR, 'logs.log'))
c_handler.setLevel(logging.DEBUG)
f_handler.setLevel(logging.INFO)
c_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
f_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'
                             ' - %(lineno)s')
c_handler.setFormatter(c_format)
f_handler.setFormatter(f_format)
logger.addHandler(c_handler)
logger.addHandler(f_handler)


def send_message(bot, message):
    """Отправляет сообщение в Telegram."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Бот начал отправку сообщения в Телеграм')
    except telegram.error.TelegramError as error:
        logger.error(f'Сообщение - {message} - отправить не удалось, {error}')
        return False
    else:
        logger.info(f'Бот отправил сообщение в Телеграм: {message}')
        return True


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp
    dict_params = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': timestamp},
    }
    logger.info('Создали запрос к API по адресу {url}, c {headers} и '
                'параметрами {params}'.format(**dict_params))
    try:
        response = requests.get(**dict_params)
        if response.status_code != requests.codes.ok:
            raise StatusCodeNot200('Должен быть 200')
        return response.json()
    except Exception as error:
        raise ConnectionError('Ошибка запроса к API по адресу '
                              '{url}, c {headers} и параметрами '
                              '{params}'.format(**dict_params), error)


def check_response(response):
    """Проверяет ответ API на корректность."""
    logger.info('Проверяем ответ API')
    if not isinstance(response, dict):
        raise TypeError
    elif 'homeworks' not in response or 'current_date' not in response:
        raise EmptyResponseFromApi
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError
    return homeworks


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе её статус."""
    if 'homework_name' not in homework:
        message = 'В ответе нет информации о статусе'
        logger.error(message)
        raise KeyError(message)
    else:
        return ('Изменился статус проверки работы "{homework_name}". '
                '{verdict}'.format(homework_name=homework.get('homework_name'),
                                   verdict=VERDICTS[homework.get('status')]))


def check_tokens():
    """Проверяет доступность переменных окружения."""
    if all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        return True
    else:
        for token in TOKENS:
            if token[1] is None:
                logger.critical(f'Отсутствует обязательная переменная окружения: '
                                f'{token[0]}. Программа принудительно остановлена.'
                                )
                return False


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        raise NoneTokenError
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    current_report, prev_report = {}, {}
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                homework = check_response(response)[0]
                current_timestamp = int(time.time())
                verdict = parse_status(homework)
                current_report['name'] = homework.get('homework_name')
                current_report['message'] = verdict
            else:
                current_report['message'] = 'Нет новых статусов'
            if current_report != prev_report:
                send_message(bot, current_report['message'])
                prev_report = current_report.copy()
                current_timestamp = response.get('current_date')
            else:
                logger.info('Нет новых статусов')
        except EmptyResponseFromApi as error:
            logger.info('Получили пустой ответ от API', error)
        except Exception as error:
            current_report['message'] = f'Сбой в работе программы: {error}'
            if current_report != prev_report:
                send_message(bot, current_report['message'])
                prev_report = current_report.copy()
            else:
                logger.info('Нет новых статусов')
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
