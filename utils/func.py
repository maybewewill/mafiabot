import random
from models.roles import roles as ALL_ROLES

ROLES_MAP = {r.name: r for r in ALL_ROLES}
ROLES_BY_FULL_NAME = {}
for role in ALL_ROLES:
    full_name = getattr(role, 'full_name', None)
    if full_name:
        ROLES_BY_FULL_NAME[full_name] = role

def get_role(name: str):
    if name in ROLES_MAP:
        return ROLES_MAP[name]
    if name in ROLES_BY_FULL_NAME:
        return ROLES_BY_FULL_NAME[name]
    return None

def get_scenario(count: int) -> list:
    if count < 4:
         return [get_role("mafia")] + [get_role("citizen")] * (count - 1)

    deck = []
    
    mafia_count = max(1, int(count // 3.5))
    
    if mafia_count >= 2:
        deck.append(get_role("don"))
        deck.extend([get_role("mafia")] * (mafia_count - 1))
    else:
        deck.extend([get_role("mafia")] * mafia_count)

    if count >= 5:
        deck.append(get_role("sheriff"))
        deck.append(get_role("doctor"))
        
    max_specials = 0
    
    if count >= 6: 
        max_specials = 1
    if count >= 8: 
        max_specials = 2
    if count >= 10: 
        max_specials = 3
    if count >= 12: 
        max_specials = 4
    
    excluded_names = {"mafia", "don", "sheriff", "doctor", "citizen"}
    special_pool = [r for r in ALL_ROLES if r.name not in excluded_names]
    random.shuffle(special_pool)
    
    roles_assigned = len(deck)
    slots_left = count - roles_assigned
    
    specials_to_add = min(slots_left, max_specials, len(special_pool))
    deck.extend(special_pool[:specials_to_add])
    
    roles_assigned = len(deck)
    needed_citizens = count - roles_assigned
    
    if needed_citizens > 0:
        deck.extend([get_role("citizen")] * needed_citizens)
        
    return deck



def shuffle_roles(users: list) -> dict:
    player_count = len(users)
    
    game_roles = get_scenario(player_count)
    
    random.shuffle(game_roles)
    
    if len(game_roles) != player_count:
        diff = player_count - len(game_roles)
        if diff > 0:
            game_roles.extend([get_role("citizen")] * diff)
        else:
            game_roles = game_roles[:player_count]

    return {user: role for user, role in zip(users, game_roles)}

def get_role_by_name(role_name: str):
    return ROLES_MAP.get(role_name)

def get_role_type(role_name: str) -> str:
    role = get_role_by_name(role_name)
    return role.type if role else None

def get_role_full_name(role_name: str) -> str:
    role = get_role_by_name(role_name)
    return role.full_name if role else role_name

async def get_role_by_id(user_id: int) -> str:
    from database import get_user
    user = await get_user(user_id)
    if not user or not user.role:
        return "Неизвестная роль"
    return get_role_full_name(user.role)