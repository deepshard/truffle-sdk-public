import typing
import os
import json
import grpc
import base64
import requests

from . import platform

APP_SOCK = (
    os.getenv("TRUFFLE_APP_SOCKET")
    if os.getenv("TRUFFLE_APP_SOCKET") is not None
    else "unix:///tmp/truffle_app.sock"
)
SDK_SOCK = (
    os.getenv("TRUFFLE_SDK_SOCKET")
    if os.getenv("TRUFFLE_SDK_SOCKET") is not None
    else "unix:///tmp/truffle_sdk.sock"
)


SHARED_FILES_DIR = (
    os.getenv("TRUFFLE_SHARED_DIR")
    if os.getenv("TRUFFLE_SHARED_DIR") is not None
    else "/root/shared"  # container default 1.31.25
)


class TruffleClient:
    def __init__(self, host=SDK_SOCK):
        """
        Provides a pythonic interface to access the core functionality of the platform
        """
        self.channel = grpc.insecure_channel(host)
        self.stub = platform.sdk_pb2_grpc.TruffleSDKStub(self.channel)
        self.model_contexts: list[platform.sdk_pb2.Context] = []

    def perplexity_search(
        self,
        query: str,
        model: str = "sonar",
        response_fmt=None,
        system_prompt: str = "",
    ) -> str:
        """
        Perform a search using [Perplexity's API](https://docs.perplexity.ai/)
        """
        # https://docs.perplexity.ai/guides/model-cards
        perplexity_models_feb24 = [
            "sonar-reasoning",  # Chat Completion - 127k context length
            "sonar-pro",  # Chat Completion - 200k " "
            "sonar",  # Chat Completion - 127k " "
        ]
        if model not in perplexity_models_feb24:
            raise ValueError(
                f"Model '{model}' not found in available models [{perplexity_models_feb24}]. See https://docs.perplexity.ai/guides/model-cards"
            )

        PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ],
        }
        # https://docs.perplexity.ai/guides/structured-outputs
        if response_fmt is not None:
            payload["response_format"] = response_fmt

        # TODO: support everything! they have such a cool API - image return would be insane, and citations!
        # https://docs.perplexity.ai/api-reference/chat-completions
        try:
            request = platform.sdk_pb2.SystemToolRequest(tool_name="perplexity_search")
            request.args["url"] = PERPLEXITY_API_URL
            request.args["payload"] = json.dumps(payload)

            r: platform.sdk_pb2.SystemToolResponse = self.stub.SystemTool(request)
            if r.error:
                raise RuntimeError(f"SystemToolError: {r.error}")

            results = json.loads(r.response)

            return results["choices"][0]["message"]["content"]
        except grpc.RpcError as e:
            raise RuntimeError(f"RPC error: {e.details()}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"JSON error: {e}")

    def get_models(self):
        """
        Get the model which are available on the platform
        """
        response: list[platform.sdk_pb2.ModelDescription] = self.stub.GetModels(
            platform.sdk_pb2.GetModelsRequest()
        ).models
        return response

    # WIP - missing ui
    def tool_update(self, message: str):
        """
        Inform the user of something in the middle of a tool call.

        Handy for long-running tools
        """
        try:
            r: platform.sdk_pb2.SDKResponse = self.stub.ToolUpdate(
                platform.sdk_pb2.ToolUpdateRequest(friendly_description=message)
            )
            if r.error:
                raise RuntimeError(f"RPC error: {r.error}")

        except grpc.RpcError as e:
            raise RuntimeError(f"RPC error: {e.details()}")

    # WIP - missing ui
    def ask_user(
        self, message: str, reason: str = "Tool needs input to continue."
    ) -> typing.Dict[str, typing.Union[str, typing.List[str]]]:
        """
        Ask the user for input

        Args:
            message: The message to display to the user
            reason: The reason for the input

        Returns:
            A dictionary with the user's response, * marks optional fields:
                - 'response': The user's response as a string
                * 'error': A string error message if the user input failed
                * 'files' : A list of file paths if the user uploaded files
        """

        try:
            response: platform.sdk_pb2.UserResponse = self.stub.AskUser(
                platform.sdk_pb2.UserRequest(message=message, reason=reason)
            )
            ret = {"response": response.response}
            # if response.HasField("error"):
            #     ret["error"] = response.error
            # if response.HasField("files") and len(response.attached_files):
            #     ret["files"] = list(response.attached_files)
            return ret

        except grpc.RpcError as e:
            raise RuntimeError(f"RPC error: {e.details()}")

    def query_embed(
        self, query: str, documents: typing.List[str]
    ) -> typing.List[typing.Tuple[str, float]]:
        """
        Returns a list of documents sorted by cosine similarity to the query via. text embeddings, which really should include that value. Doh.

        Args:
            query: The query string
            documents: A list of document strings to search

        Returns:
            A list of document strings sorted by cosine similarity to the query from most to least similar

        """
        request = platform.sdk_pb2.EmbedRequest(query=query, documents=documents)
        # i have not tested this
        try:
            response: platform.sdk_pb2.EmbedResponse = self.stub.Embed(request)
            print("Embedding response: ")
            results = []
            if len(response.results) == 0:
                raise ValueError("No results returned")
            for r in response.results:
                print(f"{r.text}: {r.score}")
                results.append((r.text, r.score))
            return results
        except grpc.RpcError as e:
            raise RuntimeError(f"Embed RPC error: {e.details()}")
        except ValueError as e:
            raise RuntimeError(f"Embed Value error: {e}")

    def infer(
        self,
        prompt: str,
        model_id: int = 0,
        system_prompt: str | None = None,
        context_idx: int | None = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        format_type: str = None,
        schema: str = None,
    ) -> typing.Iterator[str]:
        """
        Make a streaming inference request to the TruffleSDK service.

        Args:
            prompt: The input prompt for generation
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature (0.0 to 1.0)
            format_type: Optional response format (TEXT, JSON, EBNF)
            schema: Optional schema for structured output

        Returns:
            Iterator yielding generated tokens
        """
        # TODO: properly handle format stuff
        format_spec = None
        if format_type:
            format_spec = platform.sdk_pb2.GenerateResponseFormat(
                format=platform.sdk_pb2.GenerateResponseFormat.ResponseFormat.Value(
                    f"RESPONSE_{format_type}"
                ),
                schema=schema,
            )

        # Fetch or build the context for the chat
        if context_idx is not None:
            if self.context_idx is not None and system_prompt is not None:
                raise ValueError(
                    "Only pass system_prompt or context_idx, but not both!"
                )
            current_context = self.model_contexts[context_idx]
        else:
            self.model_contexts.append(platform.sdk_pb2.Context())
            current_context: platform.sdk_pb2.Context = self.model_contexts[-1]
            if system_prompt is not None:
                current_context.history.append(
                    platform.sdk_pb2.Content(
                        role=platform.sdk_pb2.Content.ROLE_SYSTEM, content=system_prompt
                    )
                )

        current_context.history.append(
            platform.sdk_pb2.Content(
                role=platform.sdk_pb2.Content.Role.ROLE_USER, content=prompt
            )
        )

        # Create the generation request
        request = platform.sdk_pb2.GenerateRequest(
            model_id=model_id,
            context=current_context,
            max_tokens=max_tokens,
            temperature=temperature,
            fmt=format_spec,
        )

        try:
            # Make the streaming call
            streamed_message = []
            for response in self.stub.Infer(request):
                if response.error:
                    raise RuntimeError(f"Generation error: {response.error}")

                if response.finish_reason:
                    # Handle different finish reasons
                    if (
                        response.finish_reason
                        == platform.sdk_pb2.GenerateFinishReason.FINISH_REASON_ERROR
                    ):
                        raise RuntimeError("Generation terminated with error")
                    elif (
                        response.finish_reason
                        != platform.sdk_pb2.GenerateFinishReason.FINISH_REASON_UNSPECIFIED
                    ):
                        break

                streamed_message.append(response.token)
                yield response.token

            current_context.history.append(
                platform.sdk_pb2.Content(
                    role=platform.sdk_pb2.Content.ROLE_AI,
                    content="".join(streamed_message),
                )
            )

        except grpc.RpcError as e:
            raise RuntimeError(f"RPC error: {e} {e.details()}")

    def close(self):
        """Close the gRPC channel"""
        self.channel.close()


class TruffleReturnType:
    def __init__(self, type: platform.sdk_pb2.TruffleType):
        self.type = type


class TruffleFile(TruffleReturnType):
    def __init__(self, path: str, name: str):
        super().__init__(platform.sdk_pb2.TRUFFLE_FILE)
        self.path = path
        self.name = name
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")
        if os.path.commonprefix([SHARED_FILES_DIR, path]) == SHARED_FILES_DIR:
            return  # file is already in shared dir
        shared_path = SHARED_FILES_DIR + "/" + name
        os.rename(path, shared_path)
        os.chmod(
            shared_path, 0o777
        )  # make it readable by everyone - there is a wide world outside of this container
        self.path = shared_path


class TruffleImage(TruffleReturnType):
    def __init__(
        self, name: str, url: str = None, base64_data: str = None, data: bytes = None
    ):
        super().__init__(platform.sdk_pb2.TRUFFLE_IMAGE)
        path = SHARED_FILES_DIR + "/" + name
        if base64_data:
            data = base64.b64decode(base64_data)
        elif url:
            data = requests.get(url).content
        if data:
            with open(path, "wb") as f:
                f.write(data)
        self.path = path if path else None
        self.name = name
        # do we send b64 back or just the path? ask client
        if path and not os.path.exists(path):
            raise FileNotFoundError(f"Image file not found: {path}")
