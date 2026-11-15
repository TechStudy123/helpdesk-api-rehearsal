"""Gemini の担当クラス（google-genai の SDK を使う）"""
from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError

from app.llm.base import LLMError, Message, Reply, ToolCall, ToolResult
from app.retry import with_retry

# SDK が関数を自動で実行する機能（AFC）は使わない。指定しないと、呼ぶたびに注意のメッセージが出る
NO_AFC = types.AutomaticFunctionCallingConfig(disable=True)


class GeminiClient:
    def __init__(self, model: str, api_key: str,
                 embed_model: str = "gemini-embedding-2"):
        self.model = model
        self.embed_model = embed_model
        self.client = genai.Client(api_key=api_key)
        self.last_usage = (0, 0)

    def _keep_usage(self, usage) -> None:
        """レスポンスに含まれる、使ったトークンの数を覚えておく"""
        if usage is not None:
            self.last_usage = (usage.prompt_token_count or 0, usage.candidates_token_count or 0)

    def _contents(self, messages: list) -> list[types.Content]:
        """共通の形のメッセージを、Gemini の形（role は user / model）に並べ替える"""
        contents: list[types.Content] = []
        for m in messages:
            if isinstance(m, Reply):
                # 道具を提案した Gemini の答えは、元の形のまま送り返す
                # （Gemini 3 は、答えに含まれる「思考の署名」が送り返されることを求める）
                contents.append(m.raw)
            elif isinstance(m, ToolResult):
                # 道具の結果は function_response として、利用者の側から送る
                part = types.Part(function_response=types.FunctionResponse(
                    id=m.call.id, name=m.call.name, response=m.result))
                last = contents[-1] if contents else None
                if last and last.role == "user" and last.parts[0].function_response:
                    last.parts.append(part)        # 同じ回の結果は、1つにまとめる
                else:
                    contents.append(types.Content(role="user", parts=[part]))
            else:
                contents.append(types.Content(role="model" if m.role == "assistant" else "user",
                                              parts=[types.Part(text=m.content)]))
        return contents

    def _config(self, system: str) -> types.GenerateContentConfig:
        return types.GenerateContentConfig(system_instruction=system, automatic_function_calling=NO_AFC)

    async def generate(self, messages: list[Message], system: str) -> str:
        response = await with_retry(lambda: self.client.aio.models.generate_content(
            model=self.model, contents=self._contents(messages),
            config=self._config(system)))
        self._keep_usage(response.usage_metadata)
        return response.text or ""

    async def stream(self, messages: list[Message], system: str):
        async def first_piece():
            # 最初のかけらを受け取るまでを「やり直しの対象」にする
            # （送り始めたあとは、やり直せない）
            chunks = await self.client.aio.models.generate_content_stream(
                model=self.model, contents=self._contents(messages),
                config=self._config(system))
            iterator = chunks.__aiter__()
            return iterator, await iterator.__anext__()

        iterator, chunk = await with_retry(first_piece)
        self._keep_usage(chunk.usage_metadata)
        if chunk.text:
            yield chunk.text
        async for chunk in iterator:
            self._keep_usage(chunk.usage_metadata)
            if chunk.text:
                yield chunk.text

    async def embed(self, texts: list[str], kind: str = "document") -> list[list[float]]:
        """文章をベクトル（768個の数値の並び）に変える。kind は document（資料）か query（質問）"""
        if kind == "query":
            texts = [f"task: search result | query: {t}" for t in texts]
        else:
            texts = [f"title: none | text: {t}" for t in texts]
        contents = [types.Content(parts=[types.Part(text=t)]) for t in texts]
        response = await with_retry(lambda: self.client.aio.models.embed_content(
            model=self.embed_model, contents=contents,
            config=types.EmbedContentConfig(output_dimensionality=768)))
        return [e.values for e in response.embeddings]

    # ----------------------------------------------------------------
    async def generate_with_tools(self, items: list, tools: list, system: str) -> Reply:
        """道具の一覧（名前・説明・引数の形）を渡して呼ぶ。答えか、道具を使う提案が返る"""
        declarations = [types.FunctionDeclaration(
            name=t.name, description=t.description,
            parameters_json_schema=t.args.model_json_schema()) for t in tools]
        config = types.GenerateContentConfig(
            system_instruction=system,
            tools=[types.Tool(function_declarations=declarations)],
            automatic_function_calling=NO_AFC)      # 道具を実行するかどうかは、アプリの側で決める
        response = await with_retry(lambda: self.client.aio.models.generate_content(
            model=self.model, contents=self._contents(items), config=config))
        self._keep_usage(response.usage_metadata)
        if not response.candidates or response.candidates[0].content is None:
            return Reply(text="")
        content = response.candidates[0].content
        calls = [ToolCall(id=fc.id, name=fc.name or "", args=dict(fc.args or {}))
                 for fc in (response.function_calls or [])]
        text = "".join(p.text for p in content.parts or [] if p.text and not p.thought)
        return Reply(text=text, tool_calls=calls, raw=content)

    async def extract(self, text: str, schema: type[BaseModel], system: str) -> BaseModel:
        """構造化出力: 答えを、schema で決めた形の JSON で返させ、Pydantic でチェックする"""
        config = types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_json_schema=schema.model_json_schema(),
            automatic_function_calling=NO_AFC)
        response = await with_retry(lambda: self.client.aio.models.generate_content(
            model=self.model, contents=text, config=config))
        self._keep_usage(response.usage_metadata)
        try:
            return schema.model_validate_json(response.text or "")
        except ValidationError:
            raise LLMError("AI の答えを、決まった形で読み取れませんでした")
