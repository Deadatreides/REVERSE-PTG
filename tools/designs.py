"""Чтение файлов разложения: rptg.yaml (корень) и rptg.*.yaml в одном каталоге.

Данные примеров (раздел fixtures) предков видны в файле разложения: загрузчик ставит разделы
fixtures корня и разложений всех предков узла — от корня вниз — перед текстом файла под ключами
shared_fixtures_0, shared_fixtures_1, … Так якоря YAML предков разрешаются, а свои данные у
разложения остаются своими. Предки берутся из того же каталога, что и файл, — самопроверка на
копии карты читает копию. Повтор имени якоря — ошибка самого PyYAML (duplicate anchor):
столкновение не пройдёт молча. Читают карту через этот модуль все: самопроверка, генератор
обвязки, затравка Э1 и тесты.
"""
import re
from pathlib import Path

import yaml

DESIGN = Path(__file__).resolve().parent.parent / "design"


def fixtures_block(text, key):
    """Раздел fixtures как текст YAML под ключом key; раздела нет — пусто."""
    m = re.search(r"^fixtures:\n(.*?)(?=^\S)", text, re.M | re.S)
    return f"{key}:\n" + m.group(1) if m else ""


def ancestors(path):
    """Файлы разложений предков узла файла path, от корня вниз; сам файл не входит."""
    path = Path(path)
    parts = path.name[:-len(".yaml")].split(".")
    if path.name == "rptg.yaml":
        return []
    out = [path.parent / "rptg.yaml"]
    for i in range(2, len(parts)):
        f = path.parent / (".".join(parts[:i]) + ".yaml")
        if f.exists():
            out.append(f)
    return out


def load(path):
    """Файл разложения как значение YAML; якоря данных примеров предков видны."""
    path = Path(path)
    head = "".join(fixtures_block(f.read_text(encoding="utf-8"), f"shared_fixtures_{i}")
                   for i, f in enumerate(ancestors(path)))
    return yaml.safe_load(head + path.read_text(encoding="utf-8"))


def files(design_dir=None):
    """Файлы разложения: корень первым, остальные по имени."""
    d = Path(design_dir or DESIGN)
    return [d / "rptg.yaml"] + sorted(d.glob("rptg.*.yaml"))


def designs(design_dir=None):
    """[(имя файла, разложение)], корень первым."""
    return [(f.name, load(f)["design"]) for f in files(design_dir)]
