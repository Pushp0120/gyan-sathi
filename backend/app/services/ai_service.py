"""AI service: provider abstraction with NVIDIA NIM (OpenAI-compatible) provider."""
import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Generator

import requests

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _post_json(session: "requests.Session", url: str, headers: dict, payload: dict, **kw):
    """POST with raw UTF-8 body. requests' json= uses ensure_ascii=True, which
    turns every Gujarati char into a 6-byte \\uXXXX escape and triples payload
    size (breaks Groq's request-size cap)."""
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {**headers, "Content-Type": "application/json"}
    return session.post(url, data=body, headers=headers, **kw)


class AIProvider(ABC):
    name = "base"

    @abstractmethod
    def chat(self, messages: list[dict], model: str | None = None,
             temperature: float = 0.3, max_tokens: int = 1500,
             stream: bool = False) -> Generator[str, None, None] | str:
        ...

    @abstractmethod
    def embed(self, texts: list[str], input_type: str = "query") -> list[list[float]]:
        ...


class NVIDIAProvider(AIProvider):
    """NVIDIA NIM — OpenAI-compatible endpoint (integrate.api.nvidia.com/v1)."""
    name = "nvidia"

    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._session = requests.Session()

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 1500,
        stream: bool = False,
    ):
        model = model or settings.ai_model
        payload: dict = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }
        # Nemotron models: disable thinking so content is clean student-facing text
        if "nemotron" in model:
            payload["chat_template_kwargs"] = {"thinking": False}
        url = f"{self.base_url}/chat/completions"
        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                if stream:
                    return self._stream_response(url, payload)
                resp = _post_json(
                    self._session, url, self._headers(), payload, timeout=settings.ai_request_timeout
                )
                # NVIDIA free tier also signals transient overload with plain 500s
                if resp.status_code in (429, 500, 502, 503, 504):
                    last_exc = RuntimeError(f"AI HTTP {resp.status_code}")
                    time.sleep(1.5 * (attempt + 1))
                    continue
                resp.raise_for_status()
                data = resp.json()
                # Some errors arrive as HTTP 200 with an error body instead of an error status
                if isinstance(data, dict) and data.get("error"):
                    last_exc = RuntimeError(f"AI HTTP 200 error: {str(data['error'])[:150]}")
                    time.sleep(1.5 * (attempt + 1))
                    continue
                content = data["choices"][0]["message"].get("content") or ""
                usage = data.get("usage", {}) or {}
                return {"content": content, "tokens": usage.get("total_tokens", 0)}
            except requests.HTTPError as exc:
                raise exc
            except requests.Timeout as exc:
                last_exc = exc
                time.sleep(1.5 * (attempt + 1))
            except requests.RequestException as exc:
                last_exc = exc
                time.sleep(1.5 * (attempt + 1))
        if isinstance(last_exc, requests.Timeout):
            raise TimeoutError("AI સેવા ધીમી છે. થોડા સમય પછી ફરી પ્રયાસ કરો.")
        raise RuntimeError("AI સેવા હાલમાં ઉપલબ્ધ નથી. થોડીવાર પછી ફરી પ્રયાસ કરો.")

    def _stream_response(self, url: str, payload: dict) -> Generator[str, None, None]:
        """Yield content deltas from an SSE stream.

        NVIDIA's free tier sometimes returns HTTP 200 whose stream carries an
        in-band error (e.g. ResourceExhausted) and no content at all. While
        NOTHING has been yielded yet that is safe to retry; after partial
        content we must not retry (it would duplicate text)."""
        last_exc: Exception | None = None
        for attempt in range(3):
            pieces = 0
            err_msg = ""
            try:
                with _post_json(self._session, url, self._headers(), payload,
                                stream=True, timeout=(15, settings.ai_request_timeout)) as resp:
                    if resp.status_code in (429, 500, 502, 503, 504):
                        last_exc = RuntimeError(f"AI HTTP {resp.status_code}")
                        time.sleep(1.5 * (attempt + 1))
                        continue
                    resp.raise_for_status()
                    # SSE bodies carry no charset; requests would decode text/* as
                    # ISO-8859-1 and turn Gujarati into mojibake. Force UTF-8.
                    resp.encoding = "utf-8"
                    for line in resp.iter_lines(decode_unicode=True):
                        if not line or not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                        except json.JSONDecodeError:
                            continue
                        if isinstance(chunk, dict) and chunk.get("error"):
                            err_msg = str(chunk["error"].get("message", ""))[:200]
                            break
                        try:
                            delta = chunk["choices"][0].get("delta", {}) or {}
                            piece = delta.get("content")
                            if piece:
                                pieces += 1
                                yield piece
                        except (KeyError, IndexError):
                            continue
                if pieces:
                    return
                last_exc = RuntimeError(f"AI ખાલી જવાબ: {err_msg}" if err_msg else "AI ખાલી જવાબ")
            except requests.Timeout:
                last_exc = TimeoutError("AI સેવા ધીમી છે.")
            except Exception as exc:
                logger.exception("AI stream failed")
                last_exc = exc
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
        if isinstance(last_exc, TimeoutError):
            raise TimeoutError("AI સેવા ધીમી છે. થોડા સમય પછી ફરી પ્રયાસ કરો.")
        raise RuntimeError("AI સેવામાં સમસ્યા. થોડીવાર પછી ફરી પ્રયાસ કરો.") from last_exc

    def embed(self, texts: list[str], input_type: str = "query") -> list[list[float]]:
        """Embed texts. NVIDIA NIM limits ~8 inputs/call for some models; batch accordingly."""
        url = f"{self.base_url}/embeddings"
        out: list[list[float]] = []
        batch = 8
        for i in range(0, len(texts), batch):
            part = texts[i:i + batch]
            payload = {
                "input": part,
                "model": settings.ai_embedding_model,
                "input_type": input_type,
                "encoding_format": "float",
            }
            resp = _post_json(self._session, url, self._headers(), payload,
                              timeout=settings.ai_request_timeout)
            resp.raise_for_status()
            data = sorted(resp.json()["data"], key=lambda d: d["index"])
            out.extend(d["embedding"] for d in data)
        return out


class GroqProvider(AIProvider):
    """Groq — OpenAI-compatible endpoint (api.groq.com/openai/v1).
    Chat/quiz generation runs here (fast); embeddings still go to NVIDIA
    so query vectors match the ones stored in the database."""
    name = "groq"

    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "GyanSathi/1.0"})

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 1500,
        stream: bool = False,
    ):
        model = model or settings.ai_model
        payload: dict = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }
        # Reasoning models (gpt-oss): keep answers short-hygiene, low reasoning effort
        if "gpt-oss" in model:
            payload["reasoning_effort"] = "low"
        url = f"{self.base_url}/chat/completions"
        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                if stream:
                    return self._stream_response(url, payload)
                resp = _post_json(
                    self._session, url, self._headers(), payload, timeout=settings.ai_request_timeout
                )
                if resp.status_code in (429, 502, 503, 504):
                    last_exc = RuntimeError(f"AI HTTP {resp.status_code}")
                    time.sleep(1.5 * (attempt + 1))
                    continue
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"].get("content") or ""
                usage = data.get("usage", {}) or {}
                return {"content": content, "tokens": usage.get("total_tokens", 0)}
            except requests.HTTPError as exc:
                raise exc
            except requests.Timeout as exc:
                last_exc = exc
                time.sleep(1.5 * (attempt + 1))
            except requests.RequestException as exc:
                last_exc = exc
                time.sleep(1.5 * (attempt + 1))
        if isinstance(last_exc, requests.Timeout):
            raise TimeoutError("AI સેવા ધીમી છે. થોડા સમય પછી ફરી પ્રયાસ કરો.")
        raise RuntimeError("AI સેવા હાલમાં ઉપલબ્ધ નથી. થોડીવાર પછી ફરી પ્રયાસ કરો.")

    def _stream_response(self, url: str, payload: dict) -> Generator[str, None, None]:
        """Yield content deltas from an SSE stream."""
        try:
            with _post_json(self._session, url, self._headers(), payload,
                            stream=True, timeout=(15, settings.ai_request_timeout)) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines(decode_unicode=True):
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk["choices"][0].get("delta", {}) or {}
                        piece = delta.get("content")
                        if piece:
                            yield piece
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
        except requests.Timeout:
            raise TimeoutError("AI સેવા ધીમી છે.")
        except Exception as exc:
            logger.exception("AI stream failed")
            raise RuntimeError("AI સેવામાં સમસ્યા. થોડીવાર પછી ફરી પ્રયાસ કરો.") from exc

    def embed(self, texts: list[str], input_type: str = "query") -> list[list[float]]:
        """Embeddings stay on NVIDIA (vectors in DB were built with it)."""
        provider = NVIDIAProvider(settings.nvidia_api_key, settings.nvidia_base_url)
        return provider.embed(texts, input_type)


class MockProvider(AIProvider):
    """Offline provider for development without an API key."""
    name = "mock"

    def chat(self, messages, model=None, temperature=0.3, max_tokens=1500, stream=False):
        text = " ".join(m["content"] for m in messages if m["role"] == "user")[:200]
        reply = (
            "આ એક ડેમો (offline) જવાબ છે કારણ કે AI key સેટ કરેલી નથી.\n\n"
            f"તમારો પ્રશ્ન: {text}\n\n"
            "વાસ્તવિક જવાબ માટે backend/.env માં NVIDIA_API_KEY સેટ કરો."
        )
        if stream:
            def gen():
                for word in reply.split(" "):
                    yield word + " "
                    time.sleep(0.02)
            return gen()
        return {"content": reply, "tokens": 0}

    def embed(self, texts, input_type="query"):
        import hashlib

        vecs = []
        for t in texts:
            h = hashlib.sha256(t.encode("utf-8")).digest()
            vec = [b / 255.0 for b in (h * 8)[: settings.ai_embedding_dim]]
            vecs.append(vec[: settings.ai_embedding_dim])
        return vecs


_provider: AIProvider | None = None


def get_ai_provider() -> AIProvider:
    global _provider
    if _provider:
        return _provider
    if settings.ai_provider == "groq" and settings.groq_api_key:
        _provider = GroqProvider(settings.groq_api_key, settings.groq_base_url)
    elif settings.ai_provider == "nvidia" and settings.nvidia_api_key:
        _provider = NVIDIAProvider(settings.nvidia_api_key, settings.nvidia_base_url)
    else:
        logger.warning("Using MockProvider — set NVIDIA_API_KEY for real answers")
        _provider = MockProvider()
    return _provider


def choose_model(mode: str = "ask") -> str:
    """Route harder tasks to the advanced model."""
    if mode in ("quiz", "mcq", "important", "summary"):
        return settings.ai_model_advanced
    return settings.ai_model
