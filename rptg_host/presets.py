"""Готовые наборы моделей для `rptg new` (ARCHITECTURE §8): claude, mixed, local.

Цены не выдумываются: у Claude — открытые данные Anthropic (ниже, с датой сверки); у локальных моделей —
0 (свой компьютер, деньги не тратятся); у заготовок без модели («ВПИШИТЕ-…») — «0», пока пользователь не
впишет модель и её цены — `new` называет такие операторы. Пределы, маршрутизация и ремонт — значения
примера корня (design/rptg.yaml) и LOGIC §5–§7.
"""
import copy

LIMITS = {"max_depth": 8, "max_children": 7, "final_max_ops": 6, "final_max_lines": 40, "max_complexity": 10, "k_lists": 3,
          "z3_rlimit": 5000000, "hypothesis_examples": 200}
ROUTING = {"target": 0.8, "n_min": 10, "prior_bands": {"designer": [45, 70], "implementer": [30, 55, 75]}, "adapt": False, "explore": 0.0}
FREE = {"input": "0", "output": "0"}
# У Anthropic max_tokens обязателен (ARCHITECTURE §5.1), а talk своих умолчаний не вводит. Здесь — потолок
# вывода модели при потоке по документации Anthropic: Opus 5.5 и Sonnet 5.5 — 128K, Haiku 4.5 — 64K. Ответ не
# обрезается раньше модели (обрезанный — потерянная попытка), а платится только написанное; в лимит выдачи в
# минуту max_tokens не входит (platform.claude.com/docs/en/api/rate-limits).
CEILING = {"claude-opus-5-5": 128000, "claude-sonnet-5-5": 128000, "claude-haiku-4-5-20251001": 64000}
# Цены за миллион токенов, USD — platform.claude.com/docs/en/about-claude/pricing, сверено 04.10.2026: вход, выход,
# чтение из кэша (у Opus 5.5 — 0,05 входа, у остальных — 0,1). Запись в кэш (1,25 входа) Price не знает и
# считает по цене входа (talk, Т-6) — расход по записи в кэш занижен на четверть её цены.
PRICES_AS_OF = "04.10.2026"
PRICES = {"claude-opus-5-5": {"input": "4", "output": "20", "cache": "0.20"},
          "claude-sonnet-5-5": {"input": "2", "output": "10", "cache": "0.20"},
          "claude-haiku-4-5-20251001": {"input": "1", "output": "5", "cache": "0.10"}}


def op(id_, provider, model, mode="json_schema", steps="combined", **more):
    return {"id": id_, "provider": provider, "model": model, "output_mode": mode, "steps": steps, "prices": dict(FREE),
            "prompt_version": "p1", **more}


def claude(id_, model):
    return op(id_, "anthropic", model, params={"max_tokens": CEILING[model]}, prices=dict(PRICES[model]))


PRESETS = {
    "claude": {"roles": {"architect": ["opus"], "designer": ["sonnet", "opus"], "implementer": ["haiku", "sonnet", "opus"]},
               "operators": {"opus": claude("opus", "claude-opus-5-5"), "sonnet": claude("sonnet", "claude-sonnet-5-5"),
                             "haiku": claude("haiku", "claude-haiku-4-5-20251001")}},
    "mixed": {"roles": {"architect": ["opus"], "designer": ["gemini", "opus"], "implementer": ["local", "mini", "gemini", "opus"]},
              "operators": {"opus": claude("opus", "claude-opus-5-5"),
                            "gemini": op("gemini", "google", "ВПИШИТЕ-модель-gemini"),
                            "mini": op("mini", "openrouter", "ВПИШИТЕ/модель-openrouter"),
                            "local": op("local", "llamacpp", "ВПИШИТЕ-путь-к-модели.gguf", mode="grammar", steps="split")}},
    "local": {"roles": {"architect": ["local"], "designer": ["local"], "implementer": ["local"]},
              "operators": {"local": op("local", "llamacpp", "ВПИШИТЕ-путь-к-модели.gguf", mode="grammar", steps="split")}},
}


def config(name):
    return copy.deepcopy({"limits": LIMITS, "routing": ROUTING, "repair": {"per_rung": 1, "form_retries": 2}, "overrides": {},
                          **PRESETS[name]})
