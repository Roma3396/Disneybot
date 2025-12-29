import asyncio
import logging
import os
import psycopg2
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# --- KONFIGURATSIYA ---
TOKEN = "8511080877:AAFaQLkJtpezZfzuwt897HJSNOgAaK0rDXQ"
ADMINS = [7829422043, 6881599988]
CHANNEL_ID = -1003155796926
CHANNEL_LINK = "https://t.me/FeaF_Helping"
DB_URL = os.getenv("DATABASE_URL")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- POSTGRESQL MA'LUMOTLAR BAZASI ---
def get_db_connection():
    return psycopg2.connect(DB_URL)

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS films 
                 (id SERIAL PRIMARY KEY, photo TEXT, video TEXT, name TEXT, year TEXT, code TEXT, "desc" TEXT, likes INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS favorites (user_id BIGINT, film_id INTEGER)''')
    conn.commit()
    c.close()
    conn.close()

init_db()

# --- STATES ---
class AdminState(StatesGroup):
    waiting_for_photo = State()
    waiting_for_video = State()
    waiting_for_name = State()
    waiting_for_year = State()
    waiting_for_code = State()
    waiting_for_desc = State()
    waiting_for_post = State()
    waiting_for_reply = State()

class UserState(StatesGroup):
    waiting_for_search = State()
    waiting_for_support = State()

# --- KEYBOARDS ---
def main_menu(user_id):
    kb = [
        [KeyboardButton(text="🔍 Qidiruv"), KeyboardButton(text="🔥 Rek")],
        [KeyboardButton(text="💾 Saqlangan"), KeyboardButton(text="📩 Murojat")]
    ]
    if user_id in ADMINS:
        kb.append([KeyboardButton(text="🎬 Film joylash"), KeyboardButton(text="📢 Post Joylash")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def back_kb():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🔙 Orqaga")]], resize_keyboard=True)

def sub_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Kanalga o'tish", url=CHANNEL_LINK)],
        [InlineKeyboardButton(text="Tasdiqlash ✅", callback_data="check_sub")]
    ])

# --- FUNKSIYALAR ---
async def check_sub(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["creator", "administrator", "member"]
    except:
        return False

async def send_film_card(chat_id, film):
    # film: (id, photo, video, name, year, code, desc, likes)
    text = f"🎬 **{film[3]}**\n\n📅 Yili: {film[4]}\n🔢 Kodi: {film[5]}\n📝 Izoh: {film[6]}\n\n❤️ {film[7]} ta like"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Chapga", callback_data=f"prev_{film[0]}"),
         InlineKeyboardButton(text=f"❤️ {film[7]}", callback_data=f"like_{film[0]}"),
         InlineKeyboardButton(text="💾 Saqlash", callback_data=f"save_{film[0]}"),
         InlineKeyboardButton(text="➡️ O'nga", callback_data=f"next_{film[0]}")],
        [InlineKeyboardButton(text="👁 Tomosha qilish", callback_data=f"watch_{film[0]}")]
    ])
    await bot.send_photo(chat_id, film[1], caption=text, reply_markup=kb, parse_mode="Markdown")

# --- HANDLERS ---
@dp.message(CommandStart())
async def start(message: types.Message):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO users (user_id) VALUES (%s) ON CONFLICT DO NOTHING", (message.from_user.id,))
    conn.commit()
    c.close()
    conn.close()
    
    if await check_sub(message.from_user.id):
        await message.answer(f"Salom {message.from_user.full_name}! Botga xush kelibsiz 🎥", reply_markup=main_menu(message.from_user.id))
    else:
        await message.answer("Botdan foydalanish uchun kanalga obuna bo'ling!", reply_markup=sub_kb())

@dp.callback_query(F.data == "check_sub")
async def verify_sub(call: types.CallbackQuery):
    if await check_sub(call.from_user.id):
        await call.message.delete()
        await call.message.answer("Obuna tasdiqlandi! Asosiy menyu:", reply_markup=main_menu(call.from_user.id))
    else:
        await call.answer("Hali obuna bo'lmagansiz!", show_alert=True)

# --- FILM JOYLASH ---
@dp.message(F.text == "🎬 Film joylash", F.from_user.id.in_(ADMINS))
async def add_film(message: types.Message, state: FSMContext):
    await state.set_state(AdminState.waiting_for_photo)
    await message.answer("Film uchun rasm yuboring:", reply_markup=back_kb())

@dp.message(AdminState.waiting_for_photo, F.photo)
async def get_photo(message: types.Message, state: FSMContext):
    await state.update_data(photo=message.photo[-1].file_id)
    await state.set_state(AdminState.waiting_for_video)
    await message.answer("Endi film videosini yuboring:")

@dp.message(AdminState.waiting_for_video, F.video)
async def get_video(message: types.Message, state: FSMContext):
    await state.update_data(video=message.video.file_id)
    await state.set_state(AdminState.waiting_for_name)
    await message.answer("Film nomini yozing:")

@dp.message(AdminState.waiting_for_name)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AdminState.waiting_for_year)
    await message.answer("Film yilini yozing:")

@dp.message(AdminState.waiting_for_year)
async def get_year(message: types.Message, state: FSMContext):
    await state.update_data(year=message.text)
    await state.set_state(AdminState.waiting_for_code)
    await message.answer("Film kodini kiriting:")

@dp.message(AdminState.waiting_for_code)
async def get_code(message: types.Message, state: FSMContext):
    await state.update_data(code=message.text)
    await state.set_state(AdminState.waiting_for_desc)
    await message.answer("Film uchun izoh yozing:")

@dp.message(AdminState.waiting_for_desc)
async def save_film(message: types.Message, state: FSMContext):
    data = await state.get_data()
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO films (photo, video, name, year, code, \"desc\") VALUES (%s,%s,%s,%s,%s,%s)",
              (data['photo'], data['video'], data['name'], data['year'], data['code'], message.text))
    conn.commit()
    c.close()
    conn.close()
    await state.clear()
    await message.answer("Film saqlandi! ✅", reply_markup=main_menu(message.from_user.id))

# --- REK VA QIDIRUV ---
@dp.message(F.text == "🔥 Rek")
async def show_rek(message: types.Message):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM films ORDER BY id DESC LIMIT 1")
    film = c.fetchone()
    c.close()
    conn.close()
    if film: await send_film_card(message.chat.id, film)
    else: await message.answer("Filmlar yo'q.")

@dp.message(F.text == "🔍 Qidiruv")
async def search_start(message: types.Message, state: FSMContext):
    await state.set_state(UserState.waiting_for_search)
    await message.answer("Kod yoki nom yozing:", reply_markup=back_kb())

@dp.message(UserState.waiting_for_search)
async def search_result(message: types.Message, state: FSMContext):
    if message.text == "🔙 Orqaga":
        await state.clear()
        return await message.answer("Menyu", reply_markup=main_menu(message.from_user.id))
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM films WHERE code = %s OR name ILIKE %s", (message.text, f'%{message.text}%'))
    film = c.fetchone()
    c.close()
    conn.close()
    if film: await send_film_card(message.chat.id, film)
    else: await message.answer("Topilmadi.")

# --- CALLBACK ACTIONS ---
@dp.callback_query(F.data.startswith(("next_", "prev_", "like_", "save_", "watch_")))
async def film_actions(call: types.CallbackQuery):
    action, f_id = call.data.split("_")
    conn = get_db_connection()
    c = conn.cursor()
    if action == "watch":
        c.execute("SELECT video FROM films WHERE id = %s", (f_id,))
        v = c.fetchone()
        if v: await bot.send_video(call.message.chat.id, v[0])
    elif action == "like":
        c.execute("UPDATE films SET likes = likes + 1 WHERE id = %s", (f_id,))
        conn.commit()
        await call.answer("❤️")
    elif action == "save":
        c.execute("INSERT INTO favorites (user_id, film_id) VALUES (%s,%s)", (call.from_user.id, f_id))
        conn.commit()
        await call.answer("Saqlandi")
    c.close()
    conn.close()

# --- MUROJAT VA POST ---
@dp.message(F.text == "📩 Murojat")
async def support(message: types.Message, state: FSMContext):
    await state.set_state(UserState.waiting_for_support)
    await message.answer("Murojatingizni yozing:", reply_markup=back_kb())

@dp.message(UserState.waiting_for_support)
async def send_support(message: types.Message, state: FSMContext):
    if message.text == "🔙 Orqaga":
        await state.clear()
        return await message.answer("Menyu", reply_markup=main_menu(message.from_user.id))
    for admin in ADMINS:
        await bot.send_message(admin, f"📩 Murojat: {message.text}\nKimdan: {message.from_user.id}")
    await message.answer("Yuborildi!")
    await state.clear()

@dp.message(F.text == "📢 Post Joylash", F.from_user.id.in_(ADMINS))
async def post_start(message: types.Message, state: FSMContext):
    await state.set_state(AdminState.waiting_for_post)
    await message.answer("Postni yuboring:")

@dp.message(AdminState.waiting_for_post)
async def broadcast(message: types.Message, state: FSMContext):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = c.fetchall()
    c.close()
    conn.close()
    for u in users:
        try: await message.copy_to(u[0])
        except: pass
    await message.answer("Tugadi!")
    await state.clear()

@dp.message(F.text == "🔙 Orqaga")
async def go_back(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Menyu", reply_markup=main_menu(message.from_user.id))

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
