import logging

class Logger:

    def __init__(self, log_level: str = "INFO"):
        self.log_level = log_level.upper()
        self.logger = logging.getLogger()
        self.logger.setLevel(log_level)
        self.handler = logging.StreamHandler()
        self.formatter = logging.Formatter(
            '**%(levelname)s** %(name)s - %(funcName)s() - Line:%(lineno)d - %(message)s'
        )
        self.handler.setFormatter(self.formatter)
        self.logger.addHandler(self.handler)

    def get_logger(self, file):
        self.loggger = logging.getLogger(file.split('/')[-1].upper())
        return self.logger