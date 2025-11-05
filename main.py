import asyncio
import random
import requests #Для выполнения HTTP-запросов к внешним API
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message,FSInputFile
from config import TG_TOKEN, OPENWEATHER_API_KEY
from gtts import gTTS
from googletrans import Translator
from gtts import gTTS


# Напишите код для сохранения всех фото, которые отправляет пользователь боту в папке img
# Отправьте с помощью бота голосовое сообщение
# Напишите код для перевода любого текста, который пишет пользователь боту, на английский язык

bot = Bot(token=TG_TOKEN)
dp = Dispatcher()
#Путь к папке для сохранения фото
PHOTO_DIR = "img"
os.makedirs(PHOTO_DIR, exist_ok=True)  # Создаём папку, если её нет

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(f"Привет, {message.from_user.first_name}!")

@dp.message(Command('help'))
async def help(message: Message):
    await message.answer("Этот бот отвечает на команды: \n "
                         "/start - начало диалога \n "
                         "/help - помощь \n"
                         "Отправь мне фото и я сохраню его в папке img \n" 
                         "/photo - случайное фото из папки img\n"
                         "/weather - прогноз погоды \n"
                         "/voice_ru <сообщение> - напиши что-нибудь и я прочитаю его \n"
                         "/voice_ru <сообщение> - напиши что-нибудь и я прочитаю его")

@dp.message(Command('weather'))
async def weather(message: Message):
    city = 'Moscow'
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ru"
    try:
        response = requests.get(url)  # Отправка запроса
        data = response.json()  # Парсинг ответа в словарь
        if response.status_code == 200:  # Проверка на успешность запроса
            weather_info = (
                f" Погода в г.{city}:\n"
                f" Температура:  {data['main']['temp']} °C\n"
                f" Состояние:  {data['weather'][0]['description']} \n"
                f" Влажность:  {data['main']['humidity']} %\n"
                f" Ветер:  {data['wind']['speed']} м/с"
            )
        else:
            if response.status_code == 404:
                weather_info = "Город не найден"
            else:
                weather_info = f"Ошибка при получении информации о погоде: {response.status_code}"
    except Exception as e:
        weather_info = f"Ошибка при получении информации о погоде: {e}"
    await message.answer(weather_info)

@dp.message(F.text == "что такое ИИ?")
async def aitext(message: Message):
    await message.answer('ИИ - это искусственный интеллект')

@dp.message(F.photo)
async def react_photo(message: Message):
    # Генерация имени файла
    photo = message.photo[-1]  # Берём фото наилучшего качества
    file_name = f"{PHOTO_DIR}/{photo.file_id}.jpg"

    # Скачивание фото
    await bot.download(photo, destination=file_name)
    await message.answer("Фото сохранено!")

    # Произвольный ответ
    list = ['Ого, какая фотка!',
            'Непонятно, что это такое',
            'Не отправляй мне такое больше'
    ]
    rand_answ = random.choice(list)
    await message.answer(rand_answ)

@dp.message(Command('photo'))
async def photo(message: Message):
    # Путь к папке с фото
    photo_dir = "img"

    # Проверяем, существует ли папка
    if not os.path.exists(photo_dir):
        await message.answer("Папка img не найдена!")
        return

    # Получаем список файлов, оставляем только изображения
    photo_extensions = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif')
    photos = [f for f in os.listdir(photo_dir) if f.lower().endswith(photo_extensions)]

    # Если нет фото — сообщаем об этом
    if not photos:
        await message.answer("В папке img нет фото!")
        return

    # Выбираем случайное фото
    random_photo = random.choice(photos)
    photo_path = os.path.join(photo_dir, random_photo)

    # Отправляем фото
    try:
        await message.answer_photo(
            photo=FSInputFile(photo_path),
            caption=f"Случайное фото: {random_photo}"
        )
    except Exception as e:
        await message.answer(f"Не удалось отправить фото: {e}")

@dp.message(Command('voice'))
async def send_voice(message: Message):
    # Голосовое сообщение (файл должен быть в папке или можно использовать ссылку)
    # Здесь пример с готовым .ogg файлом. Создайте или загрузите voice.ogg
    voice = FSInputFile("voice.ogg")
    await message.answer_voice(voice, caption="Вот тебе голосовое сообщение!")

@dp.message(Command('voice_en'))
async def voice_en(message: Message):
    try:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.answer("Введите текст после команды. Например: /voice_en Привет!")
            return
        text_to_speak = parts[1].strip()
        # Инициализация переводчика
        translator = Translator()

        # Перевод текста с любого языка на английский
        # (src='auto' определяет язык автоматически)
        translation = translator.translate(text_to_speak, src='auto', dest='en')
        translated_text = translation.text

        # Отправляем текст перевода
        await message.reply(f"🇬🇧 {translated_text}")

        await send_voice_message(message, translated_text, lang='en')

    except Exception as e:
        await message.reply("Не удалось перевести или озвучить текст.")
        print(f"Ошибка: {e}")  # Для отладки в консоли

@dp.message(Command('voice_ru'))
async def voice_ru(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Введите текст после команды. Например: /voice_ru Привет!")
        return
    text_to_speak = parts[1].strip()
    await message.answer(f"📢 {text_to_speak}")

    await send_voice_message(message,text_to_speak, lang='ru')

async def send_voice_message(message: Message, text: str, lang: str = 'en'):
    """
    Функция для озвучивания текста и отправки его как голосового сообщения
    :param message: объект сообщения от пользователя (нужен для контекста)
    :param text: текст, который нужно озвучить
    :param lang: язык озвучки (по умолчанию — английский)
    """
    try:
        # Создаём объект для синтеза речи
        tts = gTTS(text=text, lang=lang)

        # Имя временного файла
        voice_file = "temp_voice_message.ogg"

        # Сохраняем аудио
        tts.save(voice_file)

        # Отправляем голосовое сообщение
        voice = FSInputFile(voice_file)
        await message.answer_voice(voice)

        # Удаляем файл после отправки
        os.remove(voice_file)

    except Exception as e:
        await message.answer(f"Не удалось создать голосовое сообщение: {e}")
        print(f"Ошибка в send_voice_message: {e}")

@dp.message()
async def answer_msg(message: Message):
     str = f"Я не знаю, что ответить на '{message.text}'"
     await message.answer(str)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())