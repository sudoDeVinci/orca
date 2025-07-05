from llm import (
    TOOLS,
    SYSTEM_PROMPT_TOOLS,
    SYSTEM_PROMPT_THIKING_SUPPRESION,
    COMMANDS,
    SYSTEM_PROMPT_COMMANDS,
    handle_tool_calls,
    LOGGER,
    BotSession,
    ToolCall
)

from json import dumps


SESSION = BotSession(
    params="14b",
    logfile="chat_history.json",
    tools=TOOLS
)
# Attempt to init the model
yn, err = SESSION.init_model()
if not yn or not SESSION.modelfile:
    print(f">> {err}")
    exit(0)

MODELFILE = SESSION.modelfile
print(f">> {MODELFILE['name']} is ready to use.")

SESSION.prepend_messages((
    {
        'role':"system",
        'content':MODELFILE['system']
    },
    {
        'role':"system",
        'content':SYSTEM_PROMPT_TOOLS
    },
    {
        'role':"system",
        'content':SYSTEM_PROMPT_THIKING_SUPPRESION
    },
    {
        'role':"system",
        'content':SYSTEM_PROMPT_COMMANDS
    },
    {
        'role':"system",
        'content':dumps(COMMANDS, ensure_ascii=False)
    }
))

# Preload the model into memory with the system prompts
SESSION.chat(
    stream=False,
)

