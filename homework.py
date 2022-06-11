import logging
import os
import time
from logging import StreamHandler

import requests
from dotenv import load_dotenv
from telegram import Bot

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

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='programm.log',
    level=logging.DEBUG)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = StreamHandler('homework_bot.log')
logger.addHandler(handler)


def send_message(bot, message):
    """Отправляет сообщение в чат."""
    try:
        chat_id = TELEGRAM_CHAT_ID
        bot.send_message(chat_id=chat_id, text=message)
        logging.info(f'{"Сообщение успешно отправлено"}')
    except Exception:
        logging.error(f'{"Сообщение не отправлено"}')
        bot.send_message(chat_id=chat_id, text='Сообщение не отправлено')


def get_api_answer(current_timestamp):
    """Делает запрос в API Endpoint и возвращает .json."""
    bot = Bot(token=TELEGRAM_TOKEN)
    response_status = 0
    try:
        timestamp = current_timestamp or int(time.time())
        params = {'from_date': timestamp}
        headers = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
        response = requests.get(ENDPOINT, headers=headers, params=params)
        response_status = response.status_code
        if response_status != 200:
            logging.error(f'{"Статус ответа API != 200"}')
            message = (f'{"Статус ответа API != 200"}')
            send_message(bot, message)
            raise ConnectionError()
        return response.json()

    except Exception as error:
        logging.error(f'Ошибка в ответе API: {error}')
        message = (f'{"Ошибка в ответе API: {error}"}')
        send_message(bot, message)


def check_response(response):
    """Проверяет корректность типа данных от API."""
    if type(response) is not dict:
        message = (f'{"API отдает не словарь"}')
        logging.error(message)
        raise TypeError()
    if type(response['homeworks']) is not list:
        message = (f'{"API отдает не словарь"}')
        logging.error(message)
        raise TypeError()

    return response['homeworks']


def parse_status(homework):
    """Ищет статус новых работ и возвращает строку с обновлением."""
    if homework.get('homework_name') is not None:
        pass
    else:
        logging.error(f'{"Отсутствует ожидаемый ключ в response"}')
        raise KeyError()
    homework_name = homework.get('homework_name')
    if homework.get('status') is not None:
        pass
    else:
        logging.error(f'{"Отсутствует ожидаемый ключ в response"}')
    homework_status = homework.get('status')
    verdict = HOMEWORK_STATUSES.get(homework_status)
    if homework_name is None or homework_status not in HOMEWORK_STATUSES:
        logging.error(f'{"Недокументированный статус домашней работы"}')
        bot = Bot(token=TELEGRAM_TOKEN)
        message = (f'{"Недокументированный статус домашней работы"}')
        send_message(bot, message)
        raise KeyError()
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет наличие необходимых для работы токенов."""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        return True
    else:
        logging.critical(f'{"Обязательные токены отсутствуют!"}')
        return False


def main():
    """Проверяет статус новых работ, отправляет статус в чат."""
    if not check_tokens():
        print(PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
        return

    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework_list = check_response(response)
            if len(homework_list) == 0:
                logging.debug(f'{"Новые статусы отсутствуют"}')
            if homework_list is not None:
                for homework in homework_list:
                    message = parse_status(homework)
                    send_message(bot, message)
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            logging.error(message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
