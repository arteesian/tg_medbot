import sqlite3 as sq
from create_bot import bot

def sql_start():
    global base, cur
    base = sq.connect('medhelper.db')
    cur = base.cursor()
    if base:
        print('Połączenie nawiązane')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS doctors (
            id INTEGER PRIMARY KEY,
            name TEXT,
            specialization TEXT
        )
    ''')

    cur.execute("SELECT count(*) FROM doctors")
    count = cur.fetchone()[0]

    if count == 0:
        doctors_data = [
            (1, "Jan Kowalski", "Terapeuta"),
            (2, "Paulina Kowalska", "Terapeuta"),
            (3, "Ignacy Maciejewski", "Kardiolog"),
            (4, "Marta Witkowska", "Kardiolog"),
            (5, "Mikołaj Bąk", "Neurolog"),
            (6, "Ilona Zielińska", "Neurolog"),
            (7, "Kacper Kozłowski", "Psychiatra"),
            (8, "Aleksandra Adamska", "Psychiatra"),
            (9, "Norbert Stępień", "Dermatolog"),
            (10, "Ewelina Ostrowska", "Dermatolog"),
            (11, "Kinga Mróz", "Ortopeda"),
            (12, "Aleksy Włodarczyk", "Ortopeda"),
            (13, "Helena Rutkowska", "Dentysta"),
            (14, "Ludwik Michalak", "Dentysta"),
            (15, "Cecylia Błaszczyk", "Chirurg"),
            (16, "Jarosław Bąk", "Chirurg"),
            (17, "Agnieszka Jakubowska", "Okulista"),
            (18, "Anatol Malinowski", "Okulista"),
            (19, "Martyna Michalak", "Ginekolog"),
            (20, "Bruno Zawadzki", "Ginekolog"),
        ]
        cur.executemany('INSERT INTO doctors (id, name, specialization) VALUES (?, ?, ?)', doctors_data)

    cur.execute('''
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            phone TEXT CHECK(LENGTH(phone) = 9),
            tg_id TEXT NOT NULL
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS schedule (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            doctor_id   INTEGER REFERENCES doctors (id),
            day         TEXT    UNIQUE,
            shift_start TEXT,
            shift_end   TEXT
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            doctor_id        INTEGER REFERENCES doctors (id) 
                                     NOT NULL,
            patient_id       INTEGER REFERENCES patients (id) 
                                     NOT NULL,
            appointment_day  TEXT    NOT NULL,
            appointment_time TEXT    NOT NULL
        )
    ''')

    base.commit()

async def sql_show_specializations(message):
    result = cur.execute('SELECT specialization FROM doctors GROUP BY specialization').fetchall()
    return result

async def sql_show_doctors(message):
    result = cur.execute('SELECT name, specialization FROM doctors WHERE specialization == ?', (message,)).fetchall()
    return result

async def sql_check_doctor_name(message):
    result = cur.execute('SELECT COUNT(name) FROM doctors WHERE name == ?', (message,)).fetchone()
    return result

async def sql_get_available_time(state):
    async with state.proxy() as data:
        result = cur.execute('SELECT shift_start, shift_end FROM schedule JOIN doctors ON schedule.doctor_id = doctors.id WHERE doctors.specialization == ? '
                             'AND schedule.day == ? AND doctors.name == ?', tuple(data.values())).fetchall()
    return result
async def sql_select_date(state):
    async with state.proxy() as data:
        result = cur.execute('SELECT name FROM doctors JOIN schedule ON doctors.id = schedule.doctor_id WHERE date(schedule.day) == date(?) '
                             'AND specialization == ?', (data['date'], data['specialization'])).fetchall()
    return result

async def sql_create_appointment(message, state):
    async with state.proxy() as data:
        cur.execute('SELECT id FROM doctors WHERE name == ?', (data['name'],))
        doctor_id = cur.fetchone()
        cur.execute('SELECT id FROM patients WHERE tg_id == ?', (message.from_user.id,))
        patient_id = cur.fetchone()
        cur.execute('INSERT INTO appointments (doctor_id, patient_id, appointment_day, appointment_time) VALUES (?, ?, ?, ?)'
                    , (doctor_id[0], patient_id[0], data['date'], data['time']))
        base.commit()

async def sql_check_if_available(time, state):
    async with state.proxy() as data:
        result = cur.execute('SELECT * FROM appointments JOIN doctors ON appointments.doctor_id = doctors.id WHERE doctors.name == ? '
                             'AND appointments.appointment_day == ? AND appointments.appointment_time == ?',
                             (data['name'], data['date'], time)).fetchall()
    if result:
        return False
    else:
        return True

async def sql_show_appointments(message):
    result = cur.execute('''
        SELECT doctor_id, patient_id, appointment_day, appointment_time, doctors.name, doctors.specialization
        FROM appointments
        INNER JOIN doctors ON appointments.doctor_id = doctors.id
        INNER JOIN patients ON appointments.patient_id = patients.id
        WHERE patients.tg_id == ?
        ORDER BY doctors.name
    ''', (message.from_user.id,)).fetchall()
    return result

async def sql_delete_appointment(appointment):
    cur.execute('DELETE FROM appointments WHERE doctor_id == ? AND patient_id == ? '
                'AND appointment_day == ? AND appointment_time == ?',
                (appointment[0], appointment[1], appointment[2], appointment[3]))
    base.commit()
async def sql_add_user(message, state):
    async with state.proxy() as data:
        patient_data = (data['name'], data['phone'], message.from_user.id)
        cur.execute('INSERT INTO patients (name, phone, tg_id) VALUES (?, ?, ?)', patient_data)
        base.commit()

async def sql_show_user(message):
    result = cur.execute('SELECT name FROM patients WHERE tg_id == ?', (str(message.from_user.id),)).fetchone()
    return result
