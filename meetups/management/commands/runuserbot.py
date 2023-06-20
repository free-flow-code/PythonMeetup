import logging

from django.core.management.base import BaseCommand
from telegram.ext import Updater
from conf import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s',
)

logger = logging.getLogger('UserBot')

class Command(BaseCommand):
    pass
