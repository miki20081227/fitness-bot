"""Клиент для работы с локальной Ollama"""
from openai import AsyncOpenAI
from config import OLLAMA_MODEL
from knowledge_base import FULL_KNOWLEDGE_BASE

client = AsyncOpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
)

SYSTEM_PROMPT = f"""Ты — AI-консультант фитнес-клуба "Атлет". Отвечай вежливо, кратко (2-4 предложения) и ТОЛЬКО на основе базы знаний ниже.

ПРАВИЛА:
1. Отвечай ТОЛЬКО по базе знаний. Если информации нет — честно скажи и предложи оставить заявку или позвать менеджера.
2. Не выдумывай цены, имена, расписание.
3. Будь дружелюбным, используй эмодзи умеренно.
4. Если вопрос сложный (жалоба, индивидуальный запрос) — предложи связаться с менеджером.
5. В конце ответа, если уместно, мягко предлагай записаться на пробную тренировку.

БАЗА ЗНАНИЙ:
{FULL_KNOWLEDGE_BASE}
"""


async def get_ai_answer(user_message: str, chat_history: list = None) -> str:
    try:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if chat_history:
            messages.extend(chat_history[-5:])
        messages.append({"role": "user", "content": user_message})

        response = await client.chat.completions.create(
            model=OLLAMA_MODEL,
            messages=messages,
            max_tokens=500,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ Ошибка Ollama: {e}")
        return (
            "⚠️ Извините, сейчас не могу получить ответ от AI-консультанта.\n\n"
            "Пожалуйста, оставьте заявку — менеджер свяжется с вами в ближайшее время!"
        )