from aiogram import types, Dispatcher
from create_bot import bot, dp
from keyboards import kb_client
from aiogram.types import ReplyKeyboardRemove
from database import sqlite_db
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from datetime import datetime, timedelta

appointments = {}
class IsAnyAppointment():
    is_any_appointment = False
class FSMDoctors(StatesGroup):
    specialization = State()
    date = State()
    name = State()
    time = State()

class FSMPatients(StatesGroup):
    name = State()
    phone = State()

class FSMDelete(StatesGroup):
    number = State()
    confirmation = State()

async def command_start(message: types.Message):
    await bot.send_message(message.from_user.id, 'Dzień dobry! Jestem asystentem rezerwacji wizyt do lekarzy naszej kliniki. '
                                                 'Proszę wybrać jedną z opcji, przedstawionych na przyciskach.', reply_markup=kb_client)

async def check_user(message: types.Message):
    result = await sqlite_db.sql_show_user(message)
    if result is None:
        await bot.send_message(message.from_user.id, 'Aby umówić się na wizytę musisz mieć użytkownika. '
                                                     'Proszę wpisać na czacie "Nowy użytkownik"', reply_markup=ReplyKeyboardRemove())
    else:
        msg = f'Masz na tym koncie Telegram użytkownika: {result[0]}'
        await bot.send_message(message.from_user.id, msg)
        await show_all_specializations(message)
async def show_all_specializations(message: types.Message):
    await FSMDoctors.specialization.set()
    result = await sqlite_db.sql_show_specializations(message)
    if result:
        msg = "W naszej klinicę są takie specjaliści jak:\n"
        for x in result:
            msg += f'{x[0]}\n'
        await bot.send_message(message.from_user.id, msg)
    await bot.send_message(message.from_user.id, 'Proszę wybrać specjalność lekarza, wpisując ją na czacie',
                           reply_markup=ReplyKeyboardRemove())

async def select_specialization(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['specialization'] = message.text
    result = await sqlite_db.sql_show_doctors(message.text.title())
    if result:
        msg = f'Nasze lekarze ze specjalnością "{message.text.title()}":\n'
        for x in result:
            msg += f'{x[0]}\n'
        await bot.send_message(message.from_user.id, msg)
        await bot.send_message(message.from_user.id,
                               'Proszę wybrać preferowaną datę wizyty w formacie "YYYY-MM-DD". Ja pokażę dostępnych na ten dzień specjalistów.\n'
                               'Na przykład: 2024-01-01 dla 1 stycznia 2024 roku')
        await FSMDoctors.next()
    else:
        await bot.send_message(message.from_user.id, f'Nie mamy specjalisty "{message.text.title()}".\n'
                                                     f'Proszę spróbować ponownie i wprowadzić jedną z podanych specjalności z listy.')


async def select_date(message: types.Message, state: FSMContext):
    d = message.text
    if len(d.split('-')) == 3:
        try:
            async with (state.proxy() as data):
                data['date'] = d
            result = await sqlite_db.sql_select_date(state)
        except Exception:
            await bot.send_message(message.from_user.id, 'Podany zły format daty. Proszę rozpocząć proces rezerwacji wizyty ponownie.\n'
                                                         'Proszę wybrać preferowaną datę wizyty w formacie "YYYY-MM-DD".\n'
                                                         'Na przykład: 2024-01-01 dla 1 stycznia 2024 roku')
        if result:
            msg = ""
            for x in result:
                msg += f'{x[0]}\n'
            async with state.proxy() as data:
                await bot.send_message(message.from_user.id, 'Lekarze ze specjalnością ' + data[
                    'specialization'] + ' dostępne na datę '
                                       + datetime.strftime(datetime.strptime(d, "%Y-%m-%d"),"%d.%m.%Y") + ': \n' + msg)
            await bot.send_message(message.from_user.id, 'Proszę wybrać lekarza z listy i wpisać jego imię')
            await FSMDoctors.next()
        else:
            await bot.send_message(message.from_user.id,
                                   f'Niestety, nie mamy wolnych specjalistów na datę {d}. Proszę rozpocząć proces rezerwacji wizyty ponownie i wybrać inną datę.', reply_markup=kb_client)
            await state.finish()
    else:
        await bot.send_message(message.from_user.id,
                               'Podany zły format daty. Proszę rozpocząć proces rezerwacji wizyty ponownie.\n'
                               'Proszę wybrać preferowaną datę wizyty w formacie "YYYY-MM-DD".\n'
                               'Na przykład: 2024-01-01 dla 1 stycznia 2024 roku')

async def select_doctor(message: types.Message, state: FSMContext):
    result = await sqlite_db.sql_check_doctor_name(message.text)
    if result[0] > 0:
        async with state.proxy() as data:
            data['name'] = message.text
        result = await sqlite_db.sql_get_available_time(state)
        shift_start = datetime.strptime(result[0][0], "%H:%M")
        shift_end = datetime.strptime(result[0][1], "%H:%M")
        i = shift_start
        available_time = []
        while i < shift_end:
            if await sqlite_db.sql_check_if_available(datetime.strftime(i, "%H:%M"), state):
                available_time.append(i)
            i += timedelta(minutes=30)
        msg = ""
        for x in available_time:
            msg += f'{datetime.strftime(x, "%H:%M")}\n'
        await FSMDoctors.next()
        await bot.send_message(message.from_user.id, 'Proszę wybrać jedną z dostępnych godzin specjalisty:\n' + msg + '\nWpisać ją należy w formacie HH:MM (np. 12:00)')
    else:
        await bot.send_message(message.from_user.id, f'Dla podanej specjalności nie istnieje specjalisty z imieniem {message.text}. '
                                                     f'Proszę wybrać lekarza z listy powyżej i wpisać jego imię')

async def select_time(message: types.Message, state: FSMContext):
    t = message.text
    if len(t.split(':')) == 2:
        try:
            input_time = datetime.strptime(t, "%H:%M")
        except Exception:
            await bot.send_message(message.from_user.id,
                                   'Podany zły format godziny. Proszę wpisać godzinę w formacie HH:MM (np. 12:00)')
            return
        doc_time = await sqlite_db.sql_get_available_time(state)
        shift_start = datetime.strptime(doc_time[0][0], "%H:%M")
        shift_end = datetime.strptime(doc_time[0][1], "%H:%M")
        i = shift_start
        available_time = []
        while i < shift_end:
            if await sqlite_db.sql_check_if_available(datetime.strftime(i, "%H:%M"), state):
                available_time.append(i)
            i += timedelta(minutes=30)
        if input_time in available_time:
            async with state.proxy() as data:
                data['time'] = t
            await sqlite_db.sql_create_appointment(message, state)
            async with state.proxy() as data:
                await bot.send_message(message.from_user.id, 'Gratulacje! Zapisałeś się do lekarza ' + data['name']
                                       + ' (' + data['specialization'] + ') w dniu '
                                       + datetime.strftime(datetime.strptime(data['date'], "%Y-%m-%d"),"%d.%m.%Y")
                                       + ', godzina ' + data['time'] + '. Nie zapomnij wziąć ze sobą dowód osobisty!', reply_markup=kb_client)
            await state.finish()
        else:
            await bot.send_message(message.from_user.id,
                                   'Podana godzina nie jest dostępna. Proszę wpisać jedną z dostępnych godzin podanych powyżej')
    else:
        await bot.send_message(message.from_user.id, 'Podany zły format godziny. Proszę wpisać godzinę w formacie HH:MM (np. 12:00)')


async def show_appointments(message: types.Message):
    result = await sqlite_db.sql_show_appointments(message)
    if result:
        IsAnyAppointment.is_any_appointment = True
        msg = "Zarezerwowane wizyty które aktualnie masz:\n"
        for index, x in enumerate(result):
            appointments[index] = x
        for k in appointments:
            msg += (f'{k + 1}) Specjalista {appointments.get(k)[4]} ({appointments.get(k)[5]}), '
                    f'data: {datetime.strftime(datetime.strptime(appointments.get(k)[2], "%Y-%m-%d"), "%d.%m.%Y")}, '
                    f'godzina {appointments.get(k)[3]}\n')
        await bot.send_message(message.from_user.id, msg)
    else:
        await bot.send_message(message.from_user.id, 'Nie masz jeszcze żadnej zarezerwowanej wizyty')
async def appointments_to_delete(message: types.Message):
    user_check = await sqlite_db.sql_show_user(message)
    if user_check is None:
        await bot.send_message(message.from_user.id,
                               'Aby odwołać wizytę musisz mieć użytkownika. Proszę wpisać na czacie "Nowy użytkownik"',
                               reply_markup=ReplyKeyboardRemove())
    else:
        msg = f'Masz na tym koncie Telegram użytkownika: {user_check[0]}'
        await bot.send_message(message.from_user.id, msg)

        await show_appointments(message)
        if IsAnyAppointment.is_any_appointment:
            await bot.send_message(message.from_user.id,
                                   'Proszę wybrać wizytę, którą chcesz odwołać, wpisując odpowiedni numer. Na przykład, "1"', reply_markup=ReplyKeyboardRemove())
            await FSMDelete.number.set()


async def delete_appointment(message: types.Message, state: FSMContext):
    t = message.text
    try:
        n = int(message.text)
    except Exception:
        await bot.send_message(message.from_user.id, 'Błąd formatu danych, wprowadzone dane nie są liczbą')
        return
    if n > 0:
        is_included = False
        for x in list(appointments.keys()):
            if (n - 1) == x:
                is_included = True
                async with state.proxy() as data:
                    data['number'] = n - 1
        if is_included:
            await bot.send_message(message.from_user.id, 'Czy na pewno chcesz odwołać tę wizytę? Aby potwierdzić, wpisz „Tak”. '
                                                         'Aby zakończyć anulowanie wizyty, wpisz „Nie”')
            await FSMDelete.next()
        else:
            await bot.send_message(message.from_user.id,
                                   'Wprowadzono numer, którego nie ma na liście. Proszę wprowadzić istniejący numer')
    else:
        await bot.send_message(message.from_user.id, 'Wprowadzono numer, którego nie ma na liście. Proszę wprowadzić istniejący numer')

async def confirm_deletion(message: types.Message, state: FSMContext):
    if message.text.title() == "Tak":
        async with state.proxy() as data:
            appointment = appointments.get(data['number'])
            await sqlite_db.sql_delete_appointment(appointment)
        await state.finish()
        appointments.clear()
        await bot.send_message(message.from_user.id, 'Wybrana wizyta została odwołana',reply_markup=kb_client)
    elif message.text.title() == "Nie":
        await state.finish()
        await bot.send_message(message.from_user.id, 'Proces odwoływania wizyty został zakończony', reply_markup=kb_client)
    else:
        await bot.send_message(message.from_user.id, 'Aby potwierdzić odwołanie wizyty, wpisz „Tak”. Aby zakończyć anulowanie wizyty, wpisz „Nie”')
async def create_user(message: types.Message):
    await FSMPatients.name.set()
    await bot.send_message(message.from_user.id, 'Proszę wpisać swoje imię i nazwisko w formacie: "Jan Kowalski"')

async def get_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['name'] = message.text
        await FSMPatients.next()
        await bot.send_message(message.from_user.id, f'Imię {message.text} zostało wpisane.\n'
                                                     f'Proszę wpisać numer telefonu w formacie 9-cyfrowym (bez kodu krajowego)')

async def get_phone(message: types.Message, state: FSMContext):
    correct_number = ''
    if message.text.startswith('+48'):
        correct_number = message.text[3:]
    else:
        correct_number = message.text
    if len(correct_number) == 9 and correct_number.isdigit():
        async with state.proxy() as data:
            data['phone'] = message.text
        await sqlite_db.sql_add_user(message, state)
        await state.finish()
        await bot.send_message(message.from_user.id, 'Zostałeś wpisany do naszego systemu użyktowników! '
                                                     'Teraz możesz się zapisywać na wizyty do lekarzy', reply_markup=kb_client)
    else:
        await bot.send_message(message.from_user.id, 'Podany numer jest źle wpisany. Proszę spróbować ponownie')
        await bot.send_message(message.from_user.id, 'Proszę wpisać numer telefonu w formacie 9-cyfrowym (bez kodu krajowego)')

def register_handlers_client(dp : Dispatcher):
    dp.register_message_handler(command_start, commands=['start'])
    dp.register_message_handler(check_user, Text(contains='umówić'))
    dp.register_message_handler(show_all_specializations, commands=['lista'], state=None)
    dp.register_message_handler(select_specialization, state=FSMDoctors.specialization)
    dp.register_message_handler(select_date, state=FSMDoctors.date)
    dp.register_message_handler(select_doctor, state=FSMDoctors.name)
    dp.register_message_handler(select_time, state=FSMDoctors.time)
    dp.register_message_handler(show_appointments, Text(contains='Zobacz'))
    dp.register_message_handler(appointments_to_delete, Text(contains='odwołać'), state=None)
    dp.register_message_handler(delete_appointment, state=FSMDelete.number)
    dp.register_message_handler(confirm_deletion, state=FSMDelete.confirmation)
    dp.register_message_handler(create_user, Text(equals='Nowy użytkownik'), state=None)
    dp.register_message_handler(get_name, state=FSMPatients.name)
    dp.register_message_handler(get_phone, state=FSMPatients.phone)