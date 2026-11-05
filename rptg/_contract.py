"""Обёртки условий: requires на входе и ensures на выходе каждой операции (LOGIC §5, Э2).

Модуль общий для всего сгенерированного кода. Условие, упавшее при вычислении, — нарушение, а не
сбой (LOGIC §4.4): деление на ноль, поле у null, индекс вне списка делают условие ложным.
Первое нарушение называет виновного (LOGIC §5, Э6): requires — вызывающая схема, ensures — сама
операция.
"""


class ContractError(Exception):
    """Нарушено условие операции op: side — requires или ensures, cond — текст условия на CL."""

    def __init__(self, op, side, cond, why):
        super().__init__(f"{op}: {side} «{cond}» — {why}")
        self.op, self.side, self.cond, self.why = op, side, cond, why


def check(op, side, conds):
    """Проверить условия по порядку; conds — пары (текст CL, функция без аргументов)."""
    for text, test in conds:
        try:
            ok = test()
        except Exception as e:  # ошибка вычисления условия — нарушение условия (LOGIC §4.4)
            raise ContractError(op, side, text, f"{type(e).__name__}: {e}") from e
        if ok is not True:
            raise ContractError(op, side, text, "ложно" if ok is False else f"не логическое: {ok!r}")
