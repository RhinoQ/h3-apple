"""Standard logging for the standalone MLX subset."""
import logging


class RuntimeLogger(logging.LoggerAdapter):
    def __init__(self, logger):
        super().__init__(logger, {})
        self.seen = set()

    def log_once(self, level, message, *args):
        identity = level, message, repr(args)
        if identity not in self.seen:
            self.seen.add(identity)
            self.log(level, message, *args)

    def info_once(self, message, *args):
        self.log_once(logging.INFO, message, *args)

    def warning_once(self, message, *args):
        self.log_once(logging.WARNING, message, *args)


def init_logger(name):
    return RuntimeLogger(logging.getLogger(name))
