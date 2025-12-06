from datetime import datetime
import time

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from bot import bot
from database import *
from utils.func import shuffle_roles, get_role_type, get_role_full_name
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

scheduler = AsyncIOScheduler()

NIGHT_TIME = 45
NIGHT_GIF = "CgACAgIAAxkBAANNaTQfHXgjU7-Pfyd6XKnhq2qlZAsAAqiBAAKvN1lIC_BggxWdDYM2BA"

DAY_TIME = 60
DAY_GIF = "CgACAgIAAxkBAANPaTQfPM6mox--ZDMr4spSUBPs0LsAAq2BAAKvN1lIX1fq0Ms7i3c2BA"

VOTE_TIME = 45
LYNCH_TIME = 40

async def check_win_conditions(chat_id: int) -> bool:
    game = await get_game(chat_id)
    if not game or not game.started:
        return False
    
    users = await get_users(chat_id)
    alive_users = [u for u in users if u.is_alive]
    
    if len(alive_users) == 0:
        return False
    
    mafia_count = 0
    peaceful_count = 0
    
    for user in alive_users:
        if not user.role:
            continue
        role_type = get_role_type(user.role)
        if role_type == "mafia" or user.role == "don":
            mafia_count += 1
        else:
            peaceful_count += 1
    
    winner = None
    if mafia_count == 0:
        winner = "peaceful"
    elif mafia_count >= peaceful_count:
        winner = "mafia"
    
    if winner:
        await end_game(chat_id, winner, users)
        return True
    
    return False

async def end_game(chat_id: int, winner: str, users: list):
    from database import get_name_by_id
    
    game = await get_game(chat_id)
    if game:
        game_users = await get_users(chat_id)
        if game_users:
            users = game_users
    
    await update_game(chat_id, started=False, current_phase="ended")
    
    try:
        scheduler.remove_job(f"phase_{chat_id}")
    except:
        pass
    try:
        scheduler.remove_job(f"voting_start_{chat_id}")
    except:
        pass
    try:
        scheduler.remove_job(f"auto_lynch_{chat_id}")
    except:
        pass
    
    winner_text = "🤵🏻 <b>Мафия победила!</b>" if winner == "mafia" else "👨🏼 <b>Мирные жители победили!</b>"
    
    text = f" <b>Игра завершена!</b>\n\n{winner_text}\n\n"
    
    alive_players = []
    dead_players = []
    
    for user in users:
        role_full_name = get_role_full_name(user.role) if user.role else "Неизвестная роль"
        player_info = f"<a href='tg://user?id={user.telegram_id}'>{user.first_name}</a> - {role_full_name}"
        if user.is_alive:
            alive_players.append(player_info)
        else:
            dead_players.append(player_info)
    
    if alive_players:
        text += "✅ <b>Остались живы:</b>\n"
        for player in alive_players:
            text += f"{player}\n"
        text += "\n"
    
    if dead_players:
        text += "💀 <b>Мертвы:</b>\n"
        for player in dead_players:
            text += f"{player}\n"
        text += "\n"
    
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(
            text="🔄 Сыграть еще",
            callback_data="new_game"
        )
    )
    
    await bot.send_message(chat_id, text, reply_markup=builder.as_markup())

async def check_games():
    games = await get_all_games()
    for game in games:
        if not game.started and game.start_time is not None:
            if game.start_time < time.time():
                game.started = True
                await update_game(game.chat_id, started=True)
                await bot.delete_message(game.chat_id, game.message_id)
                if len(game.users) < 4:
                    await bot.send_message(
                        game.chat_id,
                        "Игра не может начаться, так как игроков меньше 3."
                    )
                    continue
                try:
                    await bot.send_message(
                        game.chat_id,
                        "Игра начинается!\n\nВ течение нескольких секунд бот пришлёт вам личное сообщение с ролью и её описанием.",
                        reply_markup=InlineKeyboardBuilder().add(
                            InlineKeyboardButton(
                                text="Посмотреть роль",
                                url="https://t.me/mafiamingbot",
                            )
                        ).as_markup(),
                    )
                except:
                    pass
                users = await get_users(game.chat_id)
                for user in users:
                    await update_user(user.telegram_id, is_alive=True, in_game=True)
                roles = shuffle_roles(users)
                for user, role in roles.items():
                    await update_user(user.telegram_id, role=role.name)
                    await bot.send_message(
                        user.telegram_id,
                        f"{role.description}",
                    )
                
                await bot.send_message(
                    game.chat_id,
                    "⏳ У вас есть 30 секунд, чтобы изучить свои роли. Первая ночь начнется через 30 секунд..."
                )
                
                first_night_time = int(time.time()) + 30
                await update_game(game.chat_id, current_phase="day", day=0, night=0, next_phase_time=first_night_time)
                scheduler.add_job(
                    switch_phase,
                    'date',
                    run_date=datetime.fromtimestamp(first_night_time),
                    kwargs={"chat_id": game.chat_id},
                    id=f"phase_{game.chat_id}",
                    replace_existing=True
                )

async def switch_phase(chat_id: int):
    game = await get_game(chat_id)
    if not game or not game.started:
        return

    users = await get_users(chat_id)
    
    if game.current_phase == "voting":
        await process_voting_results(chat_id)
        return
    
    elif game.current_phase == "day":
        new_phase = "night"
        game.night += 1
        duration = NIGHT_TIME
        
        text = f"🌃 <b>Ночь {game.night} наступила!</b>\nГород засыпает, просыпается мафия..."
        await bot.send_animation(chat_id, NIGHT_GIF, caption=text)
        
        for user in users:
            if not user.is_alive or not user.role:
                continue
            
            if user.role == "mafia":
                builder = InlineKeyboardBuilder()
                for target_user in users:
                    if target_user.is_alive and get_role_type(target_user.role) != "mafia":
                        builder.add(
                            InlineKeyboardButton(
                                text=target_user.first_name,
                                callback_data=f"mafia_choose_{target_user.telegram_id}",
                            )
                        )
                builder.adjust(1)
                await bot.send_message(
                    user.telegram_id,
                    "Пришло время выбирать!\nВыберите игрока, которого хотите убить",
                    reply_markup=builder.as_markup(),
                )
            elif user.role == "don":
                builder = InlineKeyboardBuilder()
                for target_user in users:
                    if target_user.is_alive and get_role_type(target_user.role) != "mafia":
                        builder.add(
                            InlineKeyboardButton(
                                text=target_user.first_name,
                                callback_data=f"don_choose_{target_user.telegram_id}",
                            )
                        )
                builder.adjust(1)
                await bot.send_message(
                    user.telegram_id,
                    "Пришло время выбирать!\nВыберите игрока, которого хотите убить",
                    reply_markup=builder.as_markup(),
                )
            elif user.role == "sheriff":
                builder = InlineKeyboardBuilder()
                builder.add(
                    InlineKeyboardButton(
                        text="📄 Проверить",
                        callback_data="sheriff_action_check",
                    )
                )
                builder.add(
                    InlineKeyboardButton(
                        text="🔫 Убить",
                        callback_data="sheriff_action_kill",
                    )
                )
                await bot.send_message(
                    user.telegram_id,
                    "Пришло время выбирать!\nВыберите действие:",
                    reply_markup=builder.as_markup(),
                )
            elif user.role == "doctor":
                builder = InlineKeyboardBuilder()
                for target_user in users:
                    if target_user.is_alive:
                        builder.add(
                            InlineKeyboardButton(
                                text=target_user.first_name,
                                callback_data=f"doctor_choose_{target_user.telegram_id}",
                            )
                        )
                builder.adjust(1)
                await bot.send_message(
                    user.telegram_id,
                    "Пришло время выбирать!\nВыберите игрока, которого хотите вылечить",
                    reply_markup=builder.as_markup(),
                )
            elif user.role == "murderer":
                builder = InlineKeyboardBuilder()
                for target_user in users:
                    if target_user.is_alive and target_user.telegram_id != user.telegram_id:
                        builder.add(
                            InlineKeyboardButton(
                                text=target_user.first_name,
                                callback_data=f"murderer_choose_{target_user.telegram_id}",
                            )
                        )
                builder.adjust(1)
                await bot.send_message(
                    user.telegram_id,
                    "Пришло время выбирать!\nВыберите игрока, которого хотите убить",
                    reply_markup=builder.as_markup(),
                )
            elif user.role == "lover":
                builder = InlineKeyboardBuilder()
                for target_user in users:
                    if target_user.is_alive and target_user.telegram_id != user.telegram_id:
                        builder.add(
                            InlineKeyboardButton(
                                text=target_user.first_name,
                                callback_data=f"lover_choose_{target_user.telegram_id}",
                            )
                        )
                builder.adjust(1)
                await bot.send_message(
                    user.telegram_id,
                    "<b>Пришло время выбирать!</b>\nВыберите игрока, которого хотите заглушить",
                    reply_markup=builder.as_markup(),
                )
            elif user.role == "advocate":
                builder = InlineKeyboardBuilder()
                for target_user in users:
                    if target_user.is_alive:
                        builder.add(
                            InlineKeyboardButton(
                                text=target_user.first_name,
                                callback_data=f"advocate_choose_{target_user.telegram_id}",
                            )
                        )
                builder.adjust(1)
                await bot.send_message(
                    user.telegram_id,
                    "Пришло время выбирать!\nВыберите игрока, которого хотите защитить",
                    reply_markup=builder.as_markup(),
                )
            elif user.role == "homeless":
                builder = InlineKeyboardBuilder()
                for target_user in users:
                    if target_user.is_alive and target_user.telegram_id != user.telegram_id:
                        builder.add(
                            InlineKeyboardButton(
                                text=target_user.first_name,
                                callback_data=f"homeless_choose_{target_user.telegram_id}",
                            )
                        )
                builder.adjust(1)
                await bot.send_message(
                    user.telegram_id,
                    "Пришло время выбирать!\nВыберите игрока, к которому ты хочешь зайти за бутылкой",
                    reply_markup=builder.as_markup(),
                )
        
        next_time = int(time.time()) + duration
        await update_game(
            chat_id, 
            current_phase=new_phase, 
            day=game.day, 
            night=game.night,
            next_phase_time=next_time
        )

        scheduler.add_job(
            switch_phase, 
            'date', 
            run_date=datetime.fromtimestamp(next_time), 
            kwargs={"chat_id": chat_id},
            id=f"phase_{chat_id}",
            replace_existing=True
        )
        return
    
    else:
        new_phase = "day"
        game.day += 1
        duration = DAY_TIME
        
        

        dead_don = None
        dead_sheriff = None
        someone_died = False
        
        for user in users:
            if user.visitor_id:
                if user.killer_id:
                    killer = await get_user(user.killer_id)
                    if killer.lover_affected:
                        continue
                    
                    someone_died = True
                    user_role_name = get_role_full_name(user.role) if user.role else "Неизвестная роль"
                    killer_role_name = get_role_full_name(killer.role) if killer and killer.role else "Неизвестная роль"
                    await bot.send_message(
                        game.chat_id,
                        f"Сегодня был жестоко убит <b>{user_role_name}</b> <a href='tg://user?id={user.telegram_id}'>{user.first_name}</a>\nГоворят, у него в гостях был <b>{killer_role_name}</b>"
                    )
                    if user.doctor_rescued:
                        await bot.send_message(
                            user.telegram_id,
                            "Тебя хотели убить, но доктор тебя спас!"
                        )
                        continue
                    
                    if user.role == "don":
                        dead_don = user
                    elif user.role == "sheriff":
                        dead_sheriff = user
                    
                    user.is_alive = False
                    await reset_user_game_state(user.telegram_id)
                    await update_user(user.telegram_id, last_message_sent=False)
                    await remove_user_from_game(chat_id, user.telegram_id)
        if not someone_died:
            await bot.send_message(
                chat_id,
                "🌙 <b>Прошла спокойная ночь!</b>\nНикто не пострадал."
            )

        if await check_win_conditions(chat_id):
            return

        if dead_don:
            mafia_users = [u for u in users if u.is_alive and u.role and get_role_type(u.role) == "mafia" and u.role != "don"]
            if mafia_users:
                import random
                new_don = random.choice(mafia_users)
                await update_user(new_don.telegram_id, role="don")
                await bot.send_message(
                    chat_id,
                    f"🤵🏻 <b>{new_don.first_name}</b> стал новым Доном!"
                )
        
        if dead_sheriff:
            sergeant = next((u for u in users if u.is_alive and u.role == "sergeant"), None)
            if sergeant:
                await update_user(sergeant.telegram_id, role="sheriff")
                await bot.send_message(
                    chat_id,
                    f"🕵️ <b>{sergeant.first_name}</b> стал новым Шерифом!"
                )
        text = f"☀️ <b>День {game.day} настал!</b>\nВсе просыпаются. Кто не пережил эту ночь?"
        await bot.send_animation(chat_id, DAY_GIF, caption=text)
        
        text = "<b>Живые игроки:</b>\n\n"
        _roles = {}
        for index, user in enumerate(users):
            if user.is_alive and user.role:
                role_full_name = get_role_full_name(user.role)
                if role_full_name not in _roles:
                    _roles[role_full_name] = 1
                else:
                    _roles[role_full_name] += 1
                text += f"{index + 1}. <a href='tg://user?id={user.telegram_id}'>{user.first_name}</a>\n"
        
        text += "\nКто-то из них: "
        for role_name, count in _roles.items():
            text += f"{role_name} - {count}, "
        text = text.rstrip(", ")
        text += "\nВсего игроков осталось: " + str(len([u for u in users if u.is_alive]))
        text += f"\n\nНачинайте обсуждение! Голосование начнется через {DAY_TIME} секунд и продлится {VOTE_TIME} секунд."
        await bot.send_message(game.chat_id, text)
        
        voting_start_time = int(time.time()) + DAY_TIME
        scheduler.add_job(
            start_voting,
            'date',
            run_date=datetime.fromtimestamp(voting_start_time),
            kwargs={"chat_id": chat_id},
            id=f"voting_start_{chat_id}",
            replace_existing=True
        )
        
        next_time = int(time.time()) + duration
        await update_game(
            chat_id, 
            current_phase=new_phase, 
            day=game.day, 
            night=game.night,
            next_phase_time=next_time
        )
        return

async def start_voting(chat_id: int):
    game = await get_game(chat_id)
    if not game or not game.started:
        return
    
    users = await get_users(chat_id)
    alive_users = [u for u in users if u.is_alive]
    
    if len(alive_users) < 2:
        return
    
    await clear_votes_for_day(chat_id, game.day)
    

    
    await update_game(chat_id, current_phase="voting", voting_target_id=None, voting_confirmed=False)
    
    builder = InlineKeyboardBuilder()
    for user in alive_users:
        builder.add(
            InlineKeyboardButton(
                text=user.first_name,
                callback_data=f"vote_for_{user.telegram_id}",
            )
        )
    
    builder.add(
        InlineKeyboardButton(
            text="Пропустить",
            callback_data="skip_vote",
        )
    )

    if len(alive_users) > 10:
        builder.adjust(2)
    else:
        builder.adjust(1)
    
    await bot.send_message(
        chat_id,
        f"🗳️ <b>Голосование началось!</b>\n\nВыберите игрока, за которого вы хотите проголосовать:\n\n⏱️ Голосование продлится {VOTE_TIME} секунд.",
        reply_markup=builder.as_markup()
    )
    
    voting_end_time = int(time.time()) + VOTE_TIME
    scheduler.add_job(
        switch_phase,
        'date',
        run_date=datetime.fromtimestamp(voting_end_time),
        kwargs={"chat_id": chat_id},
        id=f"phase_{chat_id}",
        replace_existing=True
    )
    await update_game(chat_id, next_phase_time=voting_end_time)

async def auto_lynch(chat_id: int, target_id: int):
    game = await get_game(chat_id)
    if not game or not game.started or game.voting_confirmed:
        return
    
    if game.voting_target_id != target_id:
        return
    
    confirmations = await get_lynch_confirmations(chat_id, target_id)
    likes = [c for c in confirmations if c.approved]
    dislikes = [c for c in confirmations if not c.approved]
    
    if len(likes) > len(dislikes):
        target_name = await get_name_by_id(target_id)
        target_user = await get_user(target_id)
        if target_user and target_user.is_alive:
            role_full_name = get_role_full_name(target_user.role) if target_user.role else "Неизвестная роль"
            target_user.is_alive = False
            await update_user(target_id, is_alive=False, last_message_sent=False)
            await reset_user_game_state(target_id)
            await remove_user_from_game(chat_id, target_id)
            await update_game(chat_id, voting_confirmed=True)
            
            await bot.send_message(
                chat_id,
                f"💀 <b>{target_name}</b> был <b>{role_full_name}</b>"
            )
            
            await clear_votes_for_day(chat_id, game.day)
            await clear_lynch_confirmations(chat_id, target_id)
            await update_game(chat_id, current_phase="day", voting_target_id=None, voting_confirmed=False)
            
            if not await check_win_conditions(chat_id):
                await switch_phase(chat_id)
    else:
        target_name = await get_name_by_id(target_id)
        await bot.send_message(
            chat_id,
            f"❌ Линчевание <b>{target_name}</b> отклонено. Игрок остается жив."
        )
        
        await clear_votes_for_day(chat_id, game.day)
        await clear_lynch_confirmations(chat_id, target_id)
        await update_game(chat_id, current_phase="day", voting_target_id=None, voting_confirmed=False)
        await switch_phase(chat_id)

async def process_voting_results(chat_id: int):
    game = await get_game(chat_id)
    if not game or not game.started:
        return
    
    users = await get_users(chat_id)
    alive_users = [u for u in users if u.is_alive]
    
    votes = await get_votes_for_day(chat_id, game.day)
    
    valid_votes = [v for v in votes if v.target_telegram_id != 0]
    
    vote_counts = {}
    for vote in valid_votes:
        target_id = vote.target_telegram_id
        if target_id not in vote_counts:
            vote_counts[target_id] = 0
        vote_counts[target_id] += 1
    
    if not vote_counts:
        await bot.send_message(
            chat_id, 
            "❌ <b>Все игроки пропустили голосование.</b>\n\nПодтверждение на линчевание не будет. Голосование пропущено."
        )
        await update_game(chat_id, current_phase="day")
        await switch_phase(chat_id)
        return
    
    max_votes = max(vote_counts.values())
    candidates = [target_id for target_id, count in vote_counts.items() if count == max_votes]
    
    if len(candidates) > 1:
        candidate_names = [await get_name_by_id(tid) for tid in candidates]
        await bot.send_message(
            chat_id,
            f"⏭️ <b>Голосование пропущено</b>\n\nУ нескольких игроков одинаковое количество голосов ({max_votes}): {', '.join(candidate_names)}\n\nПодтверждение на линчевание не будет."
        )
        await update_game(chat_id, current_phase="day")
        await switch_phase(chat_id)
        return
    
    target_id = candidates[0]
    target_user = await get_user(target_id)
    target_name = await get_name_by_id(target_id)

    await clear_lynch_confirmations(chat_id, target_id)
    await update_game(chat_id, voting_target_id=target_id, voting_confirmed=False)

    confirmations = await get_lynch_confirmations(chat_id, target_id)
    likes_count = len([c for c in confirmations if c.approved])
    dislikes_count = len([c for c in confirmations if not c.approved])

    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text=f"{likes_count} 👍", callback_data=f"confirm_lynch_{target_id}")
    )
    builder.add(
        InlineKeyboardButton(text=f"{dislikes_count} 👎", callback_data=f"reject_lynch_{target_id}")
    )
    
    lynch_message = await bot.send_message(
        chat_id,
        f"❓ <b>Вы точно хотите линчевать {target_name}?</b>\n\nПроголосовало за него: {max_votes}\n⏱️ У вас есть {LYNCH_TIME} секунд для решения.",
        reply_markup=builder.as_markup()
    )
    
    from datetime import datetime
    lynch_end_time = int(time.time()) + LYNCH_TIME
    scheduler.add_job(
        auto_lynch,
        'date',
        run_date=datetime.fromtimestamp(lynch_end_time),
        kwargs={"chat_id": chat_id, "target_id": target_id},
        id=f"auto_lynch_{chat_id}",
        replace_existing=True
    )

scheduler.add_job(check_games, "interval", seconds=1)