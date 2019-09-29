"""App configuration."""
import logging.config
import os

import dotenv
import sentry_sdk
import structlog
from sentry_sdk.integrations.aiohttp import AioHttpIntegration
from structlog_sentry import SentryJsonProcessor


class Config:
    """Configuration."""

    #: Set DEBUG logging level
    DEBUG = False

    #: Telegram bot API key (required)
    BOT_API_TOKEN = ''
    #: SongLink API URL (required)
    SONGLINK_API_URL = 'https://api.song.link/v1-alpha.1/links'
    #: SongLink API key (optional)
    SONGLINK_API_KEY = ''
    #: Sentry DSN (optional)
    SENTRY_DSN = ''

    #: Logging configuration
    LOG_CONFIG = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'default': {
                'format': (
                    '%(asctime)s - %(name)s - %(filename)s:%(lineno)d - '
                    '%(processName)s - %(levelname)s - %(message)s'
                )
            },
            'json': {'format': '%(message)s'},
        },
        'handlers': {
            'stdout': {
                'class': 'logging.StreamHandler',
                'level': 'DEBUG',
                'formatter': 'default',
                'stream': 'ext://sys.stdout',
            },
            'stdout_json': {
                'class': 'logging.StreamHandler',
                'level': 'DEBUG',
                'formatter': 'json',
                'stream': 'ext://sys.stdout',
            },
        },
        'loggers': {
            'group_songlink_bot': {
                'handlers': ['stdout_json'],
                'level': 'INFO',
            },
            # asyncio warnings
            'asyncio': {'handlers': ['stdout'], 'level': 'WARNING'},
        },
    }
    #: Log renderer
    LOG_RENDERER = structlog.processors.JSONRenderer()

    def init_logging(self):
        """Init logging."""
        if self.DEBUG:
            self.LOG_CONFIG['loggers']['group_songlink_bot']['level'] = 'DEBUG'
            if not isinstance(
                self.LOG_RENDERER, structlog.dev.ConsoleRenderer
            ):
                self.LOG_RENDERER = structlog.dev.ConsoleRenderer(pad_event=50)
        logging.config.dictConfig(self.LOG_CONFIG)
        structlog.configure_once(
            processors=[
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt='iso'),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                SentryJsonProcessor(level=logging.ERROR),
                self.LOG_RENDERER,
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

    @classmethod
    def load_config(cls, env_prefix: str = 'GROUP_SONGLINK_BOT_'):
        """Load config merging default variables and variables from the
        environment.

        :param env_prefix: prefix of environment variables
        :return: filled config object
        """
        config = cls()
        # Load environment from .env file
        dotenv.load_dotenv()
        # Update config object with environment variables
        for env_var_name, value in os.environ.items():
            if env_var_name.startswith(env_prefix):
                var_name = env_var_name[len(env_prefix) :]
                if hasattr(config, var_name):
                    setattr(config, var_name, value)
        # Check the only required field
        if not config.BOT_API_TOKEN:
            raise Exception(
                'BOT_API_TOKEN is missing. Please, provide '
                f'{env_prefix}BOT_API_TOKEN either via environment variable or'
                '.env file.'
            )
        if config.SENTRY_DSN:
            sentry_sdk.init(
                dsn=config.SENTRY_DSN, integrations=[AioHttpIntegration()]
            )
        config.init_logging()
        return config
