"""
Telegram bot — multi-provider AI chat with per-user context.
Commands:
  /start   — welcome + setup wizard
  /setup   — choose provider, model, temperature, max_tokens
  /info    — current session settings
  /clear   — clear conversation context
  /report  — model runs report table
  /help    — help message
"""
import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
)

import context_manager as cm
import openai_client
from config import BOT_TOKEN, PROVIDERS, DEFAULT_TEMPERATURE, DEFAULT_MAX_TOKENS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ── run log for /report ────────────────────────────────────────────────────────
# Each entry: {user_id, provider, model, temperature, max_tokens, run_no,
#              prompt_tokens, completion_tokens, total_tokens, finish_reason}
run_log: list[dict] = []
_run_counters: dict[str, int] = {}  # key = f"{user_id}:{model_id}"


def _next_run(user_id: int, model_id: str) -> int:
    key = f"{user_id}:{model_id}"
    _run_counters[key] = _run_counters.get(key, 0) + 1
    return _run_counters[key]


# ── FSM states ─────────────────────────────────────────────────────────────────
class Setup(StatesGroup):
    provider = State()
    model = State()
    temperature = State()
    max_tokens = State()


# ── keyboards ──────────────────────────────────────────────────────────────────
def kb_providers() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=v["name"], callback_data=f"prov:{k}")]
        for k, v in PROVIDERS.items()
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def kb_models(provider_key: str) -> InlineKeyboardMarkup:
    models = PROVIDERS[provider_key]["models"]
    buttons = [
        [InlineKeyboardButton(text=m["label"], callback_data=f"model:{i}")]
        for i, m in enumerate(models)
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ── /start ─────────────────────────────────────────────────────────────────────
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await message.answer(
        "👋 Привет! Я AI-бот с поддержкой нескольких провайдеров.\n\n"
        "Сначала выбери провайдера:",
        reply_markup=kb_providers(),
    )
    await state.set_state(Setup.provider)


# ── /setup ─────────────────────────────────────────────────────────────────────
@dp.message(Command("setup"))
async def cmd_setup(message: Message, state: FSMContext):
    await message.answer("Выбери провайдера:", reply_markup=kb_providers())
    await state.set_state(Setup.provider)


# ── provider chosen ────────────────────────────────────────────────────────────
@dp.callback_query(Setup.provider, F.data.startswith("prov:"))
async def cb_provider(call: CallbackQuery, state: FSMContext):
    provider_key = call.data.split(":")[1]
    await state.update_data(provider=provider_key)
    await call.message.edit_text(
        f"Провайдер: <b>{PROVIDERS[provider_key]['name']}</b>\nВыбери модель:",
        reply_markup=kb_models(provider_key),
        parse_mode="HTML",
    )
    await state.set_state(Setup.model)


# ── model chosen ───────────────────────────────────────────────────────────────
@dp.callback_query(Setup.model, F.data.startswith("model:"))
async def cb_model(call: CallbackQuery, state: FSMContext):
    idx = int(call.data.split(":")[1])
    data = await state.get_data()
    provider_key = data["provider"]
    model = PROVIDERS[provider_key]["models"][idx]
    await state.update_data(model=model)

    tlo, thi = model["temp_range"]
    await call.message.edit_text(
        f"Модель: <b>{model['label']}</b>\n"
        f"Контекст: {model['context']} | Max tokens: {model['max_tokens_limit']}\n\n"
        f"Введи температуру ({tlo}–{thi}), или отправь <code>.</code> для дефолта ({DEFAULT_TEMPERATURE}):",
        parse_mode="HTML",
    )
    await state.set_state(Setup.temperature)


# ── temperature input ──────────────────────────────────────────────────────────
@dp.message(Setup.temperature)
async def fsm_temperature(message: Message, state: FSMContext):
    data = await state.get_data()
    model = data["model"]
    tlo, thi = model["temp_range"]

    text = message.text.strip()
    if text == ".":
        temp = DEFAULT_TEMPERATURE
    else:
        try:
            temp = float(text)
            temp = max(tlo, min(thi, temp))
        except ValueError:
            await message.answer(f"Введи число от {tlo} до {thi}, или <code>.</code> для дефолта.", parse_mode="HTML")
            return

    await state.update_data(temperature=temp)
    await message.answer(
        f"Температура: <b>{temp}</b>\n\n"
        f"Введи max_tokens (1–{model['max_tokens_limit']}), или <code>.</code> для дефолта ({DEFAULT_MAX_TOKENS}):",
        parse_mode="HTML",
    )
    await state.set_state(Setup.max_tokens)


# ── max_tokens input ───────────────────────────────────────────────────────────
@dp.message(Setup.max_tokens)
async def fsm_max_tokens(message: Message, state: FSMContext):
    data = await state.get_data()
    model = data["model"]

    text = message.text.strip()
    if text == ".":
        max_tok = DEFAULT_MAX_TOKENS
    else:
        try:
            max_tok = int(text)
            max_tok = max(1, min(model["max_tokens_limit"], max_tok))
        except ValueError:
            await message.answer(f"Введи целое число 1–{model['max_tokens_limit']}, или <code>.</code>.", parse_mode="HTML")
            return

    provider_key = data["provider"]
    model_obj = data["model"]
    temperature = data["temperature"]

    cm.set_session(message.from_user.id, provider_key, model_obj, temperature, max_tok)
    await state.clear()

    await message.answer(
        f"✅ Сессия настроена!\n\n"
        f"Провайдер: <b>{PROVIDERS[provider_key]['name']}</b>\n"
        f"Модель: <b>{model_obj['label']}</b>\n"
        f"Температура: <b>{temperature}</b>\n"
        f"Max tokens: <b>{max_tok}</b>\n\n"
        f"Просто пиши — я отвечу 🤖\n"
        f"<i>«очистить контекст»</i> — сбросить историю диалога.",
        parse_mode="HTML",
    )


# ── /info ──────────────────────────────────────────────────────────────────────
@dp.message(Command("info"))
async def cmd_info(message: Message):
    uid = message.from_user.id
    ctx = cm.get_context(uid)
    if not cm.is_configured(uid):
        await message.answer("Сессия не настроена. Используй /setup.")
        return
    p = PROVIDERS[ctx["provider"]]
    await message.answer(
        f"📋 <b>Текущая сессия</b>\n\n"
        f"Провайдер: {p['name']}\n"
        f"Модель: {ctx['model']['label']}\n"
        f"Температура: {ctx['temperature']}\n"
        f"Max tokens: {ctx['max_tokens']}\n"
        f"Сообщений в контексте: {len(ctx['messages'])}",
        parse_mode="HTML",
    )


# ── /clear ─────────────────────────────────────────────────────────────────────
@dp.message(Command("clear"))
async def cmd_clear(message: Message):
    cm.clear_context(message.from_user.id)
    await message.answer("🗑 Контекст очищен.")


# ── /report ────────────────────────────────────────────────────────────────────
@dp.message(Command("report"))
async def cmd_report(message: Message):
    if not run_log:
        await message.answer("Пока нет данных. Отправь хотя бы один запрос.")
        return

    header = (
        "📊 Отчёт о работе моделей\n\n"
        "Модель | Temp | MaxTok | # | Эффект | Токены (in/out) | Стоимость\n"
        "─" * 55
    )
    rows = [header]
    for r in run_log:
        total = r.get("total_tokens", "?")
        p_tok = r.get("prompt_tokens", "?")
        c_tok = r.get("completion_tokens", "?")
        cost  = r.get("cost_rub", 0.0)
        cost_str = f"~{cost:.4f}₽" if cost > 0 else "бесплатно"
        finish = r.get("finish_reason", "?")

        rows.append(
            f"{r['model_label']}\n"
            f"  Temp: {r['temperature']}  MaxTok: {r['max_tokens']}  #{r['run_no']}\n"
            f"  Эффект: {r['effect']}  Finish: {finish}\n"
            f"  Токены: {total} (in {p_tok} / out {c_tok})\n"
            f"  Стоимость: {cost_str}\n"
            f"  Провайдер: {r['provider']}"
        )

    await message.answer("\n\n".join(rows))


# ── /help ──────────────────────────────────────────────────────────────────────
@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "<b>Команды:</b>\n"
        "/start — начать / выбрать провайдер и модель\n"
        "/setup — настроить сессию заново\n"
        "/info — текущие настройки сессии\n"
        "/clear — очистить историю диалога\n"
        "/report — таблица прогонов моделей\n"
        "/help — эта справка\n\n"
        "<i>«очистить контекст»</i> — тоже сбрасывает историю",
        parse_mode="HTML",
    )


# ── main message handler ───────────────────────────────────────────────────────
@dp.message(F.text)
async def handle_message(message: Message, state: FSMContext):
    uid = message.from_user.id
    text = message.text.strip()

    # clear context shortcut
    if text.lower() in ("очистить контекст", "clear context"):
        cm.clear_context(uid)
        await message.answer("🗑 Контекст очищен.")
        return

    if not cm.is_configured(uid):
        await message.answer("Сначала настрой сессию — /setup")
        return

    ctx = cm.get_context(uid)
    provider_key = ctx["provider"]
    model = ctx["model"]

    cm.add_message(uid, "user", text)
    messages = list(ctx["messages"])  # snapshot

    await bot.send_chat_action(message.chat.id, "typing")

    try:
        reply, usage = openai_client.chat(
            provider_key=provider_key,
            model_id=model["id"],
            messages=messages,
            temperature=ctx["temperature"],
            max_tokens=ctx["max_tokens"],
        )
    except Exception as e:
        logger.exception("Chat error for user %d", uid)
        err_str = str(e)
        if "402" in err_str or "Insufficient balance" in err_str or "Недостаточно средств" in err_str:
            await message.answer(
                "❌ Недостаточно средств на балансе провайдера.\n"
                "Пополни баланс или выбери другого провайдера — /setup"
            )
        else:
            await message.answer(f"❌ Ошибка: {e}")
        ctx["messages"].pop()
        return

    cm.add_message(uid, "assistant", reply)

    # ── compute cost ──────────────────────────────────────────────────────────
    price_in  = model.get("price_in", 0.0)   # ₽ per 1K tokens
    price_out = model.get("price_out", 0.0)
    p_tok = usage.get("prompt_tokens", 0)
    c_tok = usage.get("completion_tokens", 0)
    cost = (p_tok / 1000 * price_in) + (c_tok / 1000 * price_out)

    # ── effect heuristic ──────────────────────────────────────────────────────
    # temperature < 0.4 → concise/factual, > 0.8 → creative
    temp = ctx["temperature"]
    if temp < 0.4:
        effect = "сжато/факт"
    elif temp > 0.8:
        effect = "креатив"
    else:
        effect = "баланс"

    # log run
    run_no = _next_run(uid, model["id"])
    run_log.append({
        "provider":          PROVIDERS[provider_key]["name"],
        "model_label":       model["label"],
        "model_id":          model["id"],
        "temperature":       temp,
        "max_tokens":        ctx["max_tokens"],
        "run_no":            run_no,
        "effect":            effect,
        "cost_rub":          cost,
        **usage,
    })

    # footer
    token_info = ""
    if usage:
        cost_str = f"~{cost:.4f}₽" if cost > 0 else "бесплатно"
        token_info = (
            f"\n\n🔢 {usage.get('total_tokens', '?')} токенов "
            f"(in {usage.get('prompt_tokens', '?')} / out {usage.get('completion_tokens', '?')}) "
            f"· {model['id']} · t={temp} · {cost_str}"
        )

    await message.answer(reply + token_info)


# ── entry point ────────────────────────────────────────────────────────────────
async def main():
    logger.info("Bot starting...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
