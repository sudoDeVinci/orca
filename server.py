from discord import (
    Intents,
    Message
)

from discord.ext import (
    commands
)

from logging import(
    Logger,
    FileHandler,
    Formatter,
    getLogger,
    DEBUG
)

from utils import (
    HANDLER,
    TOKEN
)

intents = Intents.default()
intents.presences = True
intents.message_content = True
intents.members = True

KACK = "IDAT "

orca = commands.Bot(command_prefix=KACK, intents=intents)
kack = commands.Bot(command_prefix=KACK, intents=intents)

@orca.event
async def on_ready() -> None:
    print(f"We are ready to rumble on {orca.user.name}")

@orca.command()
async def who(context: commands.Context):
    message = context.message.content
    substringbeg = message.index(KACK)
    await context.send(f"Command is: {message[substringbeg+4:]}")

@orca.command()
async def what(context: commands.Context):
    message = context.message.content
    substringbeg = message.index(KACK)
    await context.send(f"Command is: {message[substringbeg+4:]}")

@orca.command()
async def italic(context: commands.Context):
    message = context.message.content
    substringbeg = message.index(KACK)
    await context.send(f"*{message[substringbeg+11:].strip()}*")

@orca.command()
async def bold(context: commands.Context):
    message = context.message.content
    substringbeg = message.index(KACK)
    await context.send(f"**{message[substringbeg+9:].strip()}**")

@orca.command()
async def code(context: commands.Context):
    message = context.message.content
    substringbeg = message.index(KACK)
    await context.send(f"```{message[substringbeg+9:].strip()}```")

orca.run(
    TOKEN,
    log_handler=HANDLER,
    log_formatter=Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s"),
    log_level=DEBUG
)