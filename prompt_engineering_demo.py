"""
prompt_engineering_demo.py — демонстрация prompt engineering на бытовых задачах.
Запуск: python prompt_engineering_demo.py

Сравнивает базовый промпт (роль→контекст→задача→формат) с улучшенным (+ few-shot),
валидирует JSON-ответы, выводит таблицу сравнения и генерирует artifact_README.md.
"""
import json
import os
import re
import sys
from datetime import datetime

import openai_client
from config import PROVIDERS

TEMPERATURE = 0.2

# ─── Задачи ───────────────────────────────────────────────────────────────────

TASKS: dict[str, dict] = {
    "1": {
        "key": "water_reminder",
        "label": "Напоминание пить воду",
        "role": "Ты — помощник по здоровому образу жизни.",
        "context": "Пользователь хочет выработать привычку пить воду регулярно в течение дня.",
        "task": "Составь конкретный план напоминаний пить воду на один день.",
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
                "21:00 — стакан воды за час до сна"
            ],
            "notes": [
                "Норма — 8 стаканов (около 2 литров) в день",
                "Поставь напоминания в телефоне",
                "Держи бутылку воды на виду"
            ],
        },
    },
    "2": {
        "key": "discount_calc",
        "label": "Расчёт скидки",
        "role": "Ты — помощник по бытовым расчётам и экономии.",
        "context": "Пользователь хочет быстро посчитать итоговую цену товара со скидкой.",
        "task": "Объясни пошагово, как рассчитать цену товара с учётом скидки в процентах.",
        "few_shot_example": {
            "title": "Как рассчитать цену со скидкой",
            "steps": [
                "Узнай исходную цену товара (например, 1000 ₽)",
                "Узнай размер скидки в процентах (например, 20%)",
                "Вычисли сумму скидки: 1000 × 0.20 = 200 ₽",
                "Вычти скидку из цены: 1000 − 200 = 800 ₽",
                "Итоговая цена: 800 ₽"
            ],
            "notes": [
                "Формула: итог = цена × (1 − скидка/100)",
                "Для скидки 20%: умножь цену на 0.8",
                "Проверь, не суммируются ли несколько скидок"
            ],
        },
    },
    "3": {
        "key": "welcome_bot",
        "label": "Приветственный бот",
        "role": "Ты — разработчик чат-ботов и UX-специалист.",
        "context": "Пользователь хочет настроить приветственное сообщение для своего бота.",
        "task": "Составь план создания эффективного приветственного сообщения для чат-бота.",
        "few_shot_example": {
            "title": "Приветственное сообщение для бота",
            "steps": [
                "Определи цель бота (поддержка, продажи, информация)",
                "Напиши короткое приветствие с именем бота",
                "Объясни, что умеет бот (2–3 пункта)",
                "Добавь призыв к действию (например, 'Напиши свой вопрос')",
                "Протестируй сообщение на реальных пользователях"
            ],
            "notes": [
                "Приветствие должно быть не длиннее 3–4 предложений",
                "Используй дружелюбный тон",
                "Укажи, как связаться с человеком если бот не помог"
            ],
        },
    },
    "4": {
        "key": "morning_workout",
        "label": "План утренней зарядки",
        "role": "Ты — фитнес-тренер с опытом составления домашних тренировок.",
        "context": "Пользователь хочет начать делать утреннюю зарядку дома без оборудования.",
        "task": "Составь план утренней зарядки на 10–15 минут для начинающих.",
        "few_shot_example": {
            "title": "Утренняя зарядка на 10 минут",
            "steps": [
                "1 мин — потягивания лёжа в кровати",
                "2 мин — вращения шеей, плечами, запястьями",
                "2 мин — наклоны в стороны и вперёд стоя",
                "2 мин — приседания (2 подхода по 10 раз)",
                "2 мин — отжимания от пола (2 подхода по 5–8 раз)",
                "1 мин — планка (2 подхода по 20–30 секунд)"
            ],
            "notes": [
                "Делай зарядку сразу после пробуждения",
                "Не форсируй нагрузку — важна регулярность",
                "Пей стакан воды до и после зарядки"
            ],
        },
    },
    "5": {
        "key": "shopping_list",
        "label": "Список покупок",
        "role": "Ты — помощник по организации быта и планированию.",
        "context": "Пользователь хочет составить эффективный список покупок на неделю.",
        "task": "Объясни пошагово, как составить список покупок на неделю, чтобы ничего не забыть и не купить лишнего.",
        "few_shot_example": {
            "title": "Как составить список покупок на неделю",
            "steps": [
                "Составь меню на 7 дней (завтрак, обед, ужин)",
                "Выпиши все ингредиенты из меню",
                "Проверь холодильник и шкафы — вычеркни то, что уже есть",
                "Добавь регулярные товары (хлеб, молоко, яйца)",
                "Сгруппируй список по отделам магазина",
                "Запиши список в телефон или распечатай"
            ],
            "notes": [
                "Ходи в магазин не голодным",
                "Придерживайся списка — это экономит деньги",
                "Обновляй список раз в неделю"
            ],
        },
    },
}

# ─── Вспомогательные функции ──────────────────────────────────────────────────

def sep(char: str = "─", width: int = 60) -> None:
    print(char * width)


def pick_task() -> tuple[str, dict]:
    sep("═")
    print("  ВЫБОР ЗАДАЧИ")
    sep("═")
    for key, t in TASKS.items():
        print(f"  {key}. {t['label']}")
    sep()
    while True:
        choice = input("  Номер задачи: ").strip()
        if choice in TASKS:
            return choice, TASKS[choice]
        print(f"  Неверный номер. Введите от 1 до {len(TASKS)}.")


def pick_provider_and_model() -> tuple[str, str, dict]:
    sep("═")
    print("  ВЫБОР ПРОВАЙДЕРА")
    sep("═")
    p_keys = list(PROVIDERS.keys())
    for i, k in enumerate(p_keys, 1):
        print(f"  {i}. {PROVIDERS[k]['name']}")
    sep()
    while True:
        choice = input(f"  Провайдер [1]: ").strip() or "1"
        try:
            p_key = p_keys[int(choice) - 1]
            break
        except (ValueError, IndexError):
            print(f"  Неверный номер.")

    api_key = os.environ.get(PROVIDERS[p_key].get("api_key_env", ""),
                             PROVIDERS[p_key].get("api_key", ""))
    # config.py хранит api_key напрямую, проверим оба варианта
    if not api_key:
        env_var = PROVIDERS[p_key].get("api_key_env", "")
        direct = PROVIDERS[p_key].get("api_key", "")
        if not env_var and not direct:
            print(f"  Ошибка: API-ключ для {PROVIDERS[p_key]['name']} не найден.")
            sys.exit(1)

    models = PROVIDERS[p_key]["models"]
    sep()
    print(f"  МОДЕЛИ — {PROVIDERS[p_key]['name']}")
    sep()
    print(f"  {'#':<4} {'Модель':<25} Макс. токенов")
    sep()
    for i, m in enumerate(models, 1):
        print(f"  {i:<4} {m['label']:<25} {m.get('max_tokens_limit', m.get('max_tokens', '?'))}")
    sep()
    while True:
        choice = input("  Модель [1]: ").strip() or "1"
        try:
            model = models[int(choice) - 1]
            break
        except (ValueError, IndexError):
            print("  Неверный номер.")

    return p_key, model["id"], model

# ─── Построение промптов ──────────────────────────────────────────────────────

def build_base_prompt(task: dict) -> str:
    return (
        f"Роль: {task['role']}\n"
        f"Контекст: {task['context']}\n"
        f"Задача: {task['task']}\n"
        f'Формат ответа: верни строго JSON без пояснений и без markdown:\n'
        f'{{"title": "...", "steps": ["...", "..."], "notes": ["...", "..."]}}'
    )


def build_enhanced_prompt(task: dict) -> str:
    example = json.dumps(task["few_shot_example"], ensure_ascii=False)
    return (
        build_base_prompt(task)
        + f"\n\nПример корректного ответа:\n{example}"
    )

# ─── Валидация ответа ─────────────────────────────────────────────────────────

def parse_response(raw: str) -> tuple[dict | None, str]:
    """Возвращает (parsed | None, status ∈ {'valid','incomplete','invalid'})."""
    try:
        # Извлечь JSON из ```json ... ``` если есть
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
        text = match.group(1) if match else raw.strip()
        data = json.loads(text)
        if (
            isinstance(data.get("title"), str)
            and isinstance(data.get("steps"), list)
            and isinstance(data.get("notes"), list)
        ):
            return data, "valid"
        return data, "incomplete"
    except Exception:
        return None, "invalid"

# ─── Сравнение ────────────────────────────────────────────────────────────────

def _metrics(parsed: dict | None) -> tuple[bool, int, float]:
    valid = parsed is not None and isinstance(parsed.get("steps"), list) and isinstance(parsed.get("notes"), list)
    steps = len(parsed["steps"]) if valid else 0
    notes = parsed.get("notes", []) if valid else []
    avg = sum(len(s) for s in notes) / len(notes) if notes else 0.0
    return valid, steps, avg


def compare_responses(
    base_parsed: dict | None, base_status: str,
    enhanced_parsed: dict | None, enhanced_status: str,
) -> dict:
    b_valid, b_steps, b_avg = _metrics(base_parsed if base_status == "valid" else None)
    e_valid, e_steps, e_avg = _metrics(enhanced_parsed if enhanced_status == "valid" else None)

    def winner_flag(b_val, e_val, higher_is_better: bool) -> str:
        if b_val == e_val:
            return "tie"
        if higher_is_better:
            return "enhanced" if e_val > b_val else "base"
        else:
            return "enhanced" if e_val < b_val else "base"

    json_winner = "tie" if b_valid == e_valid else ("enhanced" if e_valid else "base")

    return {
        "base":     {"json_valid": b_valid, "steps_count": b_steps, "avg_notes_len": b_avg},
        "enhanced": {"json_valid": e_valid, "steps_count": e_steps, "avg_notes_len": e_avg},
        "winner": {
            "json_valid":    json_winner,
            "steps_count":   winner_flag(b_steps, e_steps, higher_is_better=True),
            "avg_notes_len": winner_flag(b_avg,   e_avg,   higher_is_better=False),
        },
    }


def print_comparison(cmp: dict) -> None:
    sep("═")
    print("  СРАВНЕНИЕ ОТВЕТОВ")
    sep("═")
    b, e, w = cmp["base"], cmp["enhanced"], cmp["winner"]
    rows = [
        ("Критерий",          "Базовый",                    "Улучшенный",                 "Лучше"),
        ("JSON-формат",       "да" if b["json_valid"] else "нет",
                              "да" if e["json_valid"] else "нет",  w["json_valid"]),
        ("Шагов (steps)",     str(b["steps_count"]),        str(e["steps_count"]),        w["steps_count"]),
        ("Ср. длина notes",   f"{b['avg_notes_len']:.1f}",  f"{e['avg_notes_len']:.1f}",  w["avg_notes_len"]),
    ]
    col = [28, 14, 14, 12]
    header, *data_rows = rows
    print("  " + "  ".join(h.ljust(col[i]) for i, h in enumerate(header)))
    sep()
    for row in data_rows:
        print("  " + "  ".join(str(v).ljust(col[i]) for i, v in enumerate(row)))
    sep("═")

# ─── Выбор победителя ─────────────────────────────────────────────────────────

def select_winner(
    base_parsed: dict | None, base_status: str,
    enhanced_parsed: dict | None, enhanced_status: str,
) -> tuple[dict | None, str]:
    if enhanced_status == "valid":
        return enhanced_parsed, "enhanced"
    if base_status == "valid":
        return base_parsed, "base"
    return enhanced_parsed, "enhanced"

# ─── Генерация артефакта ──────────────────────────────────────────────────────

def write_artifact(
    task: dict, model_label: str,
    winner: dict | None, winner_raw: str, winner_status: str, source: str,
) -> str:
    path = "artifact_README.md"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if winner and winner_status == "valid":
        steps_md = "\n".join(f"{i+1}. {s}" for i, s in enumerate(winner["steps"]))
        notes_md = "\n".join(f"- {n}" for n in winner["notes"])
        content = (
            f"# {winner['title']}\n\n"
            f"> Задача: {task['label']}\n"
            f"> Модель: {model_label}\n"
            f"> Дата: {now}\n"
            f"> Источник: {source}\n\n"
            f"## Шаги\n\n{steps_md}\n\n"
            f"## Примечания\n\n{notes_md}\n"
        )
    else:
        content = (
            f"# Ошибка парсинга\n\n"
            f"> Задача: {task['label']}\n"
            f"> Модель: {model_label}\n"
            f"> Дата: {now}\n"
            f"> Статус: {winner_status}\n\n"
            f"## Сырой ответ модели\n\n{winner_raw}\n"
        )

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return os.path.abspath(path)

# ─── Оркестратор ──────────────────────────────────────────────────────────────

def run_demo() -> None:
    print("\n" + "═" * 60)
    print("  PROMPT ENGINEERING DEMO")
    print("═" * 60)

    _, task = pick_task()
    provider_key, model_id, model_dict = pick_provider_and_model()
    model_label = model_dict["label"]
    max_tokens = model_dict.get("max_tokens_limit", model_dict.get("max_tokens", 1024))

    base_sys    = build_base_prompt(task)
    enhanced_sys = build_enhanced_prompt(task)
    user_msg    = "Выполни задачу."

    # ── Запрос 1: базовый промпт ──────────────────────────────────────────────
    sep()
    print(f"  [1/2] Отправка базового промпта → {model_label} (t={TEMPERATURE})...")
    try:
        base_raw, base_usage = openai_client.chat(
            provider_key=provider_key,
            model_id=model_id,
            messages=[
                {"role": "system", "content": base_sys},
                {"role": "user",   "content": user_msg},
            ],
            temperature=TEMPERATURE,
            max_tokens=max_tokens,
        )
    except Exception as e:
        print(f"  Ошибка: {e}")
        sys.exit(1)

    base_parsed, base_status = parse_response(base_raw)
    print(f"  Статус: {base_status} | токены: {base_usage.get('total_tokens', '?')}")

    # ── Запрос 2: улучшенный промпт ───────────────────────────────────────────
    print(f"\n  [2/2] Отправка улучшенного промпта (few-shot) → {model_label} (t={TEMPERATURE})...")
    try:
        enhanced_raw, enhanced_usage = openai_client.chat(
            provider_key=provider_key,
            model_id=model_id,
            messages=[
                {"role": "system", "content": enhanced_sys},
                {"role": "user",   "content": user_msg},
            ],
            temperature=TEMPERATURE,
            max_tokens=max_tokens,
        )
    except Exception as e:
        print(f"  Ошибка: {e}")
        sys.exit(1)

    enhanced_parsed, enhanced_status = parse_response(enhanced_raw)
    print(f"  Статус: {enhanced_status} | токены: {enhanced_usage.get('total_tokens', '?')}")

    # ── Сравнение ─────────────────────────────────────────────────────────────
    cmp = compare_responses(base_parsed, base_status, enhanced_parsed, enhanced_status)
    print_comparison(cmp)

    # ── Артефакт ──────────────────────────────────────────────────────────────
    winner, source = select_winner(base_parsed, base_status, enhanced_parsed, enhanced_status)
    winner_raw = enhanced_raw if source == "enhanced" else base_raw
    winner_status = enhanced_status if source == "enhanced" else base_status

    artifact_path = write_artifact(task, model_label, winner, winner_raw, winner_status, source)
    print(f"\n  Артефакт сохранён → {artifact_path}")


if __name__ == "__main__":
    run_demo()
