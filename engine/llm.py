"""Optional API backend for the judgment phases. The skill's DEFAULT engine is host-agent mode (the
host CLI spawns subagents with its own model, no key needed); this module is only used when the operator
opts into API mode. It is provider-agnostic: point it at DeepSeek, OpenAI, Anthropic, OpenRouter, a
local server, or any OpenAI-compatible endpoint.

Config (all via env or a gitignored .env in the skill root or the working folder):
  LLM_PROVIDER   deepseek | openai | anthropic | openai-compatible   (inferred from which key is set)
  LLM_API_KEY    the key (or a provider-specific one: DEEPSEEK_API_KEY / OPENAI_API_KEY / ANTHROPIC_API_KEY)
  LLM_BASE_URL   override the endpoint base
  LLM_MODEL      the model id
  LLM_TIMEOUT    idle (no-bytes) socket timeout, seconds (default 150)
  LLM_DEADLINE   wall-clock cap per request, seconds (default 300)

No key ships with the skill. Concurrent (ThreadPool), streaming, robust JSON extraction with retries.
"""
import os, re, sys, json, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

# provider presets: base endpoint, wire transport, a sensible default model, and which env keys to try
PRESETS = {
    "deepseek":          {"base": "https://api.deepseek.com",   "transport": "openai",    "model": "deepseek-v4-pro",      "keys": ["DEEPSEEK_API_KEY"]},
    "openai":            {"base": "https://api.openai.com/v1",  "transport": "openai",    "model": "gpt-5.2",              "keys": ["OPENAI_API_KEY"]},
    "anthropic":         {"base": "https://api.anthropic.com",  "transport": "anthropic", "model": "claude-sonnet-4-6",    "keys": ["ANTHROPIC_API_KEY"]},
    "openai-compatible": {"base": None,                          "transport": "openai",    "model": None,                   "keys": []},
}
_KEY_ENVS = ["LLM_API_KEY", "DEEPSEEK_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"]


def _infer_provider():
    p = os.environ.get("LLM_PROVIDER")
    if p:
        return p
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    return "deepseek"  # backward-compatible default


PROVIDER = _infer_provider()
_P = PRESETS.get(PROVIDER, PRESETS["openai-compatible"])
TRANSPORT = _P["transport"]
BASE = (os.environ.get("LLM_BASE_URL") or os.environ.get("DEEPSEEK_BASE_URL") or _P["base"] or "").rstrip("/")
# model: explicit override, else legacy DeepSeek vars (so old .env files still work), else preset default
MODEL_REASONER = (os.environ.get("LLM_MODEL") or os.environ.get("DEEPSEEK_REASONER_MODEL")
                  or os.environ.get("DEEPSEEK_CHAT_MODEL") or _P["model"])
MODEL_CHAT = os.environ.get("LLM_CHAT_MODEL") or os.environ.get("DEEPSEEK_CHAT_MODEL") or MODEL_REASONER

_TIMEOUT = float(os.environ.get("LLM_TIMEOUT") or os.environ.get("DEEPSEEK_TIMEOUT", "150"))
# Wall-clock DEADLINE per request: the idle timeout only fires on TRUE silence. A reasoning model can
# stream reasoning/keepalive bytes that keep the socket "active" while emitting no answer tokens, so the
# idle timer never trips and the worker wedges. This cap is checked between SSE lines and abandons such a
# stream so retry/backoff can proceed.
_DEADLINE = float(os.environ.get("LLM_DEADLINE") or os.environ.get("DEEPSEEK_DEADLINE", "300"))


def _load_key():
    for name in _KEY_ENVS:
        if os.environ.get(name):
            return os.environ[name]
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for envpath in [os.path.join(os.environ.get("AUDIT_WORKDIR", ""), ".env"), os.path.join(here, ".env")]:
        if envpath and os.path.exists(envpath):
            for line in open(envpath):
                line = line.strip()
                for name in _KEY_ENVS:
                    if line.startswith(name + "="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("ERROR: no API key found. Set LLM_API_KEY (or DEEPSEEK_/OPENAI_/ANTHROPIC_API_KEY) in env or "
             ".env, OR use the default host-agent mode (no key needed). See engine/README.md.")


_KEY = None
def key():
    global _KEY
    if _KEY is None:
        _KEY = _load_key()
    return _KEY


def _request(payload, headers, url):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST", headers=headers)
    return urllib.request.urlopen(req, timeout=_TIMEOUT)


def _stream_read(resp, pick):
    """Read an SSE stream; pick(json_event) -> text piece or None. Enforces the wall-clock deadline."""
    out, deadline, saw = [], time.monotonic() + _DEADLINE, False
    for raw in resp:
        if time.monotonic() > deadline:
            try: resp.close()
            except Exception: pass
            if saw:
                break
            raise TimeoutError(f"stream wall-clock deadline {_DEADLINE:.0f}s exceeded with no content")
        line = raw.decode("utf-8", "replace").strip()
        if not line or not line.startswith("data:"):
            continue
        chunk = line[5:].strip()
        if chunk == "[DONE]":
            break
        try:
            piece = pick(json.loads(chunk))
        except Exception:
            continue
        if piece:
            out.append(piece); saw = True
    return "".join(out)


def _post_openai(messages, model, json_mode, stream, max_tokens, temperature):
    payload = {"model": model, "messages": messages, "max_tokens": max_tokens,
               "temperature": temperature, "stream": stream}
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    headers = {"Content-Type": "application/json", "Authorization": "Bearer " + key()}
    resp = _request(payload, headers, BASE + "/chat/completions")
    if not stream:
        return json.loads(resp.read().decode())["choices"][0]["message"]["content"]
    return _stream_read(resp, lambda j: (j.get("choices") or [{}])[0].get("delta", {}).get("content"))


def _post_anthropic(messages, model, json_mode, stream, max_tokens, temperature):
    sys_txt = " ".join(m["content"] for m in messages if m.get("role") == "system")
    msgs = [{"role": ("assistant" if m["role"] == "assistant" else "user"), "content": m["content"]}
            for m in messages if m.get("role") != "system"]
    payload = {"model": model, "max_tokens": max_tokens, "temperature": temperature,
               "messages": msgs, "stream": stream}
    if sys_txt:
        payload["system"] = sys_txt + ("\nReturn only one valid JSON object." if json_mode else "")
    headers = {"Content-Type": "application/json", "x-api-key": key(), "anthropic-version": "2023-06-01"}
    resp = _request(payload, headers, BASE + "/v1/messages")
    if not stream:
        body = json.loads(resp.read().decode())
        return "".join(b.get("text", "") for b in body.get("content", []) if b.get("type") == "text")
    return _stream_read(resp, lambda j: (j.get("delta", {}) or {}).get("text") if j.get("type") == "content_block_delta" else None)


def chat(messages, model=None, json_mode=False, stream=True, max_tokens=8000, temperature=0.2, retries=4):
    """One completion. Returns raw text. Routes to the configured provider transport."""
    model = model or MODEL_REASONER
    post = _post_anthropic if TRANSPORT == "anthropic" else _post_openai
    last = None
    for attempt in range(retries):
        try:
            return post(messages, model, json_mode, stream, max_tokens, temperature)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last = e
            if getattr(e, "code", None) == 400 and json_mode:
                json_mode = False  # endpoint rejects json mode; retry without it
            time.sleep(min(2 ** attempt * 2, 30))
        except Exception as e:
            last = e
            time.sleep(min(2 ** attempt * 2, 20))
    raise RuntimeError(f"chat failed after {retries} tries ({PROVIDER}/{model}): {last}")


def extract_json(text):
    """Pull the first balanced JSON object from text (handles prose + ```json fences)."""
    if not text:
        raise ValueError("empty response")
    t = text.strip()
    if "```" in t:
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", t, re.S)
        if m:
            t = m.group(1)
    start = t.find("{")
    if start < 0:
        raise ValueError("no JSON object in response")
    depth = instr = esc = 0
    for i in range(start, len(t)):
        c = t[i]
        if instr:
            if esc: esc = 0
            elif c == "\\": esc = 1
            elif c == '"': instr = 0
        else:
            if c == '"': instr = 1
            elif c == "{": depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return json.loads(t[start:i + 1])
    return json.loads(t[start:])


def chat_json(messages, model=None, stream=True, max_tokens=8000, temperature=0.2, retries=4):
    """Completion that must return a JSON object. Retries with a repair nudge on parse failure."""
    msgs = list(messages)
    last = None
    for attempt in range(retries):
        try:
            txt = chat(msgs, model=model, json_mode=True, stream=stream,
                       max_tokens=max_tokens, temperature=temperature, retries=2)
            return extract_json(txt)
        except (ValueError, json.JSONDecodeError) as e:
            last = e
            msgs = list(messages) + [{"role": "user",
                "content": "Your previous reply was not valid JSON. Return ONLY one valid JSON object, nothing else."}]
            temperature = 0.0
        except Exception as e:
            last = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"chat_json failed: {last}")


def map_concurrent(items, fn, workers=16, label="task", on_done=None):
    """Run fn(item) over items with a thread pool. Returns list aligned to items (None on failure)."""
    results = [None] * len(items)
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(fn, it): i for i, it in enumerate(items)}
        for fut in as_completed(futs):
            i = futs[fut]
            try:
                results[i] = fut.result()
            except Exception as e:
                results[i] = {"_error": str(e)}
            done += 1
            print(f"  [{label}] {done}/{len(items)}", flush=True)
            if on_done:
                on_done(i, results[i])
    return results
