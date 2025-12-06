from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
import logging
import os

TOKEN = os.getenv('BOT_TOKEN', '8326658124:AAE1nVuLI1Pu77FI3cI40RdQzgld3AMvT_M')

logging.basicConfig(level=logging.INFO)
logging.getLogger("apscheduler").setLevel(logging.WARNING)

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='HTML'))

dp = Dispatcher()