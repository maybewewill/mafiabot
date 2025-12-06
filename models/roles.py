from pydantic import BaseModel
from typing import Callable, Awaitable
from typing import Literal
from enum import Enum

class Role(BaseModel):
    name: str
    full_name: str
    description: str
    type: Literal['mafia', 'citizen', 'neutral']
    task: Callable[[], Awaitable[None]]

roles = [
    Role(
        name="citizen",
        full_name="👨🏼 Мирный житель", 
        description="Ты - 👨🏼 Мирный житель.\nТвоя цель - выжить до конца игры и на городском собрании убить всех мафиози", 
        type='citizen', 
        task=lambda: None
    ),
    Role(
        name="mafia", 
        full_name="🤵🏼 Мафия", 
        description="Ты - 🤵🏼 Мафия.\nТвоя задача подчиняться Дону и убивать всех мирных. После смерти Дона, ты можешь стать Доном", 
        type='mafia', 
        task=lambda: None
    ),
    Role(
        name="don", 
        full_name="🤵🏻 Дон", 
        description="Ты - 🤵🏻 Дон.\nТебе решать кто не проснется после ночи...", 
        type='mafia', 
        task=lambda: None
    ),
    Role(
        name="sheriff", 
        full_name="🕵️ Шериф", 
        description="Ты - 🕵️ Шериф.\nТвоя задача определить мафию и убить их. Главный городской защитник.", 
        type='citizen', 
        task=lambda: None
    ),
    Role(
        name="sergeant", 
        full_name="👮🏽 Сержант", 
        description="Ты - 👮🏽 Сержант.\nПомощник Шерифа. Он будет информировать тебя о своих действиях. Если Шериф погибнет - ты становишься Шерифом.", 
        type='citizen', 
        task=lambda: None
    ),
    Role(
        name="doctor", 
        full_name="👩‍⚕️ Доктор", 
        description="Ты - 👩‍⚕️ Доктор.\nТвоя задача лечить людей. Тебе решать кто выживет этой ночью.", 
        type='citizen', 
        task=lambda: None
    ),
    Role(
        name="murderer", 
        full_name="🔪 Маньяк", 
        description="Ты - 🔪 Маньяк.\nВсе вокруг должны умереть, кроме тебя.", 
        type='neutral', 
        task=lambda: None
    ),
    Role(
        name="lover", 
        full_name="💕 Любовница", 
        description="Ты - 💕 Любовница.\nТвоя цель - выжить. Используй свои навыки, чтобы заглушить одного любого игрока на одни сутки.", 
        type='citizen', 
        task=lambda: None
    ),
    Role(
        name="advocate", 
        full_name="🧑‍⚖️ Адвокат", 
        description="Ты - 🧑‍⚖️ Адвокат.\nТвоя цель - защитить мафию. Если ты выберешь Мафию, то Шериф не сможет узнать роль игрока, вместо этого он будет видеть роль Мирного жителя.", 
        type='mafia', 
        task=lambda: None
    ),
    Role(
        name="suicide", 
        full_name="💀 Самоубийца", 
        description="Ты - 💀 Самоубийца.\nТвоя цель - умереть на городском собрании.", 
        type='neutral', 
        task=lambda: None
    ),
    Role(
        name="homeless", 
        full_name="🧙 Бомж", 
        description="Ты - 🧙 Бомж.\nТвоя цель - выжить. Ты можешь зайти за бутылкой к любому игроку и стать свидетелем его смерти", 
        type='citizen', 
        task=lambda: None
    ),
    Role(
        name="happy", 
        full_name="🎉 Счастливчик", 
        description="Ты - 🎉 Счастливчик.\nТвоя цель - найти всех мафиози и убить их на городском собрании. Если повезет, после визита мафии ты можешь выжить.", 
        type='citizen', 
        task=lambda: None
    ),
    Role(
        name="kamikaze", 
        full_name="💥 Камикадзе", 
        description="Ты - 💥 Камикадзе.\nДнём и ночью ты обычный житель, но если тебя повесят, то ты можешь забрать любого из игроков с собой в могилу.", 
        type='citizen', 
        task=lambda: None
    ),
]
