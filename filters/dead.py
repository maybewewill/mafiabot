from aiogram.filters import BaseFilter
from aiogram.types import Message
from database import get_user, get_game
from utils.func import get_role_type

class DeadLastMessageFilter(BaseFilter):
    """Фильтр для проверки, что сообщение от мертвого игрока, который еще не отправил последнее сообщение"""
    
    async def __call__(self, message: Message) -> bool:
        if message.chat.type != "private":
            return False
        
        user = await get_user(message.from_user.id)
        if not user or not user.in_game:
            return False

        if user.is_alive:
            return False

        if user.last_message_sent:
            return False
        
        if not user.game_id:
            return False
        
        game = await get_game(user.game_id)
        if not game or not game.started:
            return False

        message_text = message.text or message.caption or ""
        if not message_text:
            return False
        
        return True

