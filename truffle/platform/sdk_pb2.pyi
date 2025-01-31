from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import (
    ClassVar as _ClassVar,
    Iterable as _Iterable,
    Mapping as _Mapping,
    Optional as _Optional,
    Union as _Union,
)

DESCRIPTOR: _descriptor.FileDescriptor

class GenerateFinishReason(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    FINISH_REASON_UNSPECIFIED: _ClassVar[GenerateFinishReason]
    FINISH_REASON_LENGTH: _ClassVar[GenerateFinishReason]
    FINISH_REASON_STOP: _ClassVar[GenerateFinishReason]
    FINISH_REASON_ERROR: _ClassVar[GenerateFinishReason]
    FINISH_REASON_USER: _ClassVar[GenerateFinishReason]

class TruffleType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    TRUFFLE_UNSPECIFIED: _ClassVar[TruffleType]
    TRUFFLE_IMAGE: _ClassVar[TruffleType]
    TRUFFLE_FILE: _ClassVar[TruffleType]

FINISH_REASON_UNSPECIFIED: GenerateFinishReason
FINISH_REASON_LENGTH: GenerateFinishReason
FINISH_REASON_STOP: GenerateFinishReason
FINISH_REASON_ERROR: GenerateFinishReason
FINISH_REASON_USER: GenerateFinishReason
TRUFFLE_UNSPECIFIED: TruffleType
TRUFFLE_IMAGE: TruffleType
TRUFFLE_FILE: TruffleType

class ModelDescription(_message.Message):
    __slots__ = ("model_id", "name", "description", "capabilities", "type", "is_local")
    class ModelType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        MODEL_UNSPECIFIED: _ClassVar[ModelDescription.ModelType]
        MODEL_SMART: _ClassVar[ModelDescription.ModelType]
        MODEL_FAST: _ClassVar[ModelDescription.ModelType]
        MODEL_VISION: _ClassVar[ModelDescription.ModelType]
        MODEL_AGI: _ClassVar[ModelDescription.ModelType]

    MODEL_UNSPECIFIED: ModelDescription.ModelType
    MODEL_SMART: ModelDescription.ModelType
    MODEL_FAST: ModelDescription.ModelType
    MODEL_VISION: ModelDescription.ModelType
    MODEL_AGI: ModelDescription.ModelType
    class Capabilities(_message.Message):
        __slots__ = (
            "structured_output",
            "image_support",
            "reasoner",
            "world_domination",
            "languages",
        )
        STRUCTURED_OUTPUT_FIELD_NUMBER: _ClassVar[int]
        IMAGE_SUPPORT_FIELD_NUMBER: _ClassVar[int]
        REASONER_FIELD_NUMBER: _ClassVar[int]
        WORLD_DOMINATION_FIELD_NUMBER: _ClassVar[int]
        LANGUAGES_FIELD_NUMBER: _ClassVar[int]
        structured_output: bool
        image_support: bool
        reasoner: bool
        world_domination: bool
        languages: _containers.RepeatedScalarFieldContainer[str]
        def __init__(
            self,
            structured_output: bool = ...,
            image_support: bool = ...,
            reasoner: bool = ...,
            world_domination: bool = ...,
            languages: _Optional[_Iterable[str]] = ...,
        ) -> None: ...

    MODEL_ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    CAPABILITIES_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    IS_LOCAL_FIELD_NUMBER: _ClassVar[int]
    model_id: int
    name: str
    description: str
    capabilities: ModelDescription.Capabilities
    type: ModelDescription.ModelType
    is_local: bool
    def __init__(
        self,
        model_id: _Optional[int] = ...,
        name: _Optional[str] = ...,
        description: _Optional[str] = ...,
        capabilities: _Optional[_Union[ModelDescription.Capabilities, _Mapping]] = ...,
        type: _Optional[_Union[ModelDescription.ModelType, str]] = ...,
        is_local: bool = ...,
    ) -> None: ...

class GetModelsRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GetModelsResponse(_message.Message):
    __slots__ = ("models",)
    MODELS_FIELD_NUMBER: _ClassVar[int]
    models: _containers.RepeatedCompositeFieldContainer[ModelDescription]
    def __init__(
        self, models: _Optional[_Iterable[_Union[ModelDescription, _Mapping]]] = ...
    ) -> None: ...

class SystemToolRequest(_message.Message):
    __slots__ = ("tool_name", "args")
    class ArgsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(
            self, key: _Optional[str] = ..., value: _Optional[str] = ...
        ) -> None: ...

    TOOL_NAME_FIELD_NUMBER: _ClassVar[int]
    ARGS_FIELD_NUMBER: _ClassVar[int]
    tool_name: str
    args: _containers.ScalarMap[str, str]
    def __init__(
        self, tool_name: _Optional[str] = ..., args: _Optional[_Mapping[str, str]] = ...
    ) -> None: ...

class SystemToolResponse(_message.Message):
    __slots__ = ("response", "results", "error")
    class ResultsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(
            self, key: _Optional[str] = ..., value: _Optional[str] = ...
        ) -> None: ...

    RESPONSE_FIELD_NUMBER: _ClassVar[int]
    RESULTS_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    response: str
    results: _containers.ScalarMap[str, str]
    error: str
    def __init__(
        self,
        response: _Optional[str] = ...,
        results: _Optional[_Mapping[str, str]] = ...,
        error: _Optional[str] = ...,
    ) -> None: ...

class SDKResponse(_message.Message):
    __slots__ = ("ok", "error")
    OK_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    ok: bool
    error: str
    def __init__(self, ok: bool = ..., error: _Optional[str] = ...) -> None: ...

class ToolUpdateRequest(_message.Message):
    __slots__ = ("friendly_description",)
    FRIENDLY_DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    friendly_description: str
    def __init__(self, friendly_description: _Optional[str] = ...) -> None: ...

class UserRequest(_message.Message):
    __slots__ = ("message", "reason")
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    message: str
    reason: str
    def __init__(
        self, message: _Optional[str] = ..., reason: _Optional[str] = ...
    ) -> None: ...

class UserResponse(_message.Message):
    __slots__ = ("response", "error", "attached_files")
    RESPONSE_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    ATTACHED_FILES_FIELD_NUMBER: _ClassVar[int]
    response: str
    error: str
    attached_files: _containers.RepeatedScalarFieldContainer[str]
    def __init__(
        self,
        response: _Optional[str] = ...,
        error: _Optional[str] = ...,
        attached_files: _Optional[_Iterable[str]] = ...,
    ) -> None: ...

class GenerateResponseFormat(_message.Message):
    __slots__ = ("format", "schema")
    class ResponseFormat(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        RESPONSE_TEXT: _ClassVar[GenerateResponseFormat.ResponseFormat]
        RESPONSE_JSON: _ClassVar[GenerateResponseFormat.ResponseFormat]

    RESPONSE_TEXT: GenerateResponseFormat.ResponseFormat
    RESPONSE_JSON: GenerateResponseFormat.ResponseFormat
    FORMAT_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_FIELD_NUMBER: _ClassVar[int]
    format: GenerateResponseFormat.ResponseFormat
    schema: str
    def __init__(
        self,
        format: _Optional[_Union[GenerateResponseFormat.ResponseFormat, str]] = ...,
        schema: _Optional[str] = ...,
    ) -> None: ...

class Content(_message.Message):
    __slots__ = ("role", "content", "data")
    class Role(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        ROLE_INVALID: _ClassVar[Content.Role]
        ROLE_USER: _ClassVar[Content.Role]
        ROLE_AI: _ClassVar[Content.Role]
        ROLE_SYSTEM: _ClassVar[Content.Role]

    ROLE_INVALID: Content.Role
    ROLE_USER: Content.Role
    ROLE_AI: Content.Role
    ROLE_SYSTEM: Content.Role
    ROLE_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    role: Content.Role
    content: str
    data: bytes
    def __init__(
        self,
        role: _Optional[_Union[Content.Role, str]] = ...,
        content: _Optional[str] = ...,
        data: _Optional[bytes] = ...,
    ) -> None: ...

class Context(_message.Message):
    __slots__ = ("history",)
    HISTORY_FIELD_NUMBER: _ClassVar[int]
    history: _containers.RepeatedCompositeFieldContainer[Content]
    def __init__(
        self, history: _Optional[_Iterable[_Union[Content, _Mapping]]] = ...
    ) -> None: ...

class GenerateRequest(_message.Message):
    __slots__ = ("message", "context", "max_tokens", "model_id", "temperature", "fmt")
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    CONTEXT_FIELD_NUMBER: _ClassVar[int]
    MAX_TOKENS_FIELD_NUMBER: _ClassVar[int]
    MODEL_ID_FIELD_NUMBER: _ClassVar[int]
    TEMPERATURE_FIELD_NUMBER: _ClassVar[int]
    FMT_FIELD_NUMBER: _ClassVar[int]
    message: str
    context: Context
    max_tokens: int
    model_id: int
    temperature: float
    fmt: GenerateResponseFormat
    def __init__(
        self,
        message: _Optional[str] = ...,
        context: _Optional[_Union[Context, _Mapping]] = ...,
        max_tokens: _Optional[int] = ...,
        model_id: _Optional[int] = ...,
        temperature: _Optional[float] = ...,
        fmt: _Optional[_Union[GenerateResponseFormat, _Mapping]] = ...,
    ) -> None: ...

class GenerationUsage(_message.Message):
    __slots__ = ("prompt_tokens", "completion_tokens", "approx_time")
    PROMPT_TOKENS_FIELD_NUMBER: _ClassVar[int]
    COMPLETION_TOKENS_FIELD_NUMBER: _ClassVar[int]
    APPROX_TIME_FIELD_NUMBER: _ClassVar[int]
    prompt_tokens: int
    completion_tokens: int
    approx_time: int
    def __init__(
        self,
        prompt_tokens: _Optional[int] = ...,
        completion_tokens: _Optional[int] = ...,
        approx_time: _Optional[int] = ...,
    ) -> None: ...

class TokenResponse(_message.Message):
    __slots__ = ("token", "finish_reason", "usage", "error")
    TOKEN_FIELD_NUMBER: _ClassVar[int]
    FINISH_REASON_FIELD_NUMBER: _ClassVar[int]
    USAGE_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    token: str
    finish_reason: GenerateFinishReason
    usage: GenerationUsage
    error: str
    def __init__(
        self,
        token: _Optional[str] = ...,
        finish_reason: _Optional[_Union[GenerateFinishReason, str]] = ...,
        usage: _Optional[_Union[GenerationUsage, _Mapping]] = ...,
        error: _Optional[str] = ...,
    ) -> None: ...

class GenerateResponse(_message.Message):
    __slots__ = ("response", "finish_reason", "usage", "error")
    RESPONSE_FIELD_NUMBER: _ClassVar[int]
    FINISH_REASON_FIELD_NUMBER: _ClassVar[int]
    USAGE_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    response: str
    finish_reason: GenerateFinishReason
    usage: GenerationUsage
    error: str
    def __init__(
        self,
        response: _Optional[str] = ...,
        finish_reason: _Optional[_Union[GenerateFinishReason, str]] = ...,
        usage: _Optional[_Union[GenerationUsage, _Mapping]] = ...,
        error: _Optional[str] = ...,
    ) -> None: ...

class SortedEmbedding(_message.Message):
    __slots__ = ("text", "score")
    TEXT_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    text: str
    score: float
    def __init__(
        self, text: _Optional[str] = ..., score: _Optional[float] = ...
    ) -> None: ...

class EmbedResponse(_message.Message):
    __slots__ = ("results",)
    RESULTS_FIELD_NUMBER: _ClassVar[int]
    results: _containers.RepeatedCompositeFieldContainer[SortedEmbedding]
    def __init__(
        self, results: _Optional[_Iterable[_Union[SortedEmbedding, _Mapping]]] = ...
    ) -> None: ...

class EmbedRequest(_message.Message):
    __slots__ = ("documents", "query")
    DOCUMENTS_FIELD_NUMBER: _ClassVar[int]
    QUERY_FIELD_NUMBER: _ClassVar[int]
    documents: _containers.RepeatedScalarFieldContainer[str]
    query: str
    def __init__(
        self, documents: _Optional[_Iterable[str]] = ..., query: _Optional[str] = ...
    ) -> None: ...
