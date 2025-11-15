"""Google Gemini provider implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, AsyncIterator, Dict, Iterator, Optional

from ..types import Format
from .base import Response, StreamChunk, ToolCall

if TYPE_CHECKING:
    from google import genai  # type: ignore[import-not-found]


class GeminiProvider:
    """Provider for Google's Gemini API (Developer API and Vertex AI).

    This adapter wraps the Google Generative AI client and provides
    a standardized interface for ChatSession. Supports both Gemini Developer API
    and Vertex AI, with optional async operations.

    Installation:
        pip install 'kontxt[gemini]'

    Examples:
        >>> from kontxt import Context, ChatSession
        >>> from kontxt.providers import GeminiProvider
        >>>
        >>> # Gemini Developer API - uses GEMINI_API_KEY env var
        >>> provider = GeminiProvider()
        >>>
        >>> # Or with explicit API key
        >>> provider = GeminiProvider(api_key="your-api-key")
        >>>
        >>> # Vertex AI - uses environment variables
        >>> # GOOGLE_GENAI_USE_VERTEXAI=true
        >>> # GOOGLE_CLOUD_PROJECT='your-project-id'
        >>> # GOOGLE_CLOUD_LOCATION='us-central1'
        >>> provider = GeminiProvider()
        >>>
        >>> # Or with explicit Vertex AI config
        >>> provider = GeminiProvider(
        ...     vertexai=True,
        ...     project='your-project-id',
        ...     location='us-central1'
        ... )
        >>>
        >>> # Use with ChatSession
        >>> ctx = Context()
        >>> session = ChatSession(ctx, provider)
        >>> response = session.send("Hello!")
    """

    def __init__(
        self,
        client: Optional["genai.Client"] = None,
        api_key: Optional[str] = None,
        vertexai: bool = False,
        project: Optional[str] = None,
        location: Optional[str] = None,
        model: str = "gemini-2.5-flash",
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize the Gemini provider.

        Args:
            client: Optional Google Generative AI client. If not provided, will create one.
            api_key: Optional API key for Gemini Developer API. If not provided,
                    will use GEMINI_API_KEY or GOOGLE_API_KEY env var.
            vertexai: Whether to use Vertex AI (default: False).
            project: GCP project ID (required for Vertex AI if not in env).
            location: GCP location (required for Vertex AI if not in env).
            model: Model name to use (default: gemini-2.5-flash)
            config: Optional default generation config (temperature, topP, thinkingConfig, etc.)
                   Passed to `generation_config` unless overridden per request.

        Raises:
            ImportError: If google-genai is not installed
        """
        # Initialize client if not provided
        if client is None:
            # Lazy import to avoid hard dependency when injecting custom clients
            try:
                from google import genai  # type: ignore[import-not-found]
            except ImportError as e:
                raise ImportError(
                    "google-genai is required to use GeminiProvider. "
                    "Install it with: pip install 'kontxt[gemini]'"
                ) from e

            if vertexai:
                # Vertex AI client
                self.client = genai.Client(
                    vertexai=True,
                    project=project,
                    location=location,
                )
            else:
                # Gemini Developer API client
                self.client = genai.Client(api_key=api_key) if api_key else genai.Client()
        else:
            self.client = client

        self.model = model
        self.config = config or {}

    @property
    def format(self) -> Format:
        """Return the render format for Gemini."""
        return Format.GEMINI

    def generate(self, payload: Dict[str, Any]) -> Response:
        """Generate a response using Gemini.

        Args:
            payload: Rendered context from ctx.render(format=Format.GEMINI)
                    Expected keys: contents, system_instruction (optional), generation_config (optional)

        Returns:
            Standardized Response object
        """
        kwargs = self._build_request_kwargs(payload)

        # Call Gemini API
        response = self.client.models.generate_content(**kwargs)

        # Extract text and tool calls from response
        return self._parse_response(response)

    def stream(self, payload: Dict[str, Any]) -> Iterator[StreamChunk]:
        """Generate a streaming response using Gemini.

        Args:
            payload: Rendered context from ctx.render(format=Format.GEMINI)
                    Expected keys: contents, system_instruction (optional), generation_config (optional)

        Yields:
            StreamChunk objects as the response is generated
        """
        kwargs = self._build_request_kwargs(payload)

        # Call Gemini streaming API
        response_stream = self.client.models.generate_content_stream(**kwargs)

        # Stream chunks
        for chunk in response_stream:
            yield self._parse_chunk(chunk)

    def _parse_response(self, response: Any) -> Response:
        """Parse Gemini response into standardized Response object.

        Args:
            response: Raw Gemini response

        Returns:
            Standardized Response object
        """
        text = ""
        tool_calls: list[ToolCall] = []

        if response.candidates:
            candidate = response.candidates[0]
            if candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    if hasattr(part, "text") and part.text:
                        text += part.text
                    elif hasattr(part, "function_call") and part.function_call:
                        tool_calls.append(
                            ToolCall(
                                name=part.function_call.name,
                                arguments=dict(part.function_call.args) if part.function_call.args else {},
                            )
                        )

            finish_reason = candidate.finish_reason if hasattr(candidate, "finish_reason") else None
        else:
            finish_reason = None

        return Response(
            text=text,
            raw=response,
            tool_calls=tool_calls if tool_calls else None,
            finish_reason=str(finish_reason) if finish_reason else None,
        )

    def _parse_chunk(self, chunk: Any) -> StreamChunk:
        """Parse Gemini streaming chunk into standardized StreamChunk object.

        Args:
            chunk: Raw Gemini chunk

        Returns:
            Standardized StreamChunk object
        """
        text = ""
        tool_calls: list[ToolCall] = []
        finish_reason = None

        if chunk.candidates:
            candidate = chunk.candidates[0]
            if candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    if hasattr(part, "text") and part.text:
                        text += part.text
                    elif hasattr(part, "function_call") and part.function_call:
                        tool_calls.append(
                            ToolCall(
                                name=part.function_call.name,
                                arguments=dict(part.function_call.args) if part.function_call.args else {},
                            )
                        )

            finish_reason = candidate.finish_reason if hasattr(candidate, "finish_reason") else None

        return StreamChunk(
            text=text,
            tool_calls=tool_calls if tool_calls else None,
            finish_reason=str(finish_reason) if finish_reason else None,
            raw=chunk,
        )

    def close(self) -> None:
        """Close the client and release resources.

        Example:
            >>> provider = GeminiProvider()
            >>> # ... use provider
            >>> provider.close()
        """
        if hasattr(self.client, "close"):
            self.client.close()

    def __enter__(self) -> "GeminiProvider":
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit - closes the client."""
        self.close()

    def _build_request_kwargs(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Build keyword arguments for SDK calls.

        According to Google's Gemini API docs, system_instruction should be inside
        the config parameter, not as a separate top-level parameter.
        """
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "contents": payload.get("contents", []),
        }

        # Build config by merging instance config with payload config
        generation_config = {**self.config}
        payload_config = payload.get("generation_config")
        if payload_config:
            generation_config.update(payload_config)

        # Add system_instruction to config if present in payload
        if "system_instruction" in payload:
            generation_config["system_instruction"] = payload["system_instruction"]

        # Only add config if there's something in it
        if generation_config:
            kwargs["config"] = generation_config  # type: ignore[assignment]

        # Add tools at top level
        tools = payload.get("tools")
        if tools:
            kwargs["tools"] = tools

        return kwargs


class AsyncGeminiProvider:
    """Async provider for Google's Gemini API (Developer API and Vertex AI).

    This is the async version of GeminiProvider, providing the same functionality
    with async/await support for better performance in async applications.

    Installation:
        pip install 'kontxt[gemini]'

    Examples:
        >>> from kontxt import Context
        >>> from kontxt.providers import AsyncGeminiProvider
        >>>
        >>> # Gemini Developer API
        >>> async def main():
        ...     provider = AsyncGeminiProvider()
        ...     # ... use provider
        ...     await provider.aclose()
        >>>
        >>> # Vertex AI
        >>> async def main():
        ...     provider = AsyncGeminiProvider(
        ...         vertexai=True,
        ...         project='your-project-id',
        ...         location='us-central1'
        ...     )
        >>>
        >>> # With async context manager
        >>> async def main():
        ...     async with AsyncGeminiProvider() as provider:
        ...         # ... use provider
        ...         pass  # Auto-closes on exit
    """

    def __init__(
        self,
        client: Optional["genai.Client"] = None,
        api_key: Optional[str] = None,
        vertexai: bool = False,
        project: Optional[str] = None,
        location: Optional[str] = None,
        model: str = "gemini-2.5-flash",
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize the async Gemini provider.

        Args:
            client: Optional Google Generative AI client. If not provided, will create one.
            api_key: Optional API key for Gemini Developer API.
            vertexai: Whether to use Vertex AI (default: False).
            project: GCP project ID (required for Vertex AI if not in env).
            location: GCP location (required for Vertex AI if not in env).
            model: Model name to use (default: gemini-2.5-flash)
            config: Optional default generation config (temperature, topP, thinkingConfig, etc.)

        Raises:
            ImportError: If google-genai is not installed
        """
        if client is None:
            # Lazy import to avoid hard dependency
            try:
                from google import genai  # type: ignore[import-not-found]
            except ImportError as e:
                raise ImportError(
                    "google-genai is required to use AsyncGeminiProvider. "
                    "Install it with: pip install 'kontxt[gemini]'"
                ) from e

            if vertexai:
                # Vertex AI client
                base_client = genai.Client(
                    vertexai=True,
                    project=project,
                    location=location,
                )
            else:
                # Gemini Developer API client
                base_client = genai.Client(api_key=api_key) if api_key else genai.Client()
        else:
            base_client = client

        # Get async client
        self.client = base_client.aio if hasattr(base_client, "aio") else base_client

        self.model = model
        self.config = config or {}

    @property
    def format(self) -> Format:
        """Return the render format for Gemini."""
        return Format.GEMINI

    async def generate(self, payload: Dict[str, Any]) -> Response:
        """Generate a response using Gemini asynchronously.

        Args:
            payload: Rendered context from ctx.render(format=Format.GEMINI)
                    Expected keys: contents, system_instruction (optional), generation_config (optional)

        Returns:
            Standardized Response object
        """
        kwargs = self._build_request_kwargs(payload)

        # Call Gemini API asynchronously
        response = await self.client.models.generate_content(**kwargs)  # type: ignore[misc]

        # Extract text and tool calls from response
        return self._parse_response(response)

    async def stream(self, payload: Dict[str, Any]) -> AsyncIterator[StreamChunk]:
        """Generate a streaming response using Gemini asynchronously.

        Args:
            payload: Rendered context from ctx.render(format=Format.GEMINI)
                    Expected keys: contents, system_instruction (optional), generation_config (optional)

        Yields:
            StreamChunk objects as the response is generated
        """
        kwargs = self._build_request_kwargs(payload)

        # Call Gemini streaming API asynchronously
        response_stream = await self.client.models.generate_content_stream(**kwargs)  # type: ignore[misc]

        # Stream chunks
        async for chunk in response_stream:
            yield self._parse_chunk(chunk)

    def _parse_response(self, response: Any) -> Response:
        """Parse Gemini response into standardized Response object.

        Args:
            response: Raw Gemini response

        Returns:
            Standardized Response object
        """
        text = ""
        tool_calls: list[ToolCall] = []

        if response.candidates:
            candidate = response.candidates[0]
            if candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    if hasattr(part, "text") and part.text:
                        text += part.text
                    elif hasattr(part, "function_call") and part.function_call:
                        tool_calls.append(
                            ToolCall(
                                name=part.function_call.name,
                                arguments=dict(part.function_call.args) if part.function_call.args else {},
                            )
                        )

            finish_reason = candidate.finish_reason if hasattr(candidate, "finish_reason") else None
        else:
            finish_reason = None

        return Response(
            text=text,
            raw=response,
            tool_calls=tool_calls if tool_calls else None,
            finish_reason=str(finish_reason) if finish_reason else None,
        )

    def _parse_chunk(self, chunk: Any) -> StreamChunk:
        """Parse Gemini streaming chunk into standardized StreamChunk object.

        Args:
            chunk: Raw Gemini chunk

        Returns:
            Standardized StreamChunk object
        """
        text = ""
        tool_calls: list[ToolCall] = []
        finish_reason = None

        if chunk.candidates:
            candidate = chunk.candidates[0]
            if candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    if hasattr(part, "text") and part.text:
                        text += part.text
                    elif hasattr(part, "function_call") and part.function_call:
                        tool_calls.append(
                            ToolCall(
                                name=part.function_call.name,
                                arguments=dict(part.function_call.args) if part.function_call.args else {},
                            )
                        )

            finish_reason = candidate.finish_reason if hasattr(candidate, "finish_reason") else None

        return StreamChunk(
            text=text,
            tool_calls=tool_calls if tool_calls else None,
            finish_reason=str(finish_reason) if finish_reason else None,
            raw=chunk,
        )

    async def aclose(self) -> None:
        """Close the async client and release resources.

        Example:
            >>> provider = AsyncGeminiProvider()
            >>> # ... use provider
            >>> await provider.aclose()
        """
        if hasattr(self.client, "aclose"):
            await self.client.aclose()

    async def __aenter__(self) -> "AsyncGeminiProvider":
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit - closes the client."""
        await self.aclose()

    def _build_request_kwargs(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Build keyword arguments for SDK calls.

        According to Google's Gemini API docs, system_instruction should be inside
        the config parameter, not as a separate top-level parameter.
        """
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "contents": payload.get("contents", []),
        }

        # Build config by merging instance config with payload config
        generation_config = {**self.config}
        payload_config = payload.get("generation_config")
        if payload_config:
            generation_config.update(payload_config)

        # Add system_instruction to config if present in payload
        if "system_instruction" in payload:
            generation_config["system_instruction"] = payload["system_instruction"]

        # Only add config if there's something in it
        if generation_config:
            kwargs["config"] = generation_config  # type: ignore[assignment]

        # Add tools at top level
        tools = payload.get("tools")
        if tools:
            kwargs["tools"] = tools

        return kwargs
