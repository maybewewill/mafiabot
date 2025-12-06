from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from database.models import Base, Game, User, Vote, LynchConfirmation

DATABASE_URL = "sqlite:///mafia_bot.db"
engine = create_engine(DATABASE_URL, echo=True)

Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()

def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

async def create_game(chat_id: int, start_time: int, message_id: int):
    game = Game(chat_id=chat_id, start_time=start_time, message_id=message_id)
    session.add(game)
    session.commit()
    return game

async def get_game(chat_id: int):
    result = session.execute(select(Game).where(Game.chat_id == chat_id))
    return result.scalar_one_or_none()

async def delete_game(chat_id: int):
    game = await get_game(chat_id)
    if game:
        session.delete(game)
        session.commit()

async def update_game(chat_id: int, **kwargs):
    game = await get_game(chat_id)
    if game:
        for key, value in kwargs.items():
            setattr(game, key, value)
        session.commit()
        session.expire(game)

async def add_user_to_game(chat_id: int, user_id: int):
    game = await get_game(chat_id)
    if game:
        user = await get_user(user_id)
        if user:
            game.users.append(user)
            session.commit()

async def reset_user_game_state(telegram_id: int):
    user = await get_user(telegram_id)
    if user:
        user.game_id = None
        user.in_game = False
        user.role = None
        user.visitor_id = None
        user.killer_id = None
        user.mafia_choose = None
        user.doctor_rescued = False
        user.lover_affected = False
        user.advocate_saved = False
        user.homeless_visit = False
        user.kamikaze_target_id = None
        session.commit()

async def remove_user_from_game(chat_id: int, telegram_id: int):
    user = await get_user(telegram_id)
    if user:
        user.game_id = None
        user.in_game = False
        user.role = None
        user.visitor_id = None
        user.killer_id = None
        user.mafia_choose = None
        user.doctor_rescued = False
        user.lover_affected = False
        user.advocate_saved = False
        user.homeless_visit = False
        user.kamikaze_target_id = None
        session.commit()

async def get_all_games():
    result = session.execute(select(Game))
    return result.scalars().all()

async def get_users(chat_id: int):
    game = await get_game(chat_id)
    if game:
        return game.users
    return None

async def create_user_if_not_exists(**kwargs):
    user = await get_user(kwargs["telegram_id"])
    if not user:
        user = User(**kwargs)
        session.add(user)
        session.commit()
    else:
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        session.commit()
    return user

async def inc_mafia_choose(chat_id: int, telegram_id: int, k: int = 1):
    user = await get_user(telegram_id)
    if user:
        if user.mafia_choose is None:
            user.mafia_choose = 0
        user.mafia_choose += k
        session.commit()

async def get_name_by_id(telegram_id: int):
    user = await get_user(telegram_id)
    if user:
        return user.first_name
    return None

async def get_user(telegram_id: int):
    result = session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()

async def delete_user(telegram_id: int):
    user = await get_user(telegram_id)
    if user:
        session.delete(user)
        session.commit()

async def update_user(telegram_id: int, **kwargs):
    user = await get_user(telegram_id)
    if user:
        for key, value in kwargs.items():
            setattr(user, key, value)
        session.commit()

async def is_in_game(telegram_id: int):
    user = await get_user(telegram_id)
    if user:
        return user.in_game
    return None

async def create_vote(chat_id: int, voter_telegram_id: int, target_telegram_id: int, day: int):
    game = await get_game(chat_id)
    if not game:
        return None

    existing_vote = session.execute(
        select(Vote).where(
            Vote.game_id == game.id,
            Vote.voter_telegram_id == voter_telegram_id,
            Vote.day == day
        )
    ).scalar_one_or_none()
    
    if existing_vote:
        existing_vote.target_telegram_id = target_telegram_id
        session.commit()
        return existing_vote
    
    vote = Vote(
        game_id=game.id,
        voter_telegram_id=voter_telegram_id,
        target_telegram_id=target_telegram_id,
        day=day
    )
    session.add(vote)
    session.commit()
    return vote

async def get_votes_for_day(chat_id: int, day: int):
    game = await get_game(chat_id)
    if not game:
        return []
    result = session.execute(
        select(Vote).where(
            Vote.game_id == game.id,
            Vote.day == day
        )
    )
    return result.scalars().all()

async def get_vote_count(chat_id: int, target_telegram_id: int, day: int):
    game = await get_game(chat_id)
    if not game:
        return 0
    result = session.execute(
        select(Vote).where(
            Vote.game_id == game.id,
            Vote.target_telegram_id == target_telegram_id,
            Vote.day == day
        )
    )
    return len(result.scalars().all())

async def clear_votes_for_day(chat_id: int, day: int):
    votes = await get_votes_for_day(chat_id, day)
    for vote in votes:
        session.delete(vote)
    session.commit()

async def has_voted(chat_id: int, voter_telegram_id: int, day: int):
    game = await get_game(chat_id)
    if not game:
        return False
    result = session.execute(
        select(Vote).where(
            Vote.game_id == game.id,
            Vote.voter_telegram_id == voter_telegram_id,
            Vote.day == day
        )
    )
    return result.scalar_one_or_none() is not None

async def create_lynch_confirmation(chat_id: int, voter_telegram_id: int, target_telegram_id: int, approved: bool):
    game = await get_game(chat_id)
    if not game:
        return None

    existing = session.execute(
        select(LynchConfirmation).where(
            LynchConfirmation.game_id == game.id,
            LynchConfirmation.voter_telegram_id == voter_telegram_id,
            LynchConfirmation.target_telegram_id == target_telegram_id
        )
    ).scalar_one_or_none()
    
    if existing:
        existing.approved = approved
        session.commit()
        return existing
    
    confirmation = LynchConfirmation(
        game_id=game.id,
        voter_telegram_id=voter_telegram_id,
        target_telegram_id=target_telegram_id,
        approved=approved
    )
    session.add(confirmation)
    session.commit()
    return confirmation

async def get_lynch_confirmations(chat_id: int, target_telegram_id: int):
    game = await get_game(chat_id)
    if not game:
        return []
    result = session.execute(
        select(LynchConfirmation).where(
            LynchConfirmation.game_id == game.id,
            LynchConfirmation.target_telegram_id == target_telegram_id
        )
    )
    return result.scalars().all()

async def clear_lynch_confirmations(chat_id: int, target_telegram_id: int):
    confirmations = await get_lynch_confirmations(chat_id, target_telegram_id)
    for conf in confirmations:
        session.delete(conf)
    session.commit()
