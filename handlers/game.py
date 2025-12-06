from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
import time
from database import *
from utils.func import get_role_by_id, get_role_full_name, get_role_type
from filters.mafia import MafiaChatFilter
from filters.dead import DeadLastMessageFilter

router = Router()

@router.message(DeadLastMessageFilter())
async def handle_dead_last_message(message: Message):
    user = await get_user(message.from_user.id)
    game = await get_game(user.game_id)
    
    if not user or not game:
        return
    
    await update_user(user.telegram_id, last_message_sent=True)
    
    message_text = message.text or message.caption or ""
    user_name = user.first_name

    from bot import bot
    await bot.send_message(
        game.chat_id,
        f"💀 Кто-то из жителей слышал, как <b>{user_name}</b> кричал перед смертью:\n\n<i>{message_text}</i>"
    )

@router.message(MafiaChatFilter())
async def handle_mafia_message(message: Message):
    user = await get_user(message.from_user.id)
    game = await get_game(user.game_id)

    sender_name = "Дон" if user.role == "don" else "Мафия"
    sender_display_name = user.first_name
    
    message_text = message.text or message.caption or ""
    formatted_message = f"<b>{sender_name} {sender_display_name}:</b>\n{message_text}"

    from bot import bot
    from utils.func import get_role_type
    
    for mafia_user in game.users:
        if mafia_user.is_alive and mafia_user.role:
            role_type = get_role_type(mafia_user.role)
            if role_type == "mafia" or mafia_user.role == "don":
                await bot.send_message(
                    mafia_user.telegram_id,
                    formatted_message
                )


TIME_TO_START = 30
EXTEND_TIME = 30

builder = InlineKeyboardBuilder()
builder.add(types.InlineKeyboardButton(
    text="Присоединиться",
    callback_data="join_game"
))
builder.add(
    types.InlineKeyboardButton(
        text="Выйти",
        callback_data="exit_game"
    )
)

@router.message(Command("new_game"))
async def new_game(message: types.Message):
    game = await get_game(message.chat.id)
    if game:
        await message.answer("Игра уже создана!")
        return
    
    user_id = message.from_user.id
    user_name = message.from_user.full_name

    mention = f"1. <a href='tg://user?id={user_id}'>{user_name}</a>"

    msg = await message.answer(
        f"Новая игра создана!\n\nИгроки:\n {mention}\n\nДо начала: {TIME_TO_START} сек.",
        reply_markup=builder.as_markup()
    )
    user = await create_user_if_not_exists(
        telegram_id=user_id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        in_game=True,
        game_id=message.chat.id,
    )
    game = await create_game(message.chat.id, time.time()+TIME_TO_START, msg.message_id)
    await add_user_to_game(message.chat.id, user_id)

@router.callback_query(F.data == "join_game")
async def join_game(callback: CallbackQuery):
    in_game = await is_in_game(callback.from_user.id)
    if in_game:
        await callback.answer("Вы уже в игре!", show_alert=True)
    else:
        await callback.answer("Вы присоединились!", show_alert=True)
        user = await create_user_if_not_exists(
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
            last_name=callback.from_user.last_name,
            in_game=True,
            game_id=callback.message.chat.id,
        )
        await add_user_to_game(callback.message.chat.id, user.telegram_id) 
        game = await get_game(callback.message.chat.id)
        users = game.users
        mentions = "\n".join([f"{index}. <a href='tg://user?id={user.telegram_id}'>{user.first_name}</a>" for index, user in enumerate(users, start=1)])
        await callback.message.edit_text(f"Новая игра создана!\n\nИгроки:\n{mentions}\n\nДо начала: {round(game.start_time - time.time())} сек.", reply_markup=builder.as_markup())

@router.callback_query(F.data == "new_game")
async def new_game_callback(callback: CallbackQuery):
    from aiogram.types import Message
    from database import delete_game, get_all_games
    
    existing_game = await get_game(callback.message.chat.id)
    if existing_game:
        await delete_game(callback.message.chat.id)
    
    all_games = await get_all_games()
    for game in all_games:
        if game.chat_id == callback.message.chat.id:
            await delete_game(callback.message.chat.id)
            break
    
    fake_message = Message(
        message_id=callback.message.message_id,
        date=callback.message.date,
        chat=callback.message.chat,
        from_user=callback.from_user,
        content_type="text",
        text="/new_game"
    )
    await new_game(fake_message)
    await callback.answer()

@router.callback_query(F.data == "exit_game")
async def exit_game(callback: CallbackQuery):
    await callback.answer("Вы вышли из игры!", show_alert=True)
    await remove_user_from_game(callback.message.chat.id, callback.from_user.id)
    game = await get_game(callback.message.chat.id)
    users = game.users
    mentions = "\n".join([f"{index}. <a href='tg://user?id={user.telegram_id}'>{user.first_name}</a>" for index, user in enumerate(users, start=1)])
    await callback.message.edit_text(f"Новая игра создана!\n\nИгроки:\n{mentions}\n\nДо начала: {round(game.start_time - time.time())} сек.", reply_markup=builder.as_markup())


@router.message(Command("extend"))
async def extend_game(message: Message):
    game = await get_game(message.chat.id)
    game.start_time += EXTEND_TIME
    await update_game(message.chat.id, start_time=game.start_time)
    await message.answer(f"Время до начала игры увеличено на {EXTEND_TIME} сек.")


@router.callback_query(F.data == "sheriff_action_check")
async def sheriff_action_check(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user or not user.game or user.role != "sheriff":
        await callback.answer("Ошибка!", show_alert=True)
        return
    
    game = user.game
    users = game.users
    
    builder = InlineKeyboardBuilder()
    for target_user in users:
        if target_user.is_alive and target_user.telegram_id != user.telegram_id:
            builder.add(
                types.InlineKeyboardButton(
                    text=target_user.first_name,
                    callback_data=f"sheriffcheck_choose_{target_user.telegram_id}",
                )
            )
    builder.adjust(1)
    
    await callback.message.edit_text(
        "Выберите игрока для проверки:",
        reply_markup=builder.as_markup()
    )

@router.callback_query(F.data == "sheriff_action_kill")
async def sheriff_action_kill(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user or not user.game or user.role != "sheriff":
        await callback.answer("Ошибка!", show_alert=True)
        return
    
    game = user.game
    users = game.users
    
    builder = InlineKeyboardBuilder()
    for target_user in users:
        if target_user.is_alive and target_user.telegram_id != user.telegram_id:
            builder.add(
                types.InlineKeyboardButton(
                    text=target_user.first_name,
                    callback_data=f"sheriffkill_choose_{target_user.telegram_id}",
                )
            )
    builder.adjust(1)
    
    await callback.message.edit_text(
        "Выберите игрока для убийства:",
        reply_markup=builder.as_markup()
    )

@router.callback_query(F.data.contains("_choose_"))
async def choose_user(callback: CallbackQuery):
    parts = callback.data.split("_")
    if len(parts) >= 3:
        if parts[0] == "sheriffcheck" or parts[0] == "sheriffkill":
            role_type = parts[0]
            target_id = int(parts[-1])
        else:
            role_type = parts[0]
            target_id = int(parts[-1])
    else:
        await callback.answer("Ошибка в данных!", show_alert=True)
        return

    user = await get_user(callback.from_user.id)
    target_user = await get_user(target_id)
    if not user or not user.game:
        await callback.answer("Вы не в игре!", show_alert=True)
        return
    game = user.game
    users = game.users
    if role_type == "mafia":
        await update_user(target_id, visitor_id=callback.from_user.id)
        await inc_mafia_choose(game.chat_id, target_id)

        has_don = any(u.is_alive and u.role == "don" for u in users)

        if not has_don:
            await inc_mafia_choose(game.chat_id, callback.from_user.id, 10)
            await callback.bot.send_message(game.chat_id, "🤵🏻 <b>Мафия</b> выбрала жертву...")
            await update_user(target_id, killer_id=callback.from_user.id)
        
        for mafia_user in users:
            if mafia_user.is_alive and mafia_user.role and get_role_type(mafia_user.role) == "mafia":
                _name = await get_name_by_id(target_id)
                await callback.bot.send_message(mafia_user.telegram_id, f"{callback.from_user.full_name} (Мафия) выбрал {_name}.")
    elif role_type == "don":
        await inc_mafia_choose(game.chat_id, target_id, 10)
        await update_user(target_id, killer_id=callback.from_user.id, visitor_id=callback.from_user.id)
        for mafia_user in users:
            if mafia_user.is_alive and mafia_user.role == "mafia":
                _name = await get_name_by_id(target_id)
                await callback.bot.send_message(mafia_user.telegram_id, f"{callback.from_user.full_name} (Дон) выбрал {_name}.")
        await callback.bot.send_message(game.chat_id, "🤵🏻 <b>Мафия</b> выбрала жертву...")
    elif role_type == "sheriffkill":
        await update_user(target_id, killer_id=callback.from_user.id, visitor_id=callback.from_user.id)
        await callback.bot.send_message(game.chat_id, "🕵️‍ <b>Шериф</b> уже зарядил свой пистолет...")
        
    elif role_type == "sheriffcheck":
        await update_user(target_id, visitor_id=callback.from_user.id)
        target_role_name = '👨🏼 Мирный житель' if target_user.advocate_saved else await get_role_by_id(target_id)
        await callback.message.answer(f"Роль игрока {await get_name_by_id(target_id)} - <b>{target_role_name}</b>")
        for sergeant_user in users:
            if sergeant_user.is_alive and sergeant_user.role == "sergeant":
                _name = await get_name_by_id(target_id)
                await callback.bot.send_message(sergeant_user.telegram_id, f"Шериф проверил {_name} и его роль - <b>{target_role_name}</b>")
        await callback.bot.send_message(game.chat_id, "🕵️‍ <b>Шериф</b> ушёл искать злодеев...")

    elif role_type == "doctor":
        await update_user(target_id, doctor_rescued=True, visitor_id=callback.from_user.id)
        await callback.bot.send_message(game.chat_id, "👨🏼‍⚕️ <b>Доктор</b> вышел на ночное дежурство...")

    elif role_type == "murderer":
        await update_user(target_id, killer_id=callback.from_user.id, visitor_id=callback.from_user.id)
        await callback.bot.send_message(game.chat_id, "🔪 <b>Маньяк</b> выбрал жертву...")

    elif role_type == "lover":
        await update_user(target_id, lover_affected=True, visitor_id=callback.from_user.id)
        await callback.bot.send_message(game.chat_id, "💃🏼 <b>Любовница</b> уже ждёт кого-то в гости...")

    elif role_type == "advocate":
        await update_user(target_id, advocate_saved=True, visitor_id=callback.from_user.id)
        await callback.bot.send_message(game.chat_id, "👨🏼‍💼 <b>Адвокат</b> ищет мафию для защиты...")
    
    elif role_type == "homeless":
        await update_user(target_id, homeless_visit=True)
        await callback.bot.send_message(game.chat_id, "🧙🏼‍♂️ <b>Бомж</b> пошёл к кому-то за бутылкой...")
        target_user = await get_user(target_id)
        if target_user and target_user.killer_id:
            _name = await get_name_by_id(target_id)
            _killer_name = await get_name_by_id(target_user.killer_id)
            homeless_user = await get_user(callback.from_user.id)
            await callback.bot.send_message(homeless_user.telegram_id, f"Ты увидел {_killer_name} когда ходил за бутылкой к {_name}.")
                
@router.callback_query(F.data.startswith("vote_for_"))
async def vote_for_player(callback: CallbackQuery):
    target_telegram_id = int(callback.data.split("_")[-1])
    
    if target_telegram_id == callback.from_user.id:
        await callback.answer("Вы не можете голосовать за себя!", show_alert=True)
        return

    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Вы не можете голосовать!", show_alert=True)
        return
    
    game = await get_game(callback.message.chat.id)
    if not game or not game.started:
        await callback.answer("Игра не началась!", show_alert=True)
        return
    
    from database import has_voted
    if await has_voted(game.chat_id, callback.from_user.id, game.day):
        await callback.answer("Вы уже проголосовали!", show_alert=True)
        return
    if not game or not game.started:
        await callback.answer("Игра не началась!", show_alert=True)
        return
    
    fresh_user = await get_user(callback.from_user.id)
    if not fresh_user:
        await callback.answer("Вы не можете голосовать!", show_alert=True)
        return
    
    if not fresh_user.in_game or not fresh_user.is_alive:
        await callback.answer("Вы не можете голосовать!", show_alert=True)
        return
    
    fresh_game = await get_game(callback.message.chat.id)
    
    if not fresh_game or fresh_game.current_phase != "voting":
        await callback.answer("Голосование не началось!", show_alert=True)
        return
    
    game = fresh_game
    
    target_user = await get_user(target_telegram_id)
    if not target_user or not target_user.is_alive:
        await callback.answer("Этот игрок уже мертв!", show_alert=True)
        return
    
    await create_vote(game.chat_id, callback.from_user.id, target_telegram_id, game.day)
    
    voter_name = callback.from_user.full_name or callback.from_user.first_name
    target_name = await get_name_by_id(target_telegram_id)
    
    await callback.answer(f"Вы проголосовали за {target_name}", show_alert=False)
    await callback.bot.send_message(
        game.chat_id,
        f"<b>{voter_name}</b> проголосовал за <b>{target_name}</b>"
    )

@router.callback_query(F.data == "skip_vote")
async def skip_vote(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Вы не можете пропустить голосование!", show_alert=True)
        return
    
    game = await get_game(callback.message.chat.id)
    if not game or not game.started:
        await callback.answer("Игра не началась!", show_alert=True)
        return
    
    if not user.in_game or not user.is_alive:
        await callback.answer("Вы не можете пропустить голосование!", show_alert=True)
        return
    
    fresh_game = await get_game(callback.message.chat.id)
    
    if not fresh_game or fresh_game.current_phase != "voting":
        await callback.answer("Голосование не началось!", show_alert=True)
        return
    
    game = fresh_game
    
    from database import has_voted
    if await has_voted(game.chat_id, callback.from_user.id, game.day):
        await callback.answer("Вы уже проголосовали!", show_alert=True)
        return
    
    await create_vote(game.chat_id, callback.from_user.id, 0, game.day)
    
    await callback.answer("Вы пропустили голосование", show_alert=False)
    await callback.bot.send_message(
        game.chat_id,
        f"❌ Игрок <a href='tg://user?id={callback.from_user.id}'>{callback.from_user.first_name}</a> отказался от голосования"
    )

@router.callback_query(F.data.startswith("confirm_lynch_"))
async def confirm_lynch(callback: CallbackQuery):
    target_telegram_id = int(callback.data.split("_")[-1])
    
    user = await get_user(callback.from_user.id)
    if not user or not user.in_game or not user.is_alive:
        await callback.answer("Вы не можете подтверждать!", show_alert=True)
        return
    
    game = await get_game(callback.message.chat.id)
    if not game or game.voting_target_id != target_telegram_id or game.voting_confirmed:
        await callback.answer("Некорректное действие!", show_alert=True)
        return
    
    await create_lynch_confirmation(game.chat_id, callback.from_user.id, target_telegram_id, True)
    
    confirmations = await get_lynch_confirmations(game.chat_id, target_telegram_id)
    likes = [c for c in confirmations if c.approved]
    dislikes = [c for c in confirmations if not c.approved]
    
    users = await get_users(game.chat_id)
    alive_users = [u for u in users if u.is_alive]
    
    try:
        await callback.message.edit_reply_markup(
            reply_markup=InlineKeyboardBuilder()
            .add(InlineKeyboardButton(text=f"{len(likes)} 👍", callback_data=f"confirm_lynch_{target_telegram_id}"))
            .add(InlineKeyboardButton(text=f"{len(dislikes)} 👎", callback_data=f"reject_lynch_{target_telegram_id}"))
            .as_markup()
        )
    except:
        pass
    
    await callback.answer(f"✅ Вы подтвердили линчевание (👍 {len(likes)} / 👎 {len(dislikes)})", show_alert=False)

@router.callback_query(F.data.startswith("kamikaze_choose_"))
async def kamikaze_choose_target(callback: CallbackQuery):
    parts = callback.data.split("_")
    if len(parts) >= 4:
        target_id = int(parts[-2])
        kamikaze_id = int(parts[-1])
        
        if callback.from_user.id != kamikaze_id:
            await callback.answer("Это не ваш выбор!", show_alert=True)
            return
        
        user = await get_user(callback.from_user.id)
        if not user or not user.game:
            await callback.answer("Ошибка!", show_alert=True)
            return
        
        game = user.game
        target_user = await get_user(target_id)
        kamikaze_user = await get_user(kamikaze_id)
        
        if not target_user or not target_user.is_alive:
            await callback.answer("Этот игрок уже мертв!", show_alert=True)
            return
        
        if not kamikaze_user or not kamikaze_user.is_alive:
            await callback.answer("Вы уже мертвы!", show_alert=True)
            return
        
        target_name = await get_name_by_id(target_id)
        kamikaze_name = await get_name_by_id(kamikaze_id)
        target_role_name = get_role_full_name(target_user.role) if target_user.role else "Неизвестная роль"
        kamikaze_role_name = get_role_full_name(kamikaze_user.role) if kamikaze_user.role else "Неизвестная роль"
        
        target_user.is_alive = False
        await update_user(target_id, is_alive=False, last_message_sent=False)
        await reset_user_game_state(target_id)
        await remove_user_from_game(game.chat_id, target_id)
        
        kamikaze_user.is_alive = False
        await update_user(kamikaze_id, is_alive=False, last_message_sent=False)
        await reset_user_game_state(kamikaze_id)
        await remove_user_from_game(game.chat_id, kamikaze_id)
        
        await callback.bot.send_message(
            game.chat_id,
            f"💥 <b>{kamikaze_name}</b> ({kamikaze_role_name}) забрал с собой <b>{target_name}</b> ({target_role_name})!"
        )
        
        await callback.message.edit_text("✅ Вы выбрали цель!")
        
        from utils.update import check_win_conditions, switch_phase
        if not await check_win_conditions(game.chat_id):
            await switch_phase(game.chat_id)

@router.callback_query(F.data.startswith("reject_lynch_"))
async def reject_lynch(callback: CallbackQuery):
    target_telegram_id = int(callback.data.split("_")[-1])
    
    user = await get_user(callback.from_user.id)
    if not user or not user.in_game or not user.is_alive:
        await callback.answer("Вы не можете подтверждать!", show_alert=True)
        return
    
    game = await get_game(callback.message.chat.id)
    if not game or game.voting_target_id != target_telegram_id or game.voting_confirmed:
        await callback.answer("Некорректное действие!", show_alert=True)
        return
    
    await create_lynch_confirmation(game.chat_id, callback.from_user.id, target_telegram_id, False)
    
    confirmations = await get_lynch_confirmations(game.chat_id, target_telegram_id)
    likes = [c for c in confirmations if c.approved]
    dislikes = [c for c in confirmations if not c.approved]
    
    users = await get_users(game.chat_id)
    alive_users = [u for u in users if u.is_alive]
    
    try:
        await callback.message.edit_reply_markup(
            reply_markup=InlineKeyboardBuilder()
            .add(InlineKeyboardButton(text=f"{len(likes)} 👍", callback_data=f"confirm_lynch_{target_telegram_id}"))
            .add(InlineKeyboardButton(text=f"{len(dislikes)} 👎", callback_data=f"reject_lynch_{target_telegram_id}"))
            .as_markup()
        )
    except:
        pass
    
    await callback.answer(f"❌ Вы отклонили линчевание (👍 {len(likes)} / 👎 {len(dislikes)})", show_alert=False)

@router.message(MafiaChatFilter())
async def handle_mafia_message(message: Message):
    user = await get_user(message.from_user.id)
    game = await get_game(user.game_id)
    
    sender_name = "Дон" if user.role == "don" else "Мафия"
    sender_display_name = user.first_name
    
    message_text = message.text or message.caption or ""
    formatted_message = f"<b>{sender_name} {sender_display_name}:</b>\n{message_text}"
    
    from bot import bot
    from utils.func import get_role_type
    
    for mafia_user in game.users:
        if mafia_user.is_alive and mafia_user.role:
            role_type = get_role_type(mafia_user.role)
            if role_type == "mafia" or mafia_user.role == "don":
                await bot.send_message(
                    mafia_user.telegram_id,
                    formatted_message
                )


@router.message(F.text & ~F.command)
async def handle_text_message(message: Message):
    user = await get_user(message.from_user.id)
    if not user or not user.in_game:
        return
    
    game = await get_game(message.chat.id)
    if not game or not game.started:
        return
    
    if game.current_phase == "day" and user.lover_affected:
        await message.delete()
        await message.answer("💃🏼 К вам пришла любовница, вы не можете писать днем!")
        return