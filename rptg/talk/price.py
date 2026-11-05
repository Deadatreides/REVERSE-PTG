"""Лист rptg.talk.price — цена ответа (ARCHITECTURE §5.3, LOGIC §11).

Функции приняты по карточке design/rptg.talk.yaml; обвязку пишет скрипт. Десятичная арифметика —
точная, в целых с общим масштабом: модуль decimal узлу не разрешён. Запись в кэш у Anthropic
идёт по цене входа — надбавки за запись в Price нет.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rptg._types import Decimal, Operator, RawAnswer


def cost(answer: RawAnswer, operator: Operator) -> Decimal:
    """(вход × input + выход × output + из кэша × cache) / 10⁶; нет цены кэша — по цене входа. Запись
    десятичная без хвостовых нулей, ноль — «0»."""
    def parse(text):
        whole, _, frac = text.lstrip("-").partition(".")
        return (-1 if text.startswith("-") else 1) * int(whole + frac), len(frac)

    prices = operator.prices
    rates = [parse(prices.input), parse(prices.output), parse(prices.cache if prices.cache is not None else prices.input)]
    scale = max(s for _, s in rates)
    total = sum(n * 10 ** (scale - s) * k
                for (n, s), k in zip(rates, (answer.input_tokens, answer.output_tokens, answer.cache_read_tokens)))
    scale += 6  # цены — за миллион токенов
    digits = str(abs(total)).rjust(scale + 1, "0")
    whole, frac = digits[:-scale], digits[-scale:].rstrip("0")
    return ("-" if total < 0 else "") + whole + ("." + frac if frac else "") if total else "0"
