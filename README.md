# 🤵🏻 Mafia Telegram Bot

Telegram bot for playing Mafia game with automatic game management and multiple roles.

## Features

- Automatic day/night phases management
- 12+ unique roles
- Voting system with lynch confirmation
- Private messages for special roles
- Auto win condition detection

## Installation

1. Clone repository:
```bash
git clone https://github.com/maybewewillw/mafiabot.git
cd mafiabot
```

2. Install dependencies:
```bash
uv sync
```

3. Set bot token in `bot.py` or as `BOT_TOKEN` environment variable

4. Run:
```bash
python main.py
```

## Usage

- `/new_game` - create new game
- `/extend` - extend start time by 30 seconds
- `/start` - start bot

Game starts automatically after 30 seconds (minimum 4 players).

## Roles

**Citizens**: Citizen, Sheriff, Sergeant, Doctor, Lover, Homeless, Lucky, Kamikaze

**Mafia**: Don, Mafia, Advocate

**Neutral**: Murderer, Suicide

## Tech Stack

- aiogram 3.22+
- SQLAlchemy 2.0+
- APScheduler
- Python 3.13+

## License

MIT
