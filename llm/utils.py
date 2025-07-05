from ollama import Tool, Message
from ._types import (
    ToolCall,
    ToolResponse,
    AuthenticationToken,
    ToolCallErrorResponse,
    ToolCallReturnData
)
from typing import Sequence, Callable
import jwt

from os import environ
from dotenv import load_dotenv

from json import dumps

SYSTEM_PROMPT_TOOLS = (
    """
{- if .Messages }}
{{- if or .System .Tools }}<|im_start|>system
{{- if .System }}
{{ .System }}
{{- end }}
{{- if .Tools }}

# Tools

You may call one or more functions to assist with the user query.

You are provided with function signatures within <tools></tools> XML tags:
<tools>
{{- range .Tools }}
{"type": "function", "function": {{ .Function }}}
{{- end }}
</tools>

For each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:
<tool_call>
{"name": <function-name>, "arguments": <args-json-object>}
</tool_call>
{{- end }}<|im_end|>
{{ end }}
{{- range $i, $_ := .Messages }}
{{- $last := eq (len (slice $.Messages $i)) 1 -}}
{{- if eq .Role "user" }}<|im_start|>user
{{ .Content }}<|im_end|>
{{ else if eq .Role "assistant" }}<|im_start|>assistant
{{ if .Content }}{{ .Content }}
{{- else if .ToolCalls }}<tool_call>
{{ range .ToolCalls }}{"name": "{{ .Function.Name }}", "arguments": {{ .Function.Arguments }}}
{{ end }}</tool_call>
{{- end }}{{ if not $last }}<|im_end|>
{{ end }}
{{- else if eq .Role "tool" }}<|im_start|>user
<tool_response>
{{ .Content }}
</tool_response><|im_end|>
{{ end }}
{{- if and (ne .Role "assistant") $last }}<|im_start|>assistant
{{ end }}
{{- end }}
{{- else }}
{{- if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}{{ if .Prompt }}<|im_start|>user
{{ .Prompt }}<|im_end|>
{{ end }}<|im_start|>assistant
{{ end }}{{ .Response }}{{ if .Response }}<|im_end|>{{ end }}
    """
)

SYSTEM_PROMPT_THIKING_SUPPRESION = (
"""
{- range $i, $_ := .Messages }}
{{- $last := eq (len (slice $.Messages $i)) 1 -}}
{{- if eq .Role "user" }}<|im_start|>user
{{ .Content }}
{{/* This part correctly appends /think or /no_think based on $.IsThinkSet and $.Think */}}
{{- if and $.IsThinkSet (eq $i $lastUserIdx) }}
   {{- if $.Think -}}
      {{- " "}}/think
   {{- else -}}
      {{- " "}}/no_think
   {{- end -}}
{{- end }}<|im_end|>
{{ else if eq .Role "assistant" }}<|im_start|>assistant
{{/* Modified condition: Only render .Thinking if $.Think is true (user explicitly wants to think) */}}
{{ if (and $.Think .Thinking (or $last (gt $i $lastUserIdx))) -}}
<think>{{ .Thinking }}</think>
{{ end -}}
{{ if .Content }}{{ .Content }}
{{- else if .ToolCalls }}<tool_call>
{{ range .ToolCalls }}{"name": "{{ .Function.Name }}", "arguments": {{ .Function.Arguments }}}
{{ end }}</tool_call>
{{- end }}{{ if not $last }}<|im_end|>
{{ end }}
{{- else if eq .Role "tool" }}<|im_start|>user
<tool_response>
{{ .Content }}
</tool_response><|im_end|>
{{ end }}
{{- if and (ne .Role "assistant") $last }}<|im_start|>assistant
{{/* Removed the conditional empty <think> block.
     If $.Think is true, the model should generate the <think> block itself.
     If $.Think is false, no thinking is desired.
     Original block that was here:
     {{ if and $.IsThinkSet (not $.Think) -}}
     <think>

     </think>
     {{ end -}}
*/}}
{{ end }}
{{- end }}
"""
)

SYSTEM_PROMPT_COMMANDS = (
"""
{{- if .Messages }}
{{- if or .System .Commands }}<|im_start|>system
{{- if .System }}
{{ .System }}
{{- end }}
{{- if .Commands }}

# Commands

You can execute specific commands by prefixing them with "ORCA " followed by the command and its parameters.

Available commands:
{{- range .Commands }}
- ORCA {{ .Signature }}: {{ .Description }}
{{- end }}

When a user types a command starting with "ORCA ", parse and execute it accordingly. For the 'ask' command, provide guidance on which command to use instead of executing the action directly.

Examples:
- ORCA login john_doe mypassword123
- ORCA generate_random_string 16
- ORCA ask Can you log me in please?
- ORCA help

If the input starts with "ORCA " but doesn't match any command, respond with: "Command not recognised. Available commands: {{ range $i, $cmd := .Commands }}{{if $i}}, {{end}}{{ $cmd.Name }}{{ end }}"
{{- end }}<|im_end|>
{{ end }}
{{- range $i, $_ := .Messages }}
{{- $last := eq (len (slice $.Messages $i)) 1 -}}
{{- if eq .Role "user" }}<|im_start|>user
{{ .Content }}<|im_end|>
{{ else if eq .Role "assistant" }}<|im_start|>assistant
{{ if .Content }}{{ .Content }}{{ end }}{{ if not $last }}<|im_end|>
{{ end }}
{{- end }}
{{- if and (ne .Role "assistant") $last }}<|im_start|>assistant
{{ end }}
{{- end }}
{{- else }}
{{- if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}{{ if .Prompt }}<|im_start|>user
{{ .Prompt }}<|im_end|>
{{ end }}<|im_start|>assistant
{{ end }}{{ .Response }}{{ if .Response }}<|im_end|>{{ end }}
"""
)

# Command definitions for ORCA
COMMANDS = [
    {
        'name': 'login',
        'signature': 'login <username> <password>',
        'description': 'Authenticate user and return access token'
    },
    {
        'name': 'generate_random_string',
        'signature': 'generate_random_string <length>',
        'description': 'Generate a random string of specified length'
    },
    {
        'name': 'ask',
        'signature': 'ask <question>',
        'description': 'Ask for guidance on which command to use for a specific task'
    },
    {
        'name': 'help',
        'signature': 'help [command_name]',
        'description': 'Show help for all commands or a specific command'
    }
]

def create_error_response(
        errors: list[ToolCallErrorResponse],
        warnings: list[ToolCallErrorResponse] | None = None
) -> str:
    """
    Creates an error response object with the provided errors and warnings.
    
    Args:
        errors (list[ToolCallErrorResponse]): A list of error details.
        warnings (list[ToolCallErrorResponse] | None): A list of warning details, if any.
    
    Returns:
        ToolCallErrorResponse: A dictionary containing the error and warning details.
    """
    return dumps(
        {
            'errors': errors,
            'warnings': warnings
        },
        ensure_ascii=False
    )


def generate_random_string(
        length: int
) -> str:

    def gen_string(length: int) -> ToolCallReturnData[str] | ToolCallErrorResponse:
        """
        Generates a random string of characters of a specified length.
        Args:
            length (int): The length of the random string to generate.
        
        Returns:
            str: A random string of characters.
        """
        import random
        import string
        
        try:
            assert length > 0, "Length must be a positive integer"
            characters = string.ascii_letters + string.digits
            return {
                'data': ''.join(random.choice(characters) for _ in range(length)),
                'status': 200
            }
        except AssertionError as e:
            return {
                'errors': [
                    {   'title': 'Invalid Length',
                        'details': str(e),
                        'status': 400,
                        'meta': None
                    }
                ]
            }
        
        except ValueError as e:
            return {
                'errors': [
                    {   'title': 'Unexpected Error',
                        'details': str(e),
                        'status': 500,
                        'meta': None
                    }
                ]
            }
        
    return dumps(gen_string(length), ensure_ascii=False)
        
    


def _mock_jwt(
    username: str,
    password: str,
) -> AuthenticationToken:
    
    def _generate_jwt(
        secret: str,
        payload: dict,
        algorithm: str = 'HS256'
    ) -> str:
        """
        Generates a JWT token using the provided secret and payload.
        
        Args:
            secret (str): The secret key used to sign the JWT.
            payload (dict): The payload data to include in the JWT.
            algorithm (str): The algorithm to use for signing the JWT. Default is 'HS256'.
        
        Returns:
            str: The generated JWT token.
        """
        return jwt.encode(payload, secret, algorithm=algorithm)

    assert load_dotenv(verbose=True), "Failed to load .env file"
    SECRET = environ.get("CLIENT_SECRET", None)
    assert SECRET is not None, "CLIENT_SECRET is not set in the environment variables"

    return AuthenticationToken(
        AccessToken=_generate_jwt(SECRET, {'username': username}),
        TokenType='Bearer',
        ExpiresIn=3600,  # Token valid for 1 hour
        RefreshToken=_generate_jwt(SECRET, {'username': username, 'refresh': True})
    )

def login(
    username: str,
    password: str,
    method: Callable[[str, str], AuthenticationToken] = _mock_jwt
) -> str:
    """
    Wrapper function for the login functionality.
    This function handles user authentication and returns an authentication token.

    Args:
        username (str): The username for authentication.
        password (str): The password for authentication.
        method (Callable[[str, str], AuthenticationToken]): The method to use for generating the authentication token.

    Returns:
        str: A JSON string containing the authentication token and status - or ErrorResponse object.
    """
    def _login(
        username: str,
        password: str,
        method: Callable[[str, str], AuthenticationToken] = _mock_jwt,
    ) -> ToolCallReturnData[AuthenticationToken] | ToolCallErrorResponse:
        """
        Login function that returns an authentication token.
        
        Args:
            username (str): The username for authentication.
            password (str): The password for authentication.
        
        Returns:
            ToolCallReturnData[AuthenticationToken]: A dictionary containing the authentication token and status.
            ToolCallErrorResponse: A dictionary containing error details if authentication fails.
        """
        try:
            assert username and password, "Username and password must be provided"
            return {
                'data': method(username, password),
                'status': 200
            }
        except AssertionError as e:
            return {
                'errors': [
                    {
                        'title': 'Authentication Error',
                        'details': str(e),
                        'status': 400,
                        'meta': None
                    }
                ],
                'warnings': None
            }
        
        except ValueError as e:
            return {
                'errors': [
                    {
                        'title': 'Authentication Error',
                        'details': str(e),
                        'status': 500,
                        'meta': None
                    }
                ],
                'warnings': None
            }
    
    return dumps(_login(username, password, method), ensure_ascii=False)

TOOLS: list[Tool] = [
    {
        'type':"function",
        'function': {
            'name':"generate_random_string",
            'description':"Generates a random string of characters of a specified length.",
            'parameters':{
                'type':"object",
                'required':["length"],
                'properties':{
                    "length": {
                        'type':"int",
                        'description':"The length of the random string to generate."
                    },
                }
            },
        }
    },
    {
        'type':"function",
        'function': {
            'name':"login",
            'description':"Logs in a user and returns an authentication token.",
            'parameters':{
                'type':"object",
                'required':["username", "password"],
                'properties':{
                    "username": {
                        'type':"string",
                        'description':"The username for authentication."
                    },
                    "password": {
                        'type':"string",
                        'description':"The password for authentication."
                    },
                    "method": {
                        'type':"string",
                        'description':"The method to use for generating the authentication token. Defaults to _mock_jwt."
                    },
                }
            },
        }
    }
]

TOOLS_LOOKUP: dict[str, callable] = {
    "generate_random_string": generate_random_string,
    "login": login
}

def get_specific_call(name: str, responses: list[ToolResponse]) -> ToolResponse | None:
    """
    Retrieves a specific tool call response by name from a list of tool responses.
    
    Args:
        name (str): The name of the tool call to retrieve.
        list[ToolResponse]: The list of tool responses to search in.
    
    Returns:
        ToolResponse | None: The tool response if found, otherwise None.
    """
    for call in responses:
        if call['name'] == name:
            return call
    return None


def handle_tool_calls(message: Message) -> list[ToolResponse]:
    out = []
    
    calls: Sequence[ToolCall] = message.get('tool_calls', [])
    
    for call in calls:
        name = call.function.name
        args = call.function.arguments
        func = TOOLS_LOOKUP.get(name, None)
        if not func: continue
        result = func(**args)
        out.append({
            'role':"tool",
            'content':result,
            'name':name
        })

    return out