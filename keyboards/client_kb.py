from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

b1 = KeyboardButton('Chcę się umówić na wizytę')
b2 = KeyboardButton('Zobacz moje zapisy')
b3 = KeyboardButton('Chcę odwołać wizytę')

kb_client = ReplyKeyboardMarkup(resize_keyboard=True)

kb_client.row(b1, b2, b3)


