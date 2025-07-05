from typing import (
    TypedDict,
    Any,
    Mapping,
    Optional,
    Sequence,
    Literal,
    Union,
    Generic,
    TypeVar
)

from pydantic import (
    ConfigDict,
    Field
)

from ollama._types import (
    SubscriptableBaseModel
)

class Modelfile(TypedDict):
    """
    A singular Model file for a give model.

    Attributes:
        model (str): The model identifier.
        name (str): The name of the model.
        description (str): A description of the model.
        temperature (float): The temperature setting for the model.
        top_p (float): The top-p setting for the model.
        presence_penalty (float): The presence penalty for the model.
        frequency_penalty (float): The frequency penalty for the model.
        context_length (int): The context length for the model.
        system (str): The system prompt for the model.
    """
    model: str
    name: str
    description: str
    temperature: float
    top_p: float
    presence_penalty: float
    frequency_penalty: float
    context_length: int
    system: str


class Property(SubscriptableBaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    type: Optional[Union[str, Sequence[str]]] = None
    items: Optional[Any] = None
    description: Optional[str] = None
    enum: Optional[Sequence[Any]] = None


class Parameters(SubscriptableBaseModel):
    model_config = ConfigDict(populate_by_name=True)
    type: Optional[Literal['object']] = 'object'
    defs: Optional[Any] = Field(None, alias='$defs')
    items: Optional[Any] = None
    required: Optional[Sequence[str]] = None
    properties: Optional[Mapping[str, Property]] = None


class Function(SubscriptableBaseModel):
    """
    Function definition
    """
    name: Optional[str] = None
    description: Optional[str] = None
    parameters: Optional[Parameters] = None


class _Function(SubscriptableBaseModel):
    name: Optional[str] = None
    arguments: Mapping[str, Any]


class ToolCall(SubscriptableBaseModel):
    """
    Model tool calls.
    This uses the "arguments" field of the
    Function, NOT "parameters".
    """
    function: _Function

class ToolResponse(TypedDict):
    """
    Tool function call response to model

    Attributes:
        role (str): The role of the message (e.g., "tool").
        content (str | None): The content of the message, if any.
        name (str | None): The name of the tool being called, if applicable.
    """
    role: str
    content: str | None
    name: str | None

class ToolCallErrorResponse(TypedDict):
    errors: Sequence[Mapping[str, Any]] | None
    warnings: Sequence[Mapping[str, Any]] | None

class ToolCallReturnable(TypedDict):
    pass

ReturnableData = TypeVar('ReturnableData', ToolCallReturnable, str)


class AuthenticationToken(TypedDict, ToolCallReturnable):
    """
    Authentication token response.
    Attributes:
        AccessToken (str): The access token for authentication.
        TokenType (str): The type of the token (e.g., "Bearer").
        ExpiresIn (int): The number of seconds until the token expires.
        RefreshToken (str): The refresh token to obtain a new access token.
    """
    AccessToken: str
    TokenType: str
    ExpiresIn: int
    RefreshToken: str

class ToolCallReturnData(TypedDict, Generic[ReturnableData]):
    """
    Tool call return data.

    Attributes:
        data (T): The data returned by the tool call.
        status (int): The HTTP status code of the response.
    """
    data: ReturnableData
    status: int