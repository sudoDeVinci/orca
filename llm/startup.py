from ollama import (
    chat,
    ChatResponse,
    Message,
    create,
    list as list_models,
    ListResponse,
    ResponseError
)

from ._types import (
    Modelfile
)

from .utils import (
    Tool,
)

from typing import Iterator, Sequence
from logging import getLogger, Logger
from os.path import exists, isfile
from pathlib import Path
from os import makedirs

from json import load, dumps
from threading import Lock

LOGGER: Logger = getLogger(__name__)
"""
Global logger for the application.
Set to log at the INFO level by default (convenience).
"""
LOGGER.setLevel('INFO')

class BotSession:
    __slots__ = (
        "_MODELFILE",
        "_MESSAGES",
        "LOGFILE",
        "MFLOCK",
        "MSGLOCK",
        "_NAME",
        "TOOLS"
    )

    def __init__(
        self,
        params: str = "2b",
        logfile: str = "chatlog.json",
        tools: list[Tool] = None,
        defaultmsgs: Sequence[Message] = []
    ) -> None:
        
        self._MODELFILE: Modelfile | None = None
        """
        The model file content loaded from the config file.
        This is initialized to None and will be populated by
        the `read_config_file` function.
        """

        self._MESSAGES: list[Message] = []
        """
        A list of messages for this session.
        """

        self.LOGFILE = Path(__file__).parent.resolve() / "memory" / logfile
        self.LOGFILE.parent.mkdir(parents=True, exist_ok=True)
        """
        The path to the chat log file where the conversation
        will be saved. Defaults to "chatlog.json".
        """
        
        self.TOOLS = tools if tools else []
        """
        A list of tools that the bot can use during the chat session.
        If no tools are provided, it defaults to an empty list.
        """

        self._NAME: str | None = None
        """
        The name of the model being used.
        This is initialized to None and will be set
        when the model is successfully initialized.
        """

        self.MFLOCK: Lock = Lock()
        """
        A threading lock to ensure that the modelfile
        is interacted with in a thread-safe manner.
        """

        self.MSGLOCK: Lock = Lock()
        """
        A threading lock to ensure that the messages
        are interacted with in a thread-safe manner.
        """
        self.read_config_file(params=params)

        self.load_messages(defaultmsgs)

        LOGGER.info(f"BotSession initialized with params: {params}, logfile: {logfile}, tools: {tools}")

    @property
    def modelfile(self) -> Modelfile | None:
        """
        Property to access the model file content.
        This is a thread-safe way to access the model file content.
        It returns a copy of the model file to ensure that
        the original content is not modified outside of this class.

        Returns:
            - Modelfile | None: The model file content as a dictionary, or None if not available.
        """
        with self.MFLOCK:
            modelcopy = self._MODELFILE.copy() if self._MODELFILE else None
            return modelcopy
        
    @property
    def messages(self) -> list[Message]:
        """
        Property to access the messages of the session.
        This is a thread-safe way to access the messages.
        It returns a copy of the messages to ensure that
        the original content is not modified outside of this class.

        Returns:
            - list[Message]: A copy of the messages in the session.
        """
        with self.MSGLOCK:
            return self._MESSAGES.copy()
        
    @property
    def name(self) -> str | None:
        """
        Property to access the name of the model.

        Returns:
            - str | None: The name of the model, or None if not set.
        """
        return self._NAME
        
    def chat(
        self,
        stream: bool = True
    )  -> Iterator[ChatResponse]:
        """
        Starts a chat session with the model using the current messages.
        This is a thread-safe operation.

        Args:
            stream (bool): Whether to stream the response or not. Defaults to True.

        Returns:
            Iterator[ChatResponse]: An iterator that yields ChatResponse objects.
        """
        with self.MSGLOCK:
            return chat(
                model=self._NAME,
                messages=self._MESSAGES,
                stream=stream,
                tools=self.TOOLS
            )
        
    def add_message(
        self,
        message: Message
    ) -> None:
        """
        Adds a message to the session's message list.
        This is a thread-safe operation.

        Args:
            Message (Message): The message to be added to the session.
        """
        with self.MSGLOCK:
            self._MESSAGES.append(message)
            LOGGER.info(f"Message added: {Message}")

    def get_message(
            self,
            index: int
    ) -> Message | None:
        """
        Retrieves a reference to a message from the session's message list by index.
        We retrieve a copy of the message to ensure that the original message
        is not modified outside of this class.
        This is a thread-safe operation.

        Args:
            index (int): The index of the message to retrieve.

        Returns:
            Message | None: The message at the specified index, or None if the index is out of range.
        """
        with self.MSGLOCK:
            if 0 <= index < len(self._MESSAGES):
                return self._MESSAGES[index].copy()
            LOGGER.warning(f"Index {index} out of range for messages.")
            return None

    def extend_messages(
        self,
        messages: list[Message]
    ) -> None:
        """
        Extends the session's message list with a list of messages.
        This is a thread-safe operation.

        Args:
            messages (list[Message]): The list of messages to be added to the session.
        """
        with self.MSGLOCK:
            self._MESSAGES.extend(messages)
            LOGGER.info(f"Messages extended: {messages}")

    def prepend_messages(self, startingmsgs: Sequence[Message]) -> None:
        """
        Prepends the default messages to the session's message list.
        This is a thread-safe operation.
        WARNING: Big memory and performance impact if the list is large.
        """
        with self.MSGLOCK:
            if not all(msg in self._MESSAGES for msg in startingmsgs):
                LOGGER.info("Prepending messages to the session.")
                self._MESSAGES = list(startingmsgs) + self._MESSAGES

        
    def save(self) -> None:
        """
        Saves the current model file content to a JSON file.
        This is a thread-safe operation.
        """
        with self.MSGLOCK:
            try:
                with open(self.LOGFILE, "w") as f:
                    f.write(dumps(self._MESSAGES, indent=4))
                    LOGGER.info("Messages saved successfully.")    
            except ValueError as err:
                LOGGER.error(f"Error saving messages: {err}")
        

    def load_messages(self,
                      defaults: Sequence[Message]) -> None:
        """
        Loads the messages from the chat log file.
        This is a thread-safe operation.
        """
        if not exists(self.LOGFILE) or not isfile(self.LOGFILE):
            LOGGER.warning(f"Log file {self.LOGFILE} does not exist. Starting fresh.")
            self._MESSAGES = []
            return

        with self.MSGLOCK:
            try:
                with open(self.LOGFILE, "r") as f:
                    messages = load(f)
                    LOGGER.info("Messages loaded successfully.")
            
                # Check if defaults are already present in the messages
                if all(msg in messages for msg in defaults):
                    LOGGER.info("Defaults already present in messages, skipping addition.")
                    self._MESSAGES = messages
                    return

                # Prepend default messages to the session
                LOGGER.info("Prepending default messages to the session.")
                self._MESSAGES = list(defaults) + messages

                
            except ValueError:
                LOGGER.warning("No previous messages found, starting fresh.")


    def read_config_file(
            self,
            params: str = "2b"
    ) -> Modelfile | None:
        """
        Reads the config file and returns the content as a dictionary.

        Args:
            params (str): The key to access the specific model configuration in the config file.
                        This corresponds to billions of parameters for the model. Defaults to "2b".

        Returns:
            Modelfile | None: The content of the config file as a dictionary, or None if the file does not exist.
        """
        with self.MFLOCK:
            try:
                with open("config.json", "r") as f:
                    self._MODELFILE = load(f).get(params, None)
                    return self._MODELFILE.copy() if self._MODELFILE else None

            except ValueError as err:
                LOGGER.error(f"Error reading config file: {err}")
                return None


    def modelfile_str(self) -> str | None:
        """
        Converts the model file content to a string.

        Returns:
            str | None: The model file content as a string, or None if the model file is not available.
        """
        with self.MFLOCK:
            if self._MODELFILE is None: return None
        
            return (
                f"FROM {self._MODELFILE['model'].split(':')[0]}"
                "PARAMETER stop \"<|eot|>\"\n"
                "PARAMETER stop \"</answer>\"\n"
                f"PARAMETER top_p {self._MODELFILE['top_p']}\n"
                f"PARAMETER presence_penalty {self._MODELFILE['presence_penalty']}\n"
                f"PARAMETER frequency_penalty {self._MODELFILE['frequency_penalty']}\n"
                f"PARAMETER context_length {self._MODELFILE['context_length']}\n"
                f"PARAMETER temperature {self._MODELFILE['temperature']}\n"
                f"SYSTEM \"\"\"\n{self._MODELFILE['system']}\n\"\"\"\n"
            )


    def init_model(self) -> tuple[bool, str | None]:
        """
        Initializes the model by checking if it exists and creating it if not.
        Returns:
            tuple[bool, str | None]: A tuple containing a boolean indicating success or failure,
                                    and an error message if applicable.
        """
        # List all models
        models: ListResponse = list_models()
        with self.MFLOCK:
            modelcopy = self._MODELFILE.copy() if self._MODELFILE else None

        if modelcopy is None:
            return (False, "Model configuration file is empty.",)

        # Check if the main model is available
        for model in models['models']:
            if modelcopy['name'] in model['model']:
                self._NAME = modelcopy['name']
                return (True, None,)

        system = modelcopy.pop("system", None)
        name = modelcopy.pop("name", None)
        model = modelcopy.pop("model", None)

        try:
            # If the model is not available, create it
            # TODO: Import model filecontent.
            print(f">> {name} not found. Creating from config...")
            create(
                model=name,
                from_=model,
                system=system,
                parameters=modelcopy
                )
            print(f">> {name} created.")
        except ResponseError as e:
            # Handle the error if the model creation fails
            return (False, f"Error creating {name}:: {e}",)
        
        # Check if the model was created successfully
        models = list_models()
        for model in models['models']:
            if name in model['model']:
                self._NAME = name
                return (True, None,)
            
        # If the model is still not available, return an error
        return (False, f"Error creating {name}:: Model not found after creation",)
