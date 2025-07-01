from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from dotenv import load_dotenv
from keep_alive import keep_alive
import os
import json

# === YUKLAMALAR ===
load_dotenv()
keep_alive()

API_TOKEN = os.getenv("API_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
BOT_USERNAME = os.getenv("BOT_USERNAME")

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

ADMINS = [6486825926]

# === FAYLLAR ===

def load_codes():
    try:
        with open("kino_posts.json", "r") as f:
            return json.load(f)
    except:
        return {}

def save_codes(data):
    with open("kino_posts.json", "w") as f:
        json.dump(data, f, indent=4)

def load_users():
    try:
        with open("users.json", "r") as f:
            return json.load(f)
    except:
        return []

def save_users(data):
    with open("users.json", "w") as f:
        json.dump(data, f, indent=4)

# === HOLATLAR ===

class AdminStates(StatesGroup):
    waiting_for_kino_data = State()
    waiting_for_remove_code = State()

# === OBUNA TEKSHIRISH ===

async def is_user_subscribed(user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

# === /start ===

@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    # Foydalanuvchini bazaga yozish
    users = load_users()
    if message.from_user.id not in users:
        users.append(message.from_user.id)
        save_users(users)

    args = message.get_args()
    if args and args.isdigit():
        code = args
        if not await is_user_subscribed(message.from_user.id):
            markup = InlineKeyboardMarkup().add(
                InlineKeyboardButton("📢 Kanalga obuna bo‘lish", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}"),
                InlineKeyboardButton("✅ Tekshirish", callback_data=f"check_sub:{code}")
            )
            await message.answer("❗ Kino olishdan oldin kanalga obuna bo‘ling:", reply_markup=markup)
        else:
            await send_kino_by_code(message.from_user.id, code)
    else:
        if message.from_user.id in ADMINS:
            markup = ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("➕ Kino qo‘shish", "❌ Kodni o‘chirish")
            markup.add("📄 Kodlar ro‘yxati", "📊 Statistika")
            await message.answer("👮‍♂️ Admin panel:", reply_markup=markup)
        else:
            await message.answer("🎬 Botga xush kelibsiz!\nKino olish uchun tugmani bosing yoki kod yuboring.")

@dp.callback_query_handler(lambda c: c.data.startswith("check_sub:"))
async def check_sub(callback: types.CallbackQuery):
    code = callback.data.split(":")[1]
    if await is_user_subscribed(callback.from_user.id):
        await callback.message.edit_text("✅ Obuna tasdiqlandi, kino yuborilmoqda...")
        await send_kino_by_code(callback.from_user.id, code)
    else:
        await callback.answer("❗ Hali ham obuna emassiz!", show_alert=True)

# === KINO YUBORISH ===

async def send_kino_by_code(user_id, code):
    kino_data = load_codes()
    if code in kino_data:
        data = kino_data[code]
        await bot.copy_message(
            chat_id=user_id,
            from_chat_id=data["channel"],
            message_id=data["message_id"]
        )
    else:
        await bot.send_message(user_id, "❌ Bunday kino topilmadi.")

# === ➕ KINO QO‘SHISH ===

@dp.message_handler(lambda m: m.text == "➕ Kino qo‘shish")
async def add_kino_start(message: types.Message):
    if message.from_user.id in ADMINS:
        await message.answer("📝 Kino kodi, kanal va post ID yuboring:\nMasalan:\n`47 @ServerChannel 1234`", parse_mode="Markdown")
        await AdminStates.waiting_for_kino_data.set()

@dp.message_handler(state=AdminStates.waiting_for_kino_data)
async def add_kino_handler(message: types.Message, state: FSMContext):
    parts = message.text.strip().split()
    if len(parts) != 3 or not parts[0].isdigit() or not parts[2].isdigit():
        await message.answer("❌ Noto‘g‘ri format!\nMasalan: `47 @ServerChannel 1234`")
        return

    code, channel, msg_id = parts
    kino_data = load_codes()

    # Saqlanadigan post ID kino fayl (ya'ni reklama +1)
    kino_data[code] = {
        "channel": channel,
        "message_id": int(msg_id) + 1
    }
    save_codes(kino_data)

    # Reklama postni kanalga yuborish
    yukla_url = f"https://t.me/{BOT_USERNAME.strip('@')}?start={code}"
    reklama = f"🎬 Yangi kino chiqdi!\n\nKod: `{code}`\n\n📥 Yuklab olish👇"
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("📥 Yuklab olish", url=yukla_url))
    await bot.send_message(chat_id=CHANNEL_USERNAME, text=reklama, reply_markup=markup, parse_mode="Markdown")

    await message.answer("✅ Kino qo‘shildi va reklama post kanalga yuborildi!")
    await state.finish()


# === ❌ KODNI O‘CHIRISH ===

@dp.message_handler(lambda m: m.text == "❌ Kodni o‘chirish")
async def remove_kino_start(message: types.Message):
    if message.from_user.id in ADMINS:
        await message.answer("🗑 O‘chirmoqchi bo‘lgan kodni yuboring:")
        await AdminStates.waiting_for_remove_code.set()

@dp.message_handler(state=AdminStates.waiting_for_remove_code)
async def remove_kino_handler(message: types.Message, state: FSMContext):
    code = message.text.strip()
    kino_data = load_codes()
    if code in kino_data:
        del kino_data[code]
        save_codes(kino_data)
        await message.answer(f"✅ Kod o‘chirildi: {code}")
    else:
        await message.answer("❌ Bunday kod topilmadi.")
    await state.finish()

# === 📄 KODLAR RO‘YXATI ===

@dp.message_handler(lambda m: m.text == "📄 Kodlar ro‘yxati")
async def list_kodlar(message: types.Message):
    kino_data = load_codes()
    if not kino_data:
        await message.answer("📂 Hech qanday kod yo‘q.")
        return
    text = "📄 Kodlar ro‘yxati:\n"
    for code, data in kino_data.items():
        text += f"🔹 Kod: {code} | Kanal: {data['channel']} | ID: {data['message_id']}\n"
    await message.answer(text)

# === 📊 STATISTIKA ===

@dp.message_handler(lambda m: m.text == "📊 Statistika")
async def stats(message: types.Message):
    kino_data = load_codes()
    users = load_users()
    await message.answer(f"📦 Kodlar soni: {len(kino_data)}\n👥 Foydalanuvchilar: {len(users)}")

# === ISHGA TUSHIRISH ===

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
