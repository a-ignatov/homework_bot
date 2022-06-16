class SmallException(Exception):
    pass


class NoHomeworkError(SmallException):
    pass


class BadServerResponseError(Exception):
    pass


class ServerConnectionError(Exception):
    pass

class TelegramDeliveryError(Exception):
    pass