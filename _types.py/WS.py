from typing import Generic, TypeVar
from abc import ABC

class EventPayload(ABC):
    pass

PayloadType = TypeVar('EventPayloadType', bound=EventPayload)


class IdentityEvent(EventPayload):
    """
    Triggers the initial handshake with the gateway
    """

    __slots__ = (
        'token',
        'properties',
        'compress',
        'large_threshold',
        'shard',
        'presence',
        'intents'
    )

    def __init__(
            self,
            token: str,
            properties: dict[str, str],
            compress: bool = False,
            large_threshold: int = 250,
            shard: tuple[int, int] | None = None,
            presence: dict | None = None,
            intents: int = 0
    ) -> None:
        """
        Initializes an IdentityEvent instance.

        Args:
            token (str): The bot's token for authentication
            properties (dict[str, str]): Properties of the client
            compress (bool): Whether to use compression for the payloads (default is False)
            large_threshold (int): 	Value between 50 and 250, total number of members where the gateway will stop sending offline members in the guild member list
            shard (tuple[int, int]): Shard information as a tuple of shard ID and total shards (optional)
            presence (dict): Presence information to send with the identity event (optional)
            intents (int): Bitwise flags indicating which events the client wants to receive
        """
        self.token = token
        self.properties = properties
        self.compress = compress
        self.large_threshold = large_threshold
        self.shard = shard
        self.presence = presence or {}
        self.intents = intents


class GatewayEvent(Generic[PayloadType]):
    """
    Represents a message received from the Discord Gateway.

    Example:
    ```
    {
        "op": 0,
        "d": {},
        "s": 42,
        "t": "GATEWAY_EVENT_NAME"
    }
    ```
    """
    __slots__ = (
        'op',
        'd',
        's',
        't'
    )

    def __init__(
            self,
            op: int,
            d: PayloadType,
            s: int | None = None,
            t: str | None = None
    ) -> None:
        """
        Initializes a GatewayMessage instance.

        Args:
            op (int): Gateway opcode, which indicates the payload type
            d (PayloadType): Data payload, which contains the actual message content
            s (int): Sequence number of event used for resuming sessions and heartbeating (optional)
            t (str): Event name, which indicates the type of event that occurred (optional)
        """
        self.op = op
        self.d = d
        self.s = s
        self.t = t
