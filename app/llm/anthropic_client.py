"""Claude の担当クラス（任意。Anthropic の API キーを持っている人向け）"""
import json

from anthropic import AsyncAnthropic
from pydantic import BaseModel, ValidationError

from app.llm.base import LLMError, Message, Reply, ToolCall, ToolResult
from app.retry import with_retry


class AnthropicClient:
    def __init__(self, model: str, api_key: str):
        self.model = model
        self.client = AsyncAnthropic(api_key=api_key)
        self.last_usage = (0, 0)

    def _messages(self, messages: list[Message]) -> list[dict]:
        return [{"role": m.role, "content": m.content} for m in messages]

    async def generate(self, messages: list[Message], system: str) -> str:
        # Claude では、システムの指示はメッセージではなく system という別の引数で渡す
        response = await with_retry(lambda: self.client.messages.create(
            model=self.model, max_tokens=1024, system=system,
            messages=self._messages(messages)))
        self.last_usage = (response.usage.input_tokens, response.usage.output_tokens)
        return "".join(b.text for b in response.content if b.type == "text")

    async def stream(self, messages: list[Message], system: str):
        async def first_piece():
            events = await self.client.messages.create(
                model=self.model, max_tokens=1024, system=system,
                messages=self._messages(messages), stream=True)
            iterator = events.__aiter__()
            return iterator, await iterator.__anext__()

        iterator, event = await with_retry(first_piece)
        input_tokens = 0
        while True:
            if event.type == "message_start":
                input_tokens = event.message.usage.input_tokens
            elif event.type == "message_delta":
                self.last_usage = (input_tokens, event.usage.output_tokens)
            if event.type == "content_block_delta" and event.delta.type == "text_delta":
                yield event.delta.text
            try:
                event = await iterator.__anext__()
            except StopAsyncIteration:
                break

    async def embed(self, texts: list[str], kind: str = "document") -> list[list[float]]:
        raise LLMError("Claude には埋め込みの API がありません。埋め込みは Gemini か OpenAI を使ってください")

    # ----------------------------------------------------------------
    def _items(self, items: list) -> list[dict]:
        out: list[dict] = []
        for m in items:
            if isinstance(m, Reply):
                out.append({"role": "assistant", "content": m.raw})
            elif isinstance(m, ToolResult):
                block = {"type": "tool_result", "tool_use_id": m.call.id,
                         "content": json.dumps(m.result, ensure_ascii=False)}
                last = out[-1] if out else None
                if last and last["role"] == "user" and isinstance(last["content"], list):
                    last["content"].append(block)      # 同じ回の結果は、1つにまとめる
                else:
                    out.append({"role": "user", "content": [block]})
            else:
                out.append({"role": m.role, "content": m.content})
        return out

    async def generate_with_tools(self, items: list, tools: list, system: str) -> Reply:
        specs = [{"name": t.name, "description": t.description,
                  "input_schema": t.args.model_json_schema()} for t in tools]
        response = await with_retry(lambda: self.client.messages.create(
            model=self.model, max_tokens=1024, system=system,
            messages=self._items(items), tools=specs))
        self.last_usage = (response.usage.input_tokens, response.usage.output_tokens)
        calls = [ToolCall(id=b.id, name=b.name, args=dict(b.input))
                 for b in response.content if b.type == "tool_use"]
        text = "".join(b.text for b in response.content if b.type == "text")
        raw = [b.model_dump(exclude_none=True) for b in response.content]
        return Reply(text=text, tool_calls=calls, raw=raw)

    async def extract(self, text: str, schema: type[BaseModel], system: str) -> BaseModel:
        # Claude では「記録する」という道具を1つだけ渡し、必ずそれを使わせて、決まった形を受け取る
        response = await with_retry(lambda: self.client.messages.create(
            model=self.model, max_tokens=1024, system=system,
            messages=[{"role": "user", "content": text}],
            tools=[{"name": "record", "description": "読み取った内容を記録する",
                    "input_schema": schema.model_json_schema()}],
            tool_choice={"type": "tool", "name": "record"}))
        self.last_usage = (response.usage.input_tokens, response.usage.output_tokens)
        for b in response.content:
            if b.type == "tool_use":
                try:
                    return schema.model_validate(b.input)
                except ValidationError:
                    break
        raise LLMError("AI の答えを、決まった形で読み取れませんでした")
