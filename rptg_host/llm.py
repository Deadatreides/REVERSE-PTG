"""Адаптер моделей (ARCHITECTURE §5.1): ProviderRequest ядра → вызов официального SDK → сырой ответ JSON.

Договор с ядром записан в разложении talk (design/rptg.talk.yaml): payload — именованные аргументы вызова
SDK; ключей в запросе нет — их добавляет только этот модуль, из переменных окружения, и никуда не пишет.
Сырой ответ разбирает ядро (read_answer): anthropic, openai-подобные, llamacpp — model_dump(mode="json")
или словарь; google — JSON REST (camelCase). SDK грузятся лениво: без одного работают остальные.

Ключи: RPTG_KEY_<ОПЕРАТОР> (имя оператора заглавными), иначе по поставщику — ANTHROPIC_API_KEY,
OPENAI_API_KEY, OPENROUTER_API_KEY, GEMINI_API_KEY; у openai_compatible ключ не обязателен.
"""
import inspect
import json
import os

KEYS = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY", "openrouter": "OPENROUTER_API_KEY", "google": "GEMINI_API_KEY"}
_LOCAL = {}


def key(provider, operator):
    own = "RPTG_KEY_" + operator["id"].upper().replace("-", "_")
    found = os.environ.get(own) or os.environ.get(KEYS.get(provider, ""), "")
    if not found and provider in KEYS:
        raise RuntimeError(f"нет ключа {KEYS[provider]} (или {own}) в окружении для оператора {operator['id']}")
    return found or "not-needed"


def send(task, request, operator):
    """Один вызов модели; task не используется (его берут подмены в тестах)."""
    provider, payload = request["provider"], dict(request["payload"])
    if provider == "anthropic":
        import anthropic
        with anthropic.Anthropic(api_key=key(provider, operator)).messages.stream(**payload) as stream:
            return stream.get_final_message().model_dump(mode="json")
    if provider in ("openai", "openrouter", "openai_compatible"):
        import openai
        client = openai.OpenAI(api_key=key(provider, operator), base_url=request.get("endpoint"))
        return client.chat.completions.create(**payload).model_dump(mode="json")
    if provider == "google":
        from google import genai
        response = genai.Client(api_key=key(provider, operator)).models.generate_content(**payload)
        return response.model_dump(mode="json", by_alias=True, exclude_none=True)
    if provider == "llamacpp":
        return local(payload, operator)
    raise ValueError(f"поставщик {provider} не поддержан")


def split(payload, llama):
    """Параметры оператора для llama.cpp делятся по сигнатурам самой библиотеки: ключи, которые принимает
    только конструктор Llama (n_ctx, n_gpu_layers, chat_format, flash_attn…), — загрузке модели, остальное —
    create_chat_completion (там нет **kwargs: лишний ключ — TypeError). seed есть у обоих и остаётся вызову.
    n_ctx по умолчанию — 8192: у библиотеки 512, промпт задачи туда не входит."""
    load_only = (set(inspect.signature(llama.__init__).parameters) - set(inspect.signature(llama.create_chat_completion).parameters)
                 - {"self", "model_path", "kwargs"})
    call = dict(payload)
    return {"n_ctx": 8192, "verbose": False, **{k: call.pop(k) for k in list(call) if k in load_only}}, call


def model(payload, operator):
    """Модель llama.cpp и аргументы вызова: модель грузится один раз на путь и набор параметров загрузки."""
    from llama_cpp import Llama
    load, call = split(payload, Llama)
    name = operator["model"] + json.dumps(load, sort_keys=True)
    return _LOCAL.get(name) or _LOCAL.setdefault(name, Llama(model_path=operator["model"], **load)), call


GBNF_ESCAPES = set('xuUtrn\\"[]')


def gbnf(text):
    """Перевод схемы в грамматику (json_schema_to_gbnf) переносит экранирование из регулярных выражений — шаблон
    NodeId даёт «\\.», — а разборщик llama.cpp знает только \\x \\u \\U \\t \\r \\n \\\\ \\" \\[ \\]. Незнакомое
    экранирование → \\xHH (\\uHHHH): тот же символ и в строке, и в классе символов."""
    out, i = [], 0
    while i < len(text):
        if text[i] == "\\" and i + 1 < len(text):
            nxt = text[i + 1]
            code = ord(nxt)
            out.append(text[i:i + 2] if nxt in GBNF_ESCAPES else f"\\x{code:02X}" if code < 0x100 else f"\\u{code:04X}")
            i += 2
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def grammar(llama, text):
    """Грамматика проходит разборщик самой llama.cpp до выборки: при ошибке библиотека лишь печатает её и ставит
    пустой сэмплер, и выборка падает по нулевому указателю — на Windows OSError, на Linux процесс целиком (живой
    смоук 07.10.2026). Здесь ошибка — исключение и пауза круга."""
    import llama_cpp
    sampler = llama_cpp.llama_sampler_init_grammar(llama._model.vocab, text.encode("utf-8"), b"root")
    if not sampler:
        raise ValueError("грамматика не разбирается llama.cpp — см. сообщение разборщика выше")
    llama_cpp.llama_sampler_free(sampler)
    return llama_cpp.LlamaGrammar.from_string(text, verbose=False)


def local(payload, operator):
    """llama.cpp в процессе. grammar — текст GBNF; response_format.schema переводится в грамматику здесь, а не
    в библиотеке: та при неудаче перевода молча берёт «любой JSON» (ARCHITECTURE §5.1). Любая грамматика
    проверяется разборщиком llama.cpp до выборки."""
    from llama_cpp.llama_grammar import json_schema_to_gbnf
    model_, payload = model(payload, operator)
    if isinstance(payload.get("grammar"), str):
        payload["grammar"] = grammar(model_, payload["grammar"])
    schema = (payload.pop("response_format", None) or {}).get("schema")
    if schema:
        payload["grammar"] = grammar(model_, gbnf(json_schema_to_gbnf(json.dumps(schema))))
    return model_.create_chat_completion(**payload)
