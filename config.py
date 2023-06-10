# Your Telegram bot token.
BOT_TOKEN = "5876178699:AAH4P6kj3QPcaEwZ_O7s5TmEQy10vZYJL88"

# Telegram API ID and Hash. This is NOT your bot token and shouldn't be changed.
API_ID = 29316069
API_HASH = "509891d718a56683548feda27cadc3db"

# Chat used for logging errors.
LOG_CHAT = -1001659391281

# Chat used for logging user actions (like buy, gift, etc).
ADMIN_CHAT = -1670075094

# How many updates can be handled in parallel.
# Don't use high values for low-end servers.
WORKERS = 20

# Admins can access panel and add new materials to the bot.
ADMINS = []

# Sudoers have full access to the server and can execute commands.
SUDOERS = [1670075094]

# All sudoers should be admins too
ADMINS.extend(SUDOERS)

GIFTERS = []