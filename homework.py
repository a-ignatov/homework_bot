import logging
import os
import sys
import time

import requests
import telegram
from dotenv import load_dotenv

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


def send_message(bot, message):
    """Отправляет сообщение в чат."""
    try:
        logging.info('Попытка отправки сообщения в чат')
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.info('Успешно отправлено сообщение в чат')
    except telegram.error.TelegramError:
        raise exceptions.TelegramDeliveryError()


def get_api_answer(current_timestamp):
    """Делает запрос в API Endpoint и возвращает .json."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        response_status = response.status_code
        if response_status != 200:
            message = (f'{"Статус ответа API != 200"}: {ENDPOINT}')
            logging.error(message)
            raise exceptions.BadServerResponseError(message)
        return response.json()
    except Exception:
        message = ('Ошибка в ответе API')
        raise exceptions.ServerConnectionError(message)


def check_response(response):
    """Проверяет корректность типа данных от API."""
    logging.debug('Начало проверки ответа сервера')
    if not isinstance(response, dict):
        message = (f'{"API отдает не словарь"}')
        raise TypeError(message, response)
    if 'homeworks' not in response or 'current_date' not in response:
        message = (f'{"Отсутствуют обязательные ключи"}')
        raise exceptions.NoHomeworkError(message, response)
    if not isinstance(response['homeworks'], list):
        message = (f'{"API отдает не список"}')
        raise TypeError(message, response)
    return response['homeworks']


def parse_status(homework):
    """Ищет статус новых работ и возвращает строку с обновлением."""
    if not homework.get('homework_name') or None:
        raise KeyError('Отсутствует ожидаемый ключ в response')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    verdict = HOMEWORK_VERDICTS.get(homework_status)
    if homework_status not in HOMEWORK_VERDICTS:
        message = (f'{"Недокументированный статус домашней работы"}')
        raise ValueError(message)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет наличие необходимых для работы токенов."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Проверяет статус новых работ, отправляет статус в чат."""
    logging.info('Старт бота')
    if not check_tokens():
        logging.critical(f'{"Обязательные токены отсутствуют!"}')
        sys.exit("Обязательные токены отсутствуют!")
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    prev_report = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework_list = check_response(response)
            if len(homework_list) == 0:
                logging.debug(f'{"Новые статусы отсутствуют"}')
            for homework in homework_list:
                message = parse_status(homework)
                if message == prev_report:
                    logging.debug(
                        (('Статус работы не изменился после обновления.'
                          ' Сообщение не отправлено')))
                else:
                    send_message(bot, message)
                    prev_report = message
            current_timestamp = int(time.time())
        except exceptions.SmallException:
            logging.error(exc_info=True)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if message == prev_report:
                logging.debug(
                    (('Статус работы не изменился после обновления.'
                      ' Сообщение не отправлено')))
            else:
                send_message(bot, message)
            logging.error(message, exc_info=True)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logging.basicConfig(format=('%(asctime)s - %(name)s - %(levelname)s'
                                ' - %(message)s - %(funcName)s - %(lineno)s'),
                        level=logging.INFO,
                        handlers=[
                            logging.FileHandler(filename='homework_bot.log'),
                            logging.StreamHandler(stream=sys.stdout)
    ])
    main()
