"""
case_prompter.py — Тестирование системных промптов из JSON-файлов.
Запуск: python case_prompter.py

Читает системные промпты из папки Prompts/*.json, принимает вопрос от пользователя,
отправляет запрос выбранному AI-провайдеру и сохраняет ответ в Markdown-файл.

Поддерживаемые провайдеры: Z.AI, ProxyAPI, GenAPI (через openai_client.py).
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import openai_client
from config import PROVIDERS

PROMPTS_DIR = Path(__file__).parent / "Prompts"
OUTPUT_DIR  = Path(__file__).parent / "cases"

# ─── Утилиты ──────────────────────────────────────────────────────────────────

def sep(char: str = "─", width: int = 64) -> None:
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
    return (usage.get("prompt_tokens", 0) / 1000 * model.get("price_in", 0.0) +
            usage.get("completion_tokens", 0) / 1000 * model.get("price_out", 0.0))

# ─── Загрузка промптов ────────────────────────────────────────────────────────

def load_prompt_files() -> list[dict]:
    """Загружает все JSON-файлы из папки Prompts/."""
    files = sorted(PROMPTS_DIR.glob("*.json"))
    if not files:
        print(f"  Ошибка: папка {PROMPTS_DIR} пуста или не существует.")
        sys.exit(1)
    prompts = []
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            data["_file"] = f.name
            prompts.append(data)
        except Exception as e:
            print(f"  Предупреждение: не удалось прочитать {f.name}: {e}")
    return prompts

def build_system_message(prompt: dict) -> str:
    """
    Собирает системное сообщение из полей JSON-промпта.
    Схема: роль → контекст → структура → формат.
    """
    parts = []

    if role := prompt.get("role"):
        parts.append(f"# Роль\n{role}")

    if context := prompt.get("context"):
        parts.append(f"# Контекст\n{context}")

    if structure := prompt.get("structure"):
        fmt = structure.get("output_format", "")
        components = structure.get("components", [])
        if fmt or components:
            block = f"# Структура ответа\nФормат: {fmt}\n"
            block += "\n".join(f"- {c['name']}: {c['description']}" for c in components)
            parts.append(block)

    if fmt := prompt.get("format"):
        reqs = fmt.get("requirements", [])
        block = "# Требования к формату\n"
        for k, v in fmt.items():
            if k != "requirements" and isinstance(v, str):
                block += f"- {k}: {v}\n"
        if reqs:
            block += "Обязательные требования:\n"
            block += "\n".join(f"  • {r}" for r in reqs)
        parts.append(block)

    return "\n\n".join(parts)

# ─── Выбор промптов ───────────────────────────────────────────────────────────

def pick_prompts(prompts: list[dict]) -> list[dict]:
    sep("═")
    print("  СИСТЕМНЫЕ ПРОМПТЫ")
    sep("═")
    for i, p in enumerate(prompts, 1):
        name     = p.get("name", p["_file"])
        category = p.get("category", "")
        version  = p.get("version", "")
        desc     = p.get("description", "")[:60]
        print(f"  {i}. [{category}] {name} v{version}")
        print(f"     {desc}...")
    sep()
    print("  Введите номера через запятую (например: 1,3) или Enter для всех")
    raw = ask("  Промпты [все]: ", "")
    if not raw:
        return prompts
    selected = []
    for part in raw.split(","):
        part = part.strip()
        try:
            idx = int(part) - 1
            if 0 <= idx < len(prompts):
                selected.append(prompts[idx])
        except ValueError:
            pass
    return selected if selected else prompts

# ─── Выбор провайдера и модели ────────────────────────────────────────────────

def pick_provider_and_model() -> tuple[str, str, dict]:
    sep("═")
    print("  ПРОВАЙДЕР")
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
    print(f"  {'#':<4} {'Модель':<28} {'Контекст':<10} {'Бесплатно':<12} {'Температура':<14} Макс. токенов")
    sep()
    for i, m in enumerate(models, 1):
        free_tag = "да" if m.get("free") else "нет"
        tlo, thi = m.get("temp_range", (0.0, 2.0))
        print(f"  {i:<4} {m['label']:<28} {m.get('context','?'):<10} {free_tag:<12} {tlo}–{thi:<10} {m.get('max_tokens_limit','?')}")
    sep()
    while True:
        choice = ask("  Модель [1]: ", "1")
        try:
            model = models[int(choice) - 1]
            break
        except (ValueError, IndexError):
            print("  Неверный номер.")

    return p_key, model["id"], model

# ─── Выбор параметров ─────────────────────────────────────────────────────────

def pick_params(model: dict) -> tuple[float, int]:
    lo, hi = model.get("temp_range", (0.0, 2.0))
    max_limit = model.get("max_tokens_limit", 4096)
    sep()
    print("  ПАРАМЕТРЫ ЗАПРОСА")
    sep()
    print("  Рекомендуется temperature=0.2–0.7 для структурированных ответов.")
    temperature = get_float(f"  Temperature [{lo}–{hi}], по умолчанию 0.7: ", 0.7, lo, hi)
    if temperature > 1.5:
        print(f"  Предупреждение: temperature={temperature} очень высокая.")
        if ask("  Продолжить? [y/N]: ", "n").lower() != "y":
            temperature = get_float(f"  Temperature [{lo}–{hi}], по умолчанию 0.7: ", 0.7, lo, hi)
    max_tokens = get_int(f"  Max tokens [1–{max_limit}], по умолчанию 2048: ", 2048, 1, max_limit)
    return temperature, max_tokens

# ─── Ввод вопроса ─────────────────────────────────────────────────────────────

def pick_user_question(prompt: dict) -> str:
    sep()
    name = prompt.get("name", prompt["_file"])
    print(f"  ВОПРОС для промпта: {name}")
    sep()

    # Показать test_input как подсказку
    if test := prompt.get("test_input"):
        print(f"  Пример вопроса (test_input):")
        print(f"  {test[:120]}{'...' if len(test) > 120 else ''}")
        sep()
        use_test = ask("  Использовать пример? [y/N]: ", "n").lower()
        if use_test == "y":
            return test

    print("  Введите вопрос (пустая строка = завершить ввод многострочного текста двумя Enter):")
    lines = []
    empty_count = 0
    while True:
        line = input("  > ")
        if line == "":
            empty_count += 1
            if empty_count >= 2 or (lines and empty_count >= 1):
                break
        else:
            empty_count = 0
            lines.append(line)
    return "\n".join(lines).strip()

# ─── Форматирование вывода в терминал ─────────────────────────────────────────

def print_result(
    prompt_name: str,
    provider_name: str,
    model_label: str,
    temperature: float,
    max_tokens: int,
    question: str,
    answer: str,
    usage: dict,
    cost: float,
) -> None:
    sep("═")
    print(f"  ОТВЕТ — {prompt_name}")
    sep("═")
    if not answer:
        print("  [Модель вернула пустой ответ]")
    else:
        print(answer)
    sep()
    cost_str = f"{cost:.4f} ₽" if cost > 0 else "бесплатно"
    finish = usage.get("finish_reason", "?")
    print(f"  Провайдер : {provider_name}")
    print(f"  Модель    : {model_label}")
    print(f"  t={temperature}  max_tokens={max_tokens}")
    print(f"  Токены    : вход={usage.get('prompt_tokens','?')}  выход={usage.get('completion_tokens','?')}  всего={usage.get('total_tokens','?')}")
    print(f"  Стоимость : {cost_str}")
    print(f"  Причина завершения: {finish}")
    if finish == "length":
        print(f"  ⚠ Ответ обрезан (достигнут лимит max_tokens={max_tokens}). Увеличьте max_tokens для полного ответа.")
    sep("═")

# ─── Сохранение в Markdown ────────────────────────────────────────────────────

def save_markdown(
    prompt: dict,
    system_msg: str,
    provider_name: str,
    model_id: str,
    model_label: str,
    temperature: float,
    max_tokens: int,
    question: str,
    answer: str,
    usage: dict,
    cost: float,
) -> str:
    OUTPUT_DIR.mkdir(exist_ok=True)
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    human_time = now.strftime("%Y-%m-%d %H:%M:%S")
    prompt_id = prompt.get("prompt_id", "case")
    path = OUTPUT_DIR / f"case_{prompt_id}_{timestamp}.md"

    cost_str = f"{cost:.4f} ₽" if cost > 0 else "бесплатно"
    finish = usage.get("finish_reason", "?")
    truncated = finish == "length"

    lines = [
        f"# {prompt.get('name', prompt_id)} — {human_time}",
        "",
        "## Параметры запуска",
        "",
        "| Параметр | Значение |",
        "| --- | --- |",
        f"| Промпт | {prompt.get('name', prompt_id)} v{prompt.get('version','')} |",
        f"| Категория | {prompt.get('category', '')} |",
        f"| Файл промпта | {prompt['_file']} |",
        f"| Провайдер | {provider_name} |",
        f"| Модель (label) | {model_label} |",
        f"| Модель (id) | {model_id} |",
        f"| Temperature | {temperature} |",
        f"| Max tokens | {max_tokens} |",
        f"| Токены вход | {usage.get('prompt_tokens', '?')} |",
        f"| Токены выход | {usage.get('completion_tokens', '?')} |",
        f"| Токены всего | {usage.get('total_tokens', '?')} |",
        f"| Причина завершения | {finish} |",
        f"| Стоимость | {cost_str} |",
        "",
    ]

    if truncated:
        lines += [
            f"> ⚠️ **Ответ обрезан** — достигнут лимит `max_tokens={max_tokens}`.",
            "> Повторите запрос с большим значением max_tokens для получения полного ответа.",
            "",
        ]
    if not answer:
        lines += [
            "> ⚠️ **Модель вернула пустой ответ.** Возможные причины: модель недоступна,",
            "> запрос заблокирован или ответ пришёл в нестандартном поле.",
            "",
        ]

    lines += [
        "---",
        "",
        "## Системный промпт",
        "",
        f"```\n{system_msg}\n```",
        "",
        "---",
        "",
        "## Вопрос пользователя",
        "",
        question,
        "",
        "---",
        "",
        "## Ответ модели",
        "",
        answer,
        "",
    ]

    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path.resolve())

# ─── Основной цикл ────────────────────────────────────────────────────────────

def run() -> None:
    print("\n" + "═" * 64)
    print("  CASE PROMPTER — тестирование системных промптов")
    print("═" * 64)

    all_prompts = load_prompt_files()
    selected_prompts = pick_prompts(all_prompts)
    provider_key, model_id, model_dict = pick_provider_and_model()
    temperature, max_tokens = pick_params(model_dict)

    provider_name = PROVIDERS[provider_key]["name"]
    model_label   = model_dict["label"]

    # Для каждого выбранного промпта — свой вопрос и запрос
    for prompt in selected_prompts:
        system_msg = build_system_message(prompt)
        question   = pick_user_question(prompt)

        if not question:
            print("  Вопрос пустой — промпт пропущен.")
            continue

        prompt_name = prompt.get("name", prompt["_file"])
        sep("═")
        print(f"  Отправка запроса: {prompt_name} → {model_label} | t={temperature}")
        sep("═")

        try:
            answer, usage = openai_client.chat(
                provider_key=provider_key,
                model_id=model_id,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user",   "content": question},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as e:
            print(f"  Ошибка API: {e}")
            continue

        cost = calc_cost(usage, model_dict)

        print_result(
            prompt_name=prompt_name,
            provider_name=provider_name,
            model_label=model_label,
            temperature=temperature,
            max_tokens=max_tokens,
            question=question,
            answer=answer,
            usage=usage,
            cost=cost,
        )

        out_path = save_markdown(
            prompt=prompt,
            system_msg=system_msg,
            provider_name=provider_name,
            model_id=model_id,
            model_label=model_label,
            temperature=temperature,
            max_tokens=max_tokens,
            question=question,
            answer=answer,
            usage=usage,
            cost=cost,
        )
        print(f"\n  Сохранено → {out_path}\n")

        # Предложить повторить с другими параметрами
        while True:
            again = ask("  Повторить этот промпт с другими параметрами? [y/N]: ", "n").lower()
            if again != "y":
                break

            # Выбор: сменить модель или только параметры
            change_model = ask("  Сменить провайдера/модель? [y/N]: ", "n").lower()
            if change_model == "y":
                provider_key, model_id, model_dict = pick_provider_and_model()
                provider_name = PROVIDERS[provider_key]["name"]
                model_label   = model_dict["label"]

            temperature, max_tokens = pick_params(model_dict)

            sep("═")
            print(f"  Повтор: {prompt_name} → {model_label} | t={temperature}")
            sep("═")

            try:
                answer, usage = openai_client.chat(
                    provider_key=provider_key,
                    model_id=model_id,
                    messages=[
                        {"role": "system", "content": system_msg},
                        {"role": "user",   "content": question},
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            except Exception as e:
                print(f"  Ошибка API: {e}")
                break

            cost = calc_cost(usage, model_dict)

            print_result(
                prompt_name=prompt_name,
                provider_name=provider_name,
                model_label=model_label,
                temperature=temperature,
                max_tokens=max_tokens,
                question=question,
                answer=answer,
                usage=usage,
                cost=cost,
            )

            out_path = save_markdown(
                prompt=prompt,
                system_msg=system_msg,
                provider_name=provider_name,
                model_id=model_id,
                model_label=model_label,
                temperature=temperature,
                max_tokens=max_tokens,
                question=question,
                answer=answer,
                usage=usage,
                cost=cost,
            )
            print(f"\n  Сохранено → {out_path}\n")


if __name__ == "__main__":
    run()
