"""OpenAI の担当クラス（任意。OpenAI の API キーを持っている人向け）"""
import json

from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

from app.llm.base import LLMError, Message, Reply, ToolCall, ToolResult
from app.retry import with_retry


class OpenAIClient:
    def __init__(self, model: str, api_key: str, base_url: str | None = None,
                 embed_model: str = "text-embedding-3-small"):
        self.model = model
        self.embed_model = embed_model
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.last_usage = (0, 0)

    def _keep_usage(self, usage) -> None:
        if usage is not None:
            self.last_usage = (usage.prompt_tokens or 0, usage.completion_tokens or 0)

    def _messages(self, messages: list[Message], system: str) -> list[dict]:
        """OpenAI では、システムの指示もメッセージの1つとして先頭に置く"""
        return ([{"role": "system", "content": system}]
                + [{"role": m.role, "content": m.content} for m in messages])

    async def generate(self, messages: list[Message], system: str) -> str:
        response = await with_retry(lambda: self.client.chat.completions.create(
            model=self.model, messages=self._messages(messages, system)))
        self._keep_usage(response.usage)
        return response.choices[0].message.content or ""

    async def stream(self, messages: list[Message], system: str):
        async def first_piece():
            chunks = await self.client.chat.completions.create(
                model=self.model, messages=self._messages(messages, system),
                stream=True, stream_options={"include_usage": True})
            iterator = chunks.__aiter__()
            return iterator, await iterator.__anext__()

        iterator, chunk = await with_retry(first_piece)
        while True:
            self._keep_usage(getattr(chunk, "usage", None))
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
            try:
                chunk = await iterator.__anext__()
            except StopAsyncIteration:
                break

    async def embed(self, texts: list[str], kind: str = "document") -> list[list[float]]:
        response = await with_retry(lambda: self.client.embeddings.create(
            model=self.embed_model, input=texts, dimensions=768))
        return [d.embedding for d in response.data]

    # ----------------------------------------------------------------
    def _items(self, items: list, system: str) -> list[dict]:
        out: list[dict] = [{"role": "system", "content": system}]
        for m in items:
            if isinstance(m, Reply):
                out.append(m.raw)
            elif isinstance(m, ToolResult):
                out.append({"role": "tool", "tool_call_id": m.call.id,
                            "content": json.dumps(m.result, ensure_ascii=False)})
            else:
                out.append({"role": m.role, "content": m.content})
        return out

    async def generate_with_tools(self, items: list, tools: list, system: str) -> Reply:
        specs = [{"type": "function", "function": {
            "name": t.name, "description": t.description,
            "parameters": t.args.model_json_schema()}} for t in tools]
        response = await with_retry(lambda: self.client.chat.completions.create(
            model=self.model, messages=self._items(items, system), tools=specs))
        self._keep_usage(response.usage)
        msg = response.choices[0].message
        calls = []
        for tc in msg.tool_calls or []:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            calls.append(ToolCall(id=tc.id, name=tc.function.name, args=args))
        raw = {"role": "assistant", "content": msg.content or ""}
        if msg.tool_calls:
            raw["tool_calls"] = [{"id": tc.id, "type": "function",
                                  "function": {"name": tc.function.name,
                                               "arguments": tc.function.arguments}}
                                 for tc in msg.tool_calls]
        return Reply(text=msg.content or "", tool_calls=calls, raw=raw)

    async def extract(self, text: str, schema: type[BaseModel], system: str) -> BaseModel:
        response = await with_retry(lambda: self.client.chat.completions.create(
            model=self.model, messages=self._messages([Message(role="user", content=text)], system),
            response_format={"type": "json_schema", "json_schema": {
                "name": schema.__name__, "schema": schema.model_json_schema()}}))
        self._keep_usage(response.usage)
        try:
            return schema.model_validate_json(response.choices[0].message.content or "")
        except ValidationError:
            raise LLMError("AI の答えを、決まった形で読み取れませんでした")
