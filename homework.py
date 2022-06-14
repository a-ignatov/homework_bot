import logging
import os
import sys
import time
from logging import FileHandler, StreamHandler

import requests
from dotenv import load_dotenv
from telegram import Bot

import exceptions

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

prev_report = ''


def send_message(bot, message):
    """Отправляет сообщение в чат."""
    global prev_report
    if message == prev_report:
        return

    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.info(f'Успешно отправлено сообщение в чат: "{message}"')
        prev_report = message
    except exceptions.TelegramDeliveryError:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID,
                         text='Сообщение о статусе работы не отправлено')


def get_api_answer(current_timestamp):
    """Делает запрос в API Endpoint и возвращает .json."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    message = ('Ошибка в ответе API')
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        response_status = response.status_code
        if response_status != 200:
            message = (f'{"Статус ответа API != 200"}: {ENDPOINT}')
            logging.error(message)
            raise exceptions.BadServerResponseError(message)

        return response.json()
    except Exception:
        raise exceptions.ServerConnectionError(message)


def check_response(response):
    """Проверяет корректность типа данных от API."""
    logging.debug('Начало проверки ответа сервера')
    if isinstance(response, dict) is False:
        message = (f'{"API отдает не словарь"}')

        raise TypeError(message, response)
    if 'homeworks' not in response or 'current_date' not in response:
        message = (f'{"Отсутствуют обязательные ключи"}')

        raise exceptions.NoHomeworkError(message, response)

    if isinstance(response['homeworks'], list) is False:
        message = (f'{"API отдает не список"}')
        logging.error(message)
        raise TypeError(message, response)

    return response['homeworks']


def parse_status(homework):
    """Ищет статус новых работ и возвращает строку с обновлением."""
    if not homework.get('homework_name'):
        message = ('Отсутствует ожидаемый ключ в response"')
        raise KeyError(message)
    homework_name = homework.get('homework_name')
    if homework.get('status') is None:
        message = (f'{"Отсутствует ожидаемый ключ в response"}')
        raise exceptions.BadServerResponseError(message)
    homework_status = homework.get('status')
    verdict = HOMEWORK_VERDICTS.get(homework_status)
    if homework_status not in HOMEWORK_VERDICTS:
        message = (f'{"Недокументированный статус домашней работы"}')
        raise exceptions.BadServerResponseError(message)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет наличие необходимых для работы токенов."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Проверяет статус новых работ, отправляет статус в чат."""
    if not check_tokens():
        logging.critical(f'{"Обязательные токены отсутствуют!"}')
        sys.exit(0)

    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework_list = check_response(response)
            if len(homework_list) == 0:
                logging.debug(f'{"Новые статусы отсутствуют"}')

            for homework in homework_list:
                message = parse_status(homework)
                send_message(bot, message)
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            logging.error(message, exc_info=True)

        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s - \
            %(funcName)s - %(lineno)s',
        level=logging.INFO,
        handlers=[
            FileHandler(filename='homework_bot.log'),
            StreamHandler(stream=sys.stdout)
        ])
    logging.debug('Старт бота')
    main()
