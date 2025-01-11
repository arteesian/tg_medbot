from aiogram.utils import executor
from create_bot import dp
from database import sqlite_db
from handlers import client
async def on_startup(_):
    sqlite_db.sql_start()

client.register_handlers_client(dp)
executor.start_polling(dp, skip_updates=True, on_startup=on_startup)

