"""
prompter.py — A/B-тестирование техник prompt engineering.
Запуск: python prompter.py

Техники: zero-shot, few-shot, chain-of-thought (CoT), role-based.
Сравнивает все выбранные техники и сохраняет полный отчёт в artifact_YYYYMMDD_HHMMSS.md.
"""
import json
import os
import re
import sys
from datetime import datetime

import openai_client
from config import PROVIDERS

# ─── Задачи ───────────────────────────────────────────────────────────────────

TASKS: dict[str, dict] = {
    "1": {
        "key": "water_reminder",
        "label": "Напоминание пить воду",
        "role": "Ты — персональный тренер по здоровому образу жизни с 10-летним опытом.",
        "context": "Пользователь хочет выработать привычку пить воду регулярно в течение дня.",
        "task": "Составь конкретный план напоминаний пить воду на один день.",
        "cot_hint": "Сначала определи оптимальные временные интервалы, затем учти физиологию (утро, до/после еды, вечер), потом сформируй итоговый план.",
        "few_shot_example": {
            "title": "План питья воды на день",
            "steps": [
                "07:00 — стакан воды сразу после пробуждения",
                "09:00 — стакан воды перед завтраком",
                "11:00 — стакан воды в середине утра",
                "13:00 — стакан воды перед обедом",
                "15:00 — стакан воды после обеда",
                "17:00 — стакан воды в середине дня",
                "19:00 — стакан воды перед ужином",
                "21:00 — стакан воды за час до сна",
            ],
            "notes": [
                "Норма — 8 стаканов (около 2 литров) в день",
                "Поставь напоминания в телефоне",
                "Держи бутылку воды на виду",
            ],
        },
    },
    "2": {
        "key": "discount_calc",
        "label": "Расчёт скидки",
        "role": "Ты — финансовый консультант, специализирующийся на бытовой экономии.",
        "context": "Пользователь хочет быстро посчитать итоговую цену товара со скидкой.",
        "task": "Объясни пошагово, как рассчитать цену товара с учётом скидки в процентах.",
        "cot_hint": "Сначала выведи математическую формулу, затем разбей её на понятные шаги, потом приведи числовой пример.",
        "few_shot_example": {
            "title": "Как рассчитать цену со скидкой",
            "steps": [
                "Узнай исходную цену товара (например, 1000 ₽)",
                "Узнай размер скидки в процентах (например, 20%)",
                "Вычисли сумму скидки: 1000 × 0.20 = 200 ₽",
                "Вычти скидку из цены: 1000 − 200 = 800 ₽",
                "Итоговая цена: 800 ₽",
            ],
            "notes": [
                "Формула: итог = цена × (1 − скидка/100)",
                "Для скидки 20%: умножь цену на 0.8",
                "Проверь, не суммируются ли несколько скидок",
            ],
        },
    },
    "3": {
        "key": "welcome_bot",
        "label": "Приветственный бот",
        "role": "Ты — senior UX-копирайтер с опытом разработки диалоговых интерфейсов.",
        "context": "Пользователь хочет настроить приветственное сообщение для своего чат-бота.",
        "task": "Составь план создания эффективного приветственного сообщения для чат-бота.",
        "cot_hint": "Сначала определи цель бота, затем продумай структуру сообщения (приветствие → возможности → призыв к действию), потом сформулируй финальный текст.",
        "few_shot_example": {
            "title": "Приветственное сообщение для бота",
            "steps": [
                "Определи цель бота (поддержка, продажи, информация)",
                "Напиши короткое приветствие с именем бота",
                "Объясни, что умеет бот (2–3 пункта)",
                "Добавь призыв к действию (например, 'Напиши свой вопрос')",
                "Протестируй сообщение на реальных пользователях",
            ],
            "notes": [
                "Приветствие должно быть не длиннее 3–4 предложений",
                "Используй дружелюбный тон",
                "Укажи, как связаться с человеком если бот не помог",
            ],
        },
    },
    "4": {
        "key": "morning_workout",
        "label": "План утренней зарядки",
        "role": "Ты — сертифицированный фитнес-тренер, специализирующийся на домашних тренировках.",
        "context": "Пользователь хочет начать делать утреннюю зарядку дома без оборудования.",
        "task": "Составь план утренней зарядки на 10–15 минут для начинающих.",
        "cot_hint": "Сначала определи группы мышц для разминки, затем подбери упражнения по принципу от лёгкого к сложному, потом распредели время.",
        "few_shot_example": {
            "title": "Утренняя зарядка на 10 минут",
            "steps": [
                "1 мин — потягивания лёжа в кровати",
                "2 мин — вращения шеей, плечами, запястьями",
                "2 мин — наклоны в стороны и вперёд стоя",
                "2 мин — приседания (2 подхода по 10 раз)",
                "2 мин — отжимания от пола (2 подхода по 5–8 раз)",
                "1 мин — планка (2 подхода по 20–30 секунд)",
            ],
            "notes": [
                "Делай зарядку сразу после пробуждения",
                "Не форсируй нагрузку — важна регулярность",
                "Пей стакан воды до и после зарядки",
            ],
        },
    },
    "5": {
        "key": "shopping_list",
        "label": "Список покупок",
        "role": "Ты — эксперт по организации быта и осознанному потреблению.",
        "context": "Пользователь хочет составить эффективный список покупок на неделю.",
        "task": "Объясни пошагово, как составить список покупок на неделю, чтобы ничего не забыть и не купить лишнего.",
        "cot_hint": "Сначала продумай планирование меню, затем инвентаризацию холодильника, потом структурирование списка по категориям.",
        "few_shot_example": {
            "title": "Как составить список покупок на неделю",
            "steps": [
                "Составь меню на 7 дней (завтрак, обед, ужин)",
                "Выпиши все ингредиенты из меню",
                "Проверь холодильник и шкафы — вычеркни то, что уже есть",
                "Добавь регулярные товары (хлеб, молоко, яйца)",
                "Сгруппируй список по отделам магазина",
                "Запиши список в телефон или распечатай",
            ],
            "notes": [
                "Ходи в магазин не голодным",
                "Придерживайся списка — это экономит деньги",
                "Обновляй список раз в неделю",
            ],
        },
    },
}

# ─── Техники промптинга ───────────────────────────────────────────────────────

TECHNIQUES: dict[str, str] = {
    "1": "zero-shot",
    "2": "few-shot",
    "3": "chain-of-thought",
    "4": "role-based",
}

JSON_FORMAT = '{"title": "...", "steps": ["...", "..."], "notes": ["...", "..."]}'

# ─── Вспомогательные функции ──────────────────────────────────────────────────

def sep(char: str = "─", width: int = 60) -> None:
    print(char * width)


def ask(prompt: str, default: str = "") -> str:
    val = input(prompt).strip()
    return val if val else default


def get_float(prompt: str, default: float, lo: float, hi: float) -> float:
    try:
        return max(lo, min(hi, float(ask(prompt, str(default)))))
    except ValueError:
        return default


def get_int(prompt: str, default: int, lo: int, hi: int) -> int:
    try:
        return max(lo, min(hi, int(ask(prompt, str(default)))))
    except ValueError:
        return default


def calc_cost(usage: dict, model: dict) -> float:
    p_in  = model.get("price_in", 0.0)
    p_out = model.get("price_out", 0.0)
    return (usage.get("prompt_tokens", 0) / 1000 * p_in +
            usage.get("completion_tokens", 0) / 1000 * p_out)

# ─── Выбор задачи ─────────────────────────────────────────────────────────────

def pick_task() -> dict:
    sep("═")
    print("  ВЫБОР ЗАДАЧИ")
    sep("═")
    for key, t in TASKS.items():
        print(f"  {key}. {t['label']}")
    sep()
    while True:
        choice = input("  Номер задачи: ").strip()
        if choice in TASKS:
            return TASKS[choice]
        print(f"  Неверный номер. Введите от 1 до {len(TASKS)}.")

# ─── Выбор провайдера и модели ────────────────────────────────────────────────

def pick_provider_and_model() -> tuple[str, str, dict]:
    sep("═")
    print("  ВЫБОР ПРОВАЙДЕРА")
    sep("═")
    p_keys = list(PROVIDERS.keys())
    for i, k in enumerate(p_keys, 1):
        print(f"  {i}. {PROVIDERS[k]['name']}")
    sep()
    while True:
        choice = ask("  Провайдер [1]: ", "1")
        try:
            p_key = p_keys[int(choice) - 1]
            break
        except (ValueError, IndexError):
            print("  Неверный номер.")

    if not PROVIDERS[p_key].get("api_key"):
        print(f"  Ошибка: API-ключ для {PROVIDERS[p_key]['name']} не найден в .env")
        sys.exit(1)

    models = PROVIDERS[p_key]["models"]
    sep()
    print(f"  МОДЕЛИ — {PROVIDERS[p_key]['name']}")
    sep()
    print(f"  {'#':<4} {'Модель':<28} {'Контекст':<10} {'Бесплатно':<12} Макс. токенов")
    sep()
    for i, m in enumerate(models, 1):
        free_tag = "да" if m.get("free") else "нет"
        print(f"  {i:<4} {m['label']:<28} {m.get('context','?'):<10} {free_tag:<12} {m.get('max_tokens_limit','?')}")
    sep()
    while True:
        choice = ask("  Модель [1]: ", "1")
        try:
            model = models[int(choice) - 1]
            break
        except (ValueError, IndexError):
            print("  Неверный номер.")

    return p_key, model["id"], model

# ─── Выбор параметров модели ──────────────────────────────────────────────────

def pick_params(model: dict) -> tuple[float, int]:
    lo, hi = model.get("temp_range", (0.0, 2.0))
    max_limit = model.get("max_tokens_limit", 4096)
    sep()
    print("  ПАРАМЕТРЫ ЗАПРОСА")
    sep()
    temperature = get_float(f"  Temperature ({lo}–{hi}, по умолчанию 0.2): ", 0.2, lo, hi)
    max_tokens  = get_int(f"  Max tokens (1–{max_limit}, по умолчанию 512): ", 512, 1, max_limit)
    return temperature, max_tokens

# ─── Выбор техник ─────────────────────────────────────────────────────────────

def pick_techniques() -> list[str]:
    sep()
    print("  ТЕХНИКИ ПРОМПТИНГА (A/B-тест)")
    sep()
    for key, name in TECHNIQUES.items():
        print(f"  {key}. {name}")
    sep()
    print("  Введите номера через запятую (например: 1,2,3) или Enter для всех")
    raw = ask("  Техники [все]: ", "")
    if not raw:
        return list(TECHNIQUES.values())
    selected = []
    for part in raw.split(","):
        part = part.strip()
        if part in TECHNIQUES:
            selected.append(TECHNIQUES[part])
    return selected if selected else list(TECHNIQUES.values())

# ─── Построение промптов по технике ──────────────────────────────────────────

def build_prompt(task: dict, technique: str) -> str:
    base = (
        f"Задача: {task['task']}\n"
        f"Контекст: {task['context']}\n"
        f"Формат ответа: верни строго JSON без пояснений и без markdown:\n{JSON_FORMAT}"
    )

    if technique == "zero-shot":
        return base

    if technique == "few-shot":
        example = json.dumps(task["few_shot_example"], ensure_ascii=False, indent=2)
        return base + f"\n\nПример корректного ответа:\n{example}"

    if technique == "chain-of-thought":
        return (
            f"Задача: {task['task']}\n"
            f"Контекст: {task['context']}\n"
            f"Рассуждай пошагово: {task['cot_hint']}\n"
            f"После рассуждения верни строго JSON без пояснений и без markdown:\n{JSON_FORMAT}"
        )

    if technique == "role-based":
        return (
            f"Роль: {task['role']}\n"
            f"Контекст: {task['context']}\n"
            f"Задача: {task['task']}\n"
            f"Формат ответа: верни строго JSON без пояснений и без markdown:\n{JSON_FORMAT}"
        )

    return base

# ─── Валидация ответа ─────────────────────────────────────────────────────────

def parse_response(raw: str) -> tuple[dict | None, str]:
    try:
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
        text = match.group(1) if match else raw.strip()
        # Обрезать до первого валидного JSON-объекта
        brace = text.find("{")
        if brace > 0:
            text = text[brace:]
        data = json.loads(text)
        if (isinstance(data.get("title"), str)
                and isinstance(data.get("steps"), list)
                and isinstance(data.get("notes"), list)):
            return data, "valid"
        return data, "incomplete"
    except Exception:
        return None, "invalid"

# ─── Метрики и сравнение ──────────────────────────────────────────────────────

def _metrics(parsed: dict | None, status: str) -> dict:
    valid = status == "valid"
    steps = len(parsed["steps"]) if valid and parsed else 0
    notes = parsed.get("notes", []) if valid and parsed else []
    avg_notes = sum(len(s) for s in notes) / len(notes) if notes else 0.0
    return {"json_valid": valid, "steps_count": steps, "avg_notes_len": avg_notes}


def compare_all(results: list[dict]) -> list[dict]:
    """Добавляет поле 'rank' к каждому результату по сумме баллов."""
    for r in results:
        m = r["metrics"]
        r["score"] = (
            (1 if m["json_valid"] else 0)
            + m["steps_count"] * 0.1
            - m["avg_notes_len"] * 0.001
        )
    ranked = sorted(results, key=lambda x: x["score"], reverse=True)
    for i, r in enumerate(ranked):
        r["rank"] = i + 1
    return results

# ─── Вывод в терминал ─────────────────────────────────────────────────────────

def print_comparison(results: list[dict]) -> None:
    sep("═")
    print("  A/B СРАВНЕНИЕ ТЕХНИК")
    sep("═")
    cols = [20, 10, 8, 12, 14, 10, 8]
    header = ("Техника", "Статус", "Ранг", "Шагов", "Ср.длина notes", "Токены", "Стоимость")
    print("  " + "  ".join(h.ljust(cols[i]) for i, h in enumerate(header)))
    sep()
    for r in sorted(results, key=lambda x: x["rank"]):
        m = r["metrics"]
        cost_str = f"{r['cost']:.4f}₽" if r["cost"] > 0 else "бесплатно"
        row = (
            r["technique"],
            r["status"],
            str(r["rank"]),
            str(m["steps_count"]),
            f"{m['avg_notes_len']:.1f}",
            str(r["usage"].get("total_tokens", "?")),
            cost_str,
        )
        print("  " + "  ".join(str(v).ljust(cols[i]) for i, v in enumerate(row)))
    sep("═")

# ─── Генерация артефакта ──────────────────────────────────────────────────────

def _technique_section(r: dict) -> str:
    m = r["metrics"]
    cost_str = f"{r['cost']:.4f} ₽" if r["cost"] > 0 else "бесплатно"
    u = r["usage"]
    lines = [
        f"### Техника: {r['technique']} (ранг #{r['rank']})",
        "",
        f"| Параметр | Значение |",
        f"| --- | --- |",
        f"| Статус JSON | {r['status']} |",
        f"| Шагов (steps) | {m['steps_count']} |",
        f"| Ср. длина notes | {m['avg_notes_len']:.1f} симв. |",
        f"| Токены вход | {u.get('prompt_tokens','?')} |",
        f"| Токены выход | {u.get('completion_tokens','?')} |",
        f"| Токены всего | {u.get('total_tokens','?')} |",
        f"| Стоимость | {cost_str} |",
        "",
        "**Промпт (system):**",
        "",
        f"```\n{r['prompt']}\n```",
        "",
        "**Ответ модели:**",
        "",
        f"```\n{r['raw']}\n```",
    ]
    if r["status"] == "valid" and r["parsed"]:
        p = r["parsed"]
        steps_md = "\n".join(f"{i+1}. {s}" for i, s in enumerate(p["steps"]))
        notes_md = "\n".join(f"- {n}" for n in p["notes"])
        lines += [
            "",
            "**Распознанный результат:**",
            "",
            f"**{p['title']}**",
            "",
            steps_md,
            "",
            notes_md,
        ]
    return "\n".join(lines)


def _comparison_table_md(results: list[dict]) -> str:
    header = ["Ранг", "Техника", "JSON", "Шагов", "Ср.длина notes", "Токены", "Стоимость"]
    rows = [header, ["---"] * len(header)]
    for r in sorted(results, key=lambda x: x["rank"]):
        m = r["metrics"]
        cost_str = f"{r['cost']:.4f} ₽" if r["cost"] > 0 else "бесплатно"
        rows.append([
            f"#{r['rank']}",
            r["technique"],
            "✅" if m["json_valid"] else "❌",
            str(m["steps_count"]),
            f"{m['avg_notes_len']:.1f}",
            str(r["usage"].get("total_tokens", "?")),
            cost_str,
        ])
    return "\n".join("| " + " | ".join(row) + " |" for row in rows)


def write_artifact(
    task: dict,
    provider_name: str,
    model_id: str,
    model_label: str,
    temperature: float,
    max_tokens: int,
    results: list[dict],
) -> str:
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    human_time = now.strftime("%Y-%m-%d %H:%M:%S")
    path = f"artifact_{timestamp}.md"

    total_cost = sum(r["cost"] for r in results)
    total_tokens = sum(r["usage"].get("total_tokens", 0) for r in results)
    winner = min(results, key=lambda x: x["rank"])

    lines = [
        f"# Prompter A/B Report — {human_time}",
        "",
        "## Параметры запуска",
        "",
        "| Параметр | Значение |",
        "| --- | --- |",
        f"| Задача | {task['label']} |",
        f"| Провайдер | {provider_name} |",
        f"| Модель (label) | {model_label} |",
        f"| Модель (id) | {model_id} |",
        f"| Temperature | {temperature} |",
        f"| Max tokens | {max_tokens} |",
        f"| Техник протестировано | {len(results)} |",
        f"| Токенов всего | {total_tokens} |",
        f"| Стоимость всего | {'бесплатно' if total_cost == 0 else f'{total_cost:.4f} ₽'} |",
        "",
        "---",
        "",
        "## Сводная таблица сравнения",
        "",
        _comparison_table_md(results),
        "",
        "---",
        "",
        "## Победитель",
        "",
        f"**Техника:** {winner['technique']}  ",
        f"**Статус:** {winner['status']}  ",
        f"**Шагов:** {winner['metrics']['steps_count']}  ",
        f"**Стоимость:** {'бесплатно' if winner['cost'] == 0 else f\"{winner['cost']:.4f} ₽\"}",
        "",
        "---",
        "",
        "## Детали по каждой технике",
        "",
    ]

    for r in sorted(results, key=lambda x: x["rank"]):
        lines.append(_technique_section(r))
        lines.append("")
        lines.append("---")
        lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return os.path.abspath(path)

# ─── Оркестратор ──────────────────────────────────────────────────────────────

def run() -> None:
    print("\n" + "═" * 60)
    print("  PROMPTER — A/B-тест техник промптинга")
    print("═" * 60)

    task = pick_task()
    provider_key, model_id, model_dict = pick_provider_and_model()
    temperature, max_tokens = pick_params(model_dict)
    techniques = pick_techniques()

    model_label = model_dict["label"]
    user_msg = "Выполни задачу."

    results: list[dict] = []

    sep("═")
    print(f"  Запуск {len(techniques)} техник → {model_label} | t={temperature} | max_tokens={max_tokens}")
    sep("═")

    for i, technique in enumerate(techniques, 1):
        prompt = build_prompt(task, technique)
        print(f"\n  [{i}/{len(techniques)}] {technique}...")
        try:
            raw, usage = openai_client.chat(
                provider_key=provider_key,
                model_id=model_id,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user",   "content": user_msg},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as e:
            print(f"  Ошибка: {e}")
            sys.exit(1)

        parsed, status = parse_response(raw)
        cost = calc_cost(usage, model_dict)
        cost_str = f"{cost:.4f}₽" if cost > 0 else "бесплатно"
        print(f"  Статус: {status} | токены: {usage.get('total_tokens','?')} | {cost_str}")

        results.append({
            "technique": technique,
            "prompt":    prompt,
            "raw":       raw,
            "parsed":    parsed,
            "status":    status,
            "usage":     usage,
            "cost":      cost,
            "metrics":   _metrics(parsed, status),
            "rank":      0,
            "score":     0.0,
        })

    results = compare_all(results)
    print_comparison(results)

    artifact_path = write_artifact(
        task=task,
        provider_name=PROVIDERS[provider_key]["name"],
        model_id=model_id,
        model_label=model_label,
        temperature=temperature,
        max_tokens=max_tokens,
        results=results,
    )
    print(f"\n  Артефакт сохранён → {artifact_path}")


if __name__ == "__main__":
    run()
