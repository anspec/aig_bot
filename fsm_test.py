import asyncio
from datetime import datetime

import aiosqlite
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from config import TG_TOKEN

# --- Настройка базы данных ---
DB_NAME = "school_data.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                grade TEXT NOT NULL,
                data DATETIME NOT NULL
            )
        ''')
        await db.commit()
        print("✅ Таблица students создана или уже существует.")

# --- Машины состояний ---
class StudentForm(StatesGroup):
    waiting_for_name = State()
    waiting_for_age = State()
    waiting_for_grade = State()

class FindStudentForm(StatesGroup):
    waiting_name = State()
    waiting_grade = State()

class EditStudentForm(StatesGroup):
    waiting_select = State()
    waiting_field = State()
    waiting_value = State()

class DeleteStudentForm(StatesGroup):
    waiting_select = State()
    confirm_delete = State()

# --- Инициализация ---
bot = Bot(token=TG_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()

# --- Главное меню (Inline) ---
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить студента", callback_data="add")],
        [InlineKeyboardButton(text="✏️ Изменить студента", callback_data="edit")],
        [InlineKeyboardButton(text="🗑️ Удалить студента", callback_data="del")],
        [InlineKeyboardButton(text="🔍 Найти по имени", callback_data="find_by_name")],
        [InlineKeyboardButton(text="📚 Найти по классу", callback_data="find_by_grade")],
        [InlineKeyboardButton(text="📋 Помощь", callback_data="help")],
    ])

# --- Команда /help ---
@router.message(Command('help'))
async def cmd_help(message: Message):
    help_text = (
        "📋 Доступные команды:\n\n"
        "/start — начать работу с ботом\n"
        "/add — добавить нового студента\n"
        "/edit — выбрать и изменить данные студента\n"
        "/del — выбрать и удалить студента\n"
        "/find_by_name — найти студента по имени\n"
        "/find_by_grade — найти всех студентов по классу\n"
        "/help — показать это сообщение"
    )
    await message.answer(help_text, reply_markup=main_menu())

# --- Команда /start ---
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user_name = message.from_user.first_name or "Пользователь"
    await message.answer(
        f"Привет, {user_name}! 👋\n\n"
        "Я бот для управления данными студентов.\n\n"
        "Выбери действие ниже:",
        reply_markup=main_menu()
    )
    await state.clear()

# --- Команда /add ---
@router.message(Command('add'))
@router.callback_query(F.data == "add")
async def cmd_add(event: Message | CallbackQuery, state: FSMContext):
    # Проверяем, что пришло — message или callback
    if isinstance(event, CallbackQuery):
        await event.message.answer("Введите имя студента:")
        await event.answer()  # Убираем "часики" на кнопке
    else:  # isinstance(event, Message)
        await event.answer("Введите имя студента:")

    await state.set_state(StudentForm.waiting_for_name)

# --- Добавить студента ---
@router.message(StudentForm.waiting_for_name, F.text)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Спасибо! Теперь введите возраст:")
    await state.set_state(StudentForm.waiting_for_age)

@router.message(StudentForm.waiting_for_age, F.text)
async def process_age(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Введите число!")
        return
    await state.update_data(age=int(message.text))
    await message.answer("Отлично! Теперь введите класс (например, 5Б):")
    await state.set_state(StudentForm.waiting_for_grade)

@router.message(StudentForm.waiting_for_grade, F.text)
async def process_grade(message: Message, state: FSMContext):
    await state.update_data(grade=message.text)
    user_data = await state.get_data()

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            INSERT INTO students (name, age, grade, data) 
            VALUES (?, ?, ?, ?)
        ''', (user_data['name'], user_data['age'], user_data['grade'], datetime.now()))
        await db.commit()

    await message.answer(
        f"✅ Студент добавлен!\n"
        f"Имя: {user_data['name']}\n"
        f"Возраст: {user_data['age']}\n"
        f"Класс: {user_data['grade']}"
    )
    await message.answer("Выберите следующее действие:", reply_markup=main_menu())
    await state.clear()

# --- Найти по имени ---
@router.message(Command('find_by_name'))
@router.callback_query(F.data == "find_by_name")
async def find_by_name_cmd(call: CallbackQuery | Message, state: FSMContext):
    if isinstance(call, CallbackQuery):
        await call.message.answer("Введите имя для поиска (или оставьте пустым, чтобы показать всех):")
        await call.answer()
    else:
        await call.answer("Введите имя для поиска (или оставьте пустым, чтобы показать всех):")
    await state.set_state(FindStudentForm.waiting_name)

@router.message(FindStudentForm.waiting_name, F.text)
async def process_find_by_name(message: Message, state: FSMContext):
    search_name = message.text.strip()

    async with aiosqlite.connect(DB_NAME) as db:
        if search_name:
            cursor = await db.execute('''
                SELECT id, name, age, grade, data FROM students 
                WHERE LOWER(name) LIKE ? 
                ORDER BY name
            ''', (f'%{search_name.lower()}%',))
        else:
            cursor = await db.execute('''
                SELECT id, name, age, grade, data FROM students 
                ORDER BY name
            ''')

        rows = await cursor.fetchall()

    if rows:
        result = "📋 Найденные студенты:\n\n"
        for row in rows:
            result += f"🔹 ID: {row[0]} | {row[1]}, {row[2]} лет, {row[3]}\n📅 {row[4]}\n\n"
    else:
        result = "❌ Нет студентов."

    await message.answer(result)
    await message.answer("Выберите следующее действие:", reply_markup=main_menu())
    await state.clear()

# --- Найти по классу ---
@router.message(Command('find_by_grade'))
@router.callback_query(F.data == "find_by_grade")
async def find_by_grade_cmd(call: CallbackQuery | Message, state: FSMContext):
    if isinstance(call, CallbackQuery):
        await call.message.answer("Введите класс (например, 8А):")
        await call.answer()
    else:
        await call.answer("Введите класс (например, 8А):")
    await state.set_state(FindStudentForm.waiting_grade)

@router.message(FindStudentForm.waiting_grade, F.text)
async def process_find_by_grade(message: Message, state: FSMContext):
    grade = message.text.strip()

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute('''
            SELECT id, name, age, grade, data FROM students 
            WHERE LOWER(grade) = ? 
            ORDER BY name
        ''', (grade.lower(),))
        rows = await cursor.fetchall()

    if rows:
        result = f"📋 Студенты класса {grade}:\n\n"
        for row in rows:
            result += f"🔹 ID: {row[0]} | {row[1]}, {row[2]} лет\n📅 {row[4]}\n\n"
    else:
        result = f"❌ Нет студентов в классе {grade}."

    await message.answer(result)
    await message.answer("Выберите следующее действие:", reply_markup=main_menu())
    await state.clear()

# --- Изменить студента ---
@router.message(Command('edit'))
@router.callback_query(F.data == "edit")
async def edit_student_start(call: CallbackQuery | Message, state: FSMContext):
    if isinstance(call, CallbackQuery):
        await call.message.answer("Введите имя или ID студента для редактирования:")
        await call.answer()
    else:
        await call.answer("Введите имя или ID студента для редактирования:")
    await state.set_state(EditStudentForm.waiting_select)

# --- (остальные шаги редактирования без изменений) ---
@router.message(EditStudentForm.waiting_select, F.text)
async def edit_select_student(message: Message, state: FSMContext):
    search = message.text.strip()
    async with aiosqlite.connect(DB_NAME) as db:
        if search.isdigit():
            cursor = await db.execute('SELECT id, name, age, grade FROM students WHERE id = ?', (int(search),))
        else:
            cursor = await db.execute('''
                SELECT id, name, age, grade FROM students 
                WHERE LOWER(name) LIKE ? 
                ORDER BY name LIMIT 5
            ''', (f'%{search.lower()}%',))
        rows = await cursor.fetchall()

    if not rows:
        await message.answer("❌ Студент не найден.")
        await message.answer("Выберите действие:", reply_markup=main_menu())
        await state.clear()
        return

    if len(rows) == 1:
        student = rows[0]
        await state.update_data(edit_student_id=student[0])
        await message.answer(
            f"🔧 Редактируем: {student[1]}, {student[2]} лет, класс: {student[3]}\n"
            "Что изменить?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📝 Имя", callback_data="edit_name")],
                [InlineKeyboardButton(text="📅 Возраст", callback_data="edit_age")],
                [InlineKeyboardButton(text="🏫 Класс", callback_data="edit_grade")],
                [InlineKeyboardButton(text="🔙 Отмена", callback_data="cancel_edit")]
            ])
        )
        await state.set_state(EditStudentForm.waiting_field)
    else:
        result = "Выберите ID студента:\n\n"
        for r in rows:
            result += f"🔹 {r[0]}: {r[1]}, {r[2]} лет, {r[3]}\n"
        await message.answer(result + "\nВведите ID:")
        await state.set_state(EditStudentForm.waiting_select)

@router.callback_query(F.data.in_({"edit_name", "edit_age", "edit_grade"}))
async def edit_choose_field(call: CallbackQuery, state: FSMContext):
    field_map = {
        "edit_name": "имя",
        "edit_age": "возраст",
        "edit_grade": "класс"
    }
    await state.update_data(edit_field=field_map[call.data])
    await call.message.answer(f"Введите новое значение:")
    await state.set_state(EditStudentForm.waiting_value)
    await call.answer()

@router.message(EditStudentForm.waiting_value, F.text)
async def edit_set_value(message: Message, state: FSMContext):
    user_data = await state.get_data()
    student_id = user_data['edit_student_id']
    field = user_data['edit_field']
    new_value = message.text

    field_map = {
        "имя": ("name", str),
        "возраст": ("age", int),
        "класс": ("grade", str),
    }

    db_field, cast = field_map[field]
    try:
        if cast == int and not new_value.isdigit():
            raise ValueError("не число")
        value = cast(new_value)

        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute(f'UPDATE students SET {db_field} = ?, data = ? WHERE id = ?',
                             (value, datetime.now(), student_id))
            await db.commit()

        await message.answer(f"✅ Поле '{field}' успешно обновлено на '{new_value}'")
    except Exception:
        await message.answer("❌ Ошибка: неверный формат данных.")
    finally:
        await message.answer("Выберите действие:", reply_markup=main_menu())
        await state.clear()

@router.callback_query(F.data == "cancel_edit")
async def cancel_edit(call: CallbackQuery, state: FSMContext):
    await call.message.answer("Редактирование отменено.")
    await call.message.answer("Выберите действие:", reply_markup=main_menu())
    await state.clear()
    await call.answer()

# --- Удалить студента ---
@router.message(Command('del'))
@router.callback_query(F.data == "del")
async def delete_student_start(call: CallbackQuery | Message, state: FSMContext):
    if isinstance(call, CallbackQuery):
        await call.message.answer("Введите имя или ID студента для удаления:")
        await call.answer()
    else:
        await call.answer("Введите имя или ID студента для удаления:")
    await state.set_state(DeleteStudentForm.waiting_select)

@router.message(DeleteStudentForm.waiting_select, F.text)
async def delete_select_student(message: Message, state: FSMContext):
    search = message.text.strip()
    async with aiosqlite.connect(DB_NAME) as db:
        if search.isdigit():
            cursor = await db.execute('SELECT id, name, age, grade FROM students WHERE id = ?', (int(search),))
        else:
            cursor = await db.execute('''
                SELECT id, name, age, grade FROM students 
                WHERE LOWER(name) LIKE ? 
                ORDER BY name LIMIT 5
            ''', (f'%{search.lower()}%',))
        rows = await cursor.fetchall()

    if not rows:
        await message.answer("❌ Студент не найден.")
        await message.answer("Выберите действие:", reply_markup=main_menu())
        await state.clear()
        return

    if len(rows) == 1:
        student = rows[0]
        await state.update_data(delete_student_id=student[0])
        await message.answer(
            f"⚠️ Вы уверены, что хотите удалить:\n{student[1]}, {student[2]} лет, класс: {student[3]}?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Да, удалить", callback_data="confirm_delete")],
                [InlineKeyboardButton(text="❌ Нет", callback_data="cancel_delete")]
            ])
        )
    else:
        result = "Выберите ID:\n\n"
        for r in rows:
            result += f"🔹 {r[0]}: {r[1]}, {r[2]} лет, {r[3]}\n"
        await message.answer(result + "\nВведите ID:")
        await state.set_state(DeleteStudentForm.waiting_select)

@router.callback_query(F.data == "confirm_delete")
async def confirm_delete(call: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    student_id = user_data['delete_student_id']

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('DELETE FROM students WHERE id = ?', (student_id,))
        await db.commit()

    await call.message.answer("✅ Студент удалён.")
    await call.message.answer("Выберите действие:", reply_markup=main_menu())
    await state.clear()
    await call.answer()

@router.callback_query(F.data == "cancel_delete")
async def cancel_delete(call: CallbackQuery, state: FSMContext):
    await call.message.answer("❌ Удаление отменено.")
    await call.message.answer("Выберите действие:", reply_markup=main_menu())
    await state.clear()
    await call.answer()

# --- Обработчик всех callback-кнопок ---
@router.callback_query(F.data == "help")
async def callback_help(call: CallbackQuery):
    help_text = (
        "📋 Доступные команды:\n\n"
        "/start — начать работу с ботом\n"
        "/add — добавить нового студента\n"
        "/edit — выбрать и изменить данные студента\n"
        "/del — выбрать и удалить студента\n"
        "/find_by_name — найти студента по имени\n"
        "/find_by_grade — найти всех студентов по классу\n"
        "/help — показать это сообщение"
    )
    await call.message.answer(help_text, reply_markup=main_menu())
    await call.answer()

# --- Запуск ---
dp.include_router(router)

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())