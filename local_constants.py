import os
import json


DEBUG_MODE = True
USER_LIST_SIZE = 10
DB_NAME = os.getenv('DB_NAME')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
NEWS_BOT_TOKEN = os.getenv('NEWS_BOT_TOKEN')

if DEBUG_MODE:
    BGB_BAZAR_CHANNEL_ID = os.getenv('BGB_TESTES_CHANNEL_ID')
    BGB_BAZAR_COMMENTS_ID = os.getenv('BGB_TESTES_COMMENTS_ID')
    
else:
    BGB_BAZAR_CHANNEL_ID = os.getenv('BGB_BAZAR_CHANNEL_ID')
    BGB_BAZAR_COMMENTS_ID = os.getenv('BGB_BAZAR_COMMENTS_ID')

TRUSTED_USERS_ENV = json.loads(os.getenv('TRUSTED_USERS'))
TRUSTED_USERS = [int(userid) for userid in TRUSTED_USERS_ENV.keys()]
TRUSTED_USERNAMES = [username for username in TRUSTED_USERS_ENV.values()]

DAYS_BLOCKED = 0 if DEBUG_MODE else 5
BOT_NAME = 'bazarbgb'
SUBMIT_URL = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
EDIT_MESSAGE_URL = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText'

SMMRY_API_KEY = os.getenv('SMMRY_API_KEY')
NEWS_SUBMIT_URL = f'https://api.telegram.org/bot{NEWS_BOT_TOKEN}/sendMessage'

REMOVE_COMMANDS = ['/r', '/v', '/n']
PRICE_COMMANDS = ['/ap']
