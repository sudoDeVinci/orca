from discord import (
    Intents,
    Message
)

from discord.ext import (
    commands,
    tasks
)

from logging import (
    Formatter,
    DEBUG,
    ERROR
)

from utils import (
    HANDLER,
    TOKEN,
    check_time,
    remove_think_tags_section
)

from llm import (
    ToolCallErrorResponse,
    handle_tool_calls,
    get_specific_call,
    create_error_response
)

import asyncio

from llm_stuff import SESSION

intents = Intents.default()
intents.presences = True
intents.message_content = True
intents.members = True

KACK = "ORCA "
ORCA_CHANNEL = None
ANNOUNCMENTS_CHANNEL = None

orca = commands.Bot(command_prefix=KACK, intents=intents)


@tasks.loop(hours=24)
async def daily_message():
    if ORCA_CHANNEL  is None:
        print("CHANNEL IS NONE!!!")
        return
    await ORCA_CHANNEL.send("I am Orca, this is my daily message")

@daily_message.before_loop
async def before_daily_message():
    await orca.wait_until_ready()
    wait_time = check_time(3, 57)
    print(f"Waiting {wait_time} seconds to send the first message")
    await asyncio.sleep(wait_time)

@orca.event
async def on_ready() -> None:
    global ORCA_CHANNEL
    ORCA_CHANNEL  = orca.get_channel(1390131108670079130)
    print(f"Channel set to: {ORCA_CHANNEL .name if ORCA_CHANNEL  else 'None'}")
    
    # Start the daily message task
    if not daily_message.is_running():
        daily_message.start()

    print(f">> We are ready to rumble on {orca.user.name}")


@orca.command(name="login")
async def login(ctx: commands.Context, username: str | None = None, password: str | None = None) -> None:
    """Login to the bot with a username and password."""

    print(f"Received login request with username: {username} and password: {password}")
    errors: ToolCallErrorResponse = []
    if not username:
        errors.append({
            'title': "Missing Username",
            'detail': "You must provide a username to login.",
            'status': 400,
            'meta': None
        })

    if not password:
        errors.append({
            'title': "Missing Password",
            'detail': "You must provide a password to login.",
            'status': 400,
            'meta': None
        })

    if errors:
        toolreponse = create_error_response(errors)
        SESSION.add_message({
            'role': "tool",
            'content': toolreponse,
            'name': "login"
        })

    else:
        SESSION.add_message({
            'role': "user",
            'content': f"Login with username: {username} and password: {password}"
        })

    response = SESSION.chat(stream=False)

    if 'tool_calls' in response["message"]:
        print(f'Tool calls found in response: {response["message"]["tool_calls"]}')
        calls = handle_tool_calls(response['message'])
        print(f'Processed tool calls: {calls}')
        call = get_specific_call("login", calls)
        if not call:
            print("No login tool call found in the response.")
            await ctx.send("No ability to login found within the system.")
            return
        
        for call in calls:
            SESSION.add_message(call)

        response = SESSION.chat(stream=False)
        print(f">> Response after tool call: {response['message']['content']}")

        if not response:
            await ctx.send("I couldn't process your question after searching for functionality to complete your last request.")
            return

    after_no_think = remove_think_tags_section(response['message']['content'])
    print(f">> Response after processing: {after_no_think}")
    await ctx.send(after_no_think)

@orca.command(name="ask")
async def ask(ctx: commands.Context, *, question: str) -> None:
    """Ask a question to the bot."""
    if not question:
        await ctx.send("Please provide a question.")
        return

    print(f"Received question: {question}")
    
    # Process the question using the SESSION
    SESSION.add_message(
        {
            'role': "user",
            'content': question
        }
    )
    response = SESSION.chat(stream=False)

    if not response:
        await ctx.send("I couldn't process your question.")
        return

    await ctx.send(remove_think_tags_section(response['message']['content']))
    SESSION.add_message(response['message'])
        

orca.run(
    TOKEN,
    log_handler=HANDLER,
    log_formatter=Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s"),
    log_level=ERROR
)