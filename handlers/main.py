from aiogram import Router, F, types
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import Message, CallbackQuery
from models.roles import roles

router = Router()

builder = InlineKeyboardBuilder()
builder.add(
    types.InlineKeyboardButton(text="➕ Добавить бота в чат", url="https://t.me/mafiamingbot?startgroup=true"),
    types.InlineKeyboardButton(text="🎭 Роли", callback_data="roles")
).adjust(1)

@router.message(CommandStart())
async def cmd_start(message: Message):
    
    await message.answer('''
    Привет!
Я бот для игры в <b>🤵🏻 Мафию</b>.'''
    , reply_markup=builder.as_markup())

@router.callback_query(F.data == "back")
async def back_to_menu(callback: CallbackQuery):
    await callback.message.edit_text('''
    Привет!
Я бот для игры в <b>🤵🏻 Мафию</b>.''', reply_markup=builder.as_markup())

@router.callback_query(F.data == "roles")
async def show_roles(callback: CallbackQuery):
    builder = InlineKeyboardBuilder()
    for role in roles:
        builder.add(
            types.InlineKeyboardButton(text=role.name, callback_data=f"info_{role.name}")
        )
    builder.adjust(2)
    builder.add(
        types.InlineKeyboardButton(text="🔙 Назад", callback_data="back")
    )
    await callback.message.edit_text("Выберите роль:", reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("info_"))
async def show_role_info(callback: CallbackQuery):
    role_name = callback.data.split("_")[1]
    role = next((role for role in roles if role.name == role_name), None)
    if role:
        await callback.answer(role.description, show_alert=True)


@router.message(F.animation | F.photo | F.video | F.document)
async def send_media(message: Message):
    await message.answer(message.animation.file_id if message.animation else message.photo[0].file_id if message.photo else message.video.file_id if message.video else message.document.file_id)