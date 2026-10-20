import json
import streamlit as st
from google import genai
from google.genai import types

# 1. Базовая конфигурация страницы
st.set_page_config(
    page_title="Софтлайн Образование | Навигатор & Тренажёр",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Стили оформления
st.markdown("""
<style>
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    .block-container {
        padding-top: 3.5rem !important;
        padding-bottom: 6rem !important;
        max-width: 1100px !important;
    }
    div[data-testid="stChatMessage"] {
        background-color: rgba(255, 255, 255, 0.02) !important;
        border: 1px solid rgba(255, 255, 255, 0.06) !important;
        border-radius: 12px !important;
        padding: 1.2rem !important;
        margin-bottom: 0.9rem !important;
    }
    .stButton button {
        border-radius: 10px !important;
        background: rgba(255, 255, 255, 0.04) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        transition: all 0.2s ease-in-out;
    }
    .stButton button:hover {
        background: rgba(255, 255, 255, 0.1) !important;
        border-color: rgba(255, 255, 255, 0.25) !important;
    }
</style>
""", unsafe_allow_html=True)

# 3. Загрузка базы знаний
@st.cache_data
def load_knowledge_base():
    try:
        with open("knowledge_base.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            return data
    except Exception as e:
        return {"disclaimer": "⚠️ Ошибка загрузки базы знаний", "scenarios": {}}

kb_data = load_knowledge_base()
knowledge_base_text = json.dumps(kb_data, ensure_ascii=False, indent=2)
disclaimer_text = kb_data.get("disclaimer", "⚠️ Обратите внимание: ответы бота носят исключительно информационный характер и не заменяют официальные требования вузов и работодателей.")

# 4. Поиск по официальным источникам
def search_official_sources(query: str, max_results: int = 4):
    try:
        from duckduckgo_search import DDGS
        refined_query = f"{query} официальный сайт приёмная комиссия вуз стажировка образование"
        results = DDGS().text(refined_query, region="ru-ru", max_results=max_results)
        
        snippets = []
        for r in results:
            snippets.append(f"📌 **{r.get('title')}**\nИсточник: {r.get('href')}\nВыдержка: {r.get('body')}\n")
        return "\n".join(snippets)
    except Exception:
        return ""

# 5. Инициализация сессий
if "chat_sessions" not in st.session_state:
    st.session_state.chat_sessions = {
        "Диалог 1": [
            {
                "role": "assistant",
                "content": (
                    "👋 **Привет! Я образовательный AI-наставник Софтлайн.**\n\n"
                    "Я помогу тебе пройти путь от выбора вуза до первой работы в IT:\n"
                    "• **Навигатор:** подбор вузов РФ по баллам ЕГЭ, проверка аккредитации, общежитий и стажировок.\n"
                    "• **Тренажёр:** решение реальных каверзных кейсов с экспертной обратной связью.\n\n"
                    f"*{disclaimer_text}*"
                ),
                "is_button": False
            }
        ]
    }

if "current_chat" not in st.session_state:
    st.session_state.current_chat = "Диалог 1"

if "api_key" not in st.session_state:
    st.session_state.api_key = ""
if "gemini_model" not in st.session_state:
    st.session_state.gemini_model = "gemini-3.8-flash"
if "creativity" not in st.session_state:
    st.session_state.creativity = 0.4
if "detail_mode" not in st.session_state:
    st.session_state.detail_mode = "Подробный разбор с примерами"
if "use_search" not in st.session_state:
    st.session_state.use_search = True

# 6. Боковая панель: Управление диалогами и Поддержка
with st.sidebar:
    st.subheader("💬 История диалогов")
    if st.button("➕ Новый чат", use_container_width=True, key="btn_create_new_chat"):
        new_name = f"Диалог {len(st.session_state.chat_sessions) + 1}"
        st.session_state.chat_sessions[new_name] = [
            {
                "role": "assistant", 
                "content": "Новая сессия начата. Задайте вопрос по поступлению или карьере!", 
                "is_button": False
            }
        ]
        st.session_state.current_chat = new_name
        st.rerun()

    chat_names = list(st.session_state.chat_sessions.keys())
    current_idx = chat_names.index(st.session_state.current_chat) if st.session_state.current_chat in chat_names else 0
    selected_chat = st.selectbox(
        "Выбрать сессию:",
        chat_names,
        index=current_idx,
        key="select_active_chat",
        label_visibility="collapsed"
    )
    if selected_chat != st.session_state.current_chat:
        st.session_state.current_chat = selected_chat
        st.rerun()

    current_messages = st.session_state.chat_sessions[st.session_state.current_chat]

    st.divider()
    chat_export = "\n\n".join([f"{m['role'].upper()}:\n{m['content']}" for m in current_messages if not m.get("is_button", False)])
    st.download_button("💾 Сохранить диалог (.txt)", chat_export, f"{st.session_state.current_chat}.txt", use_container_width=True, key="btn_download_chat")
    
    if st.button("🧹 Очистить чат", use_container_width=True, key="btn_clear_chat"):
        st.session_state.chat_sessions[st.session_state.current_chat] = [
            {"role": "assistant", "content": "Диалог сброшен. Готов отвечать на вопросы!", "is_button": False}
        ]
        st.rerun()

    st.divider()

    # Блок технической поддержки с отправкой на почту den13ast@mail.ru
    with st.popover("🆘 Поддержка и кураторы", use_container_width=True):
        st.markdown("#### ✉️ Связь с наставником")
        st.caption("Напиши свой вопрос или сообщи об ошибке — письмо придёт куратору на почту:")
        
        support_html = """
        <form action="https://formsubmit.co/den13ast@mail.ru" method="POST" target="_blank">
            <input type="hidden" name="_subject" value="Новое обращение из AI-Тренажёра Софтлайн!">
            <input type="hidden" name="_captcha" value="false">
            <div style="margin-bottom: 10px;">
                <label style="font-size: 13px; color: #ccc;">Твоё имя или ник:</label><br>
                <input type="text" name="Имя_пользователя" required style="width: 100%; padding: 8px; border-radius: 6px; border: 1px solid #444; background: #222; color: #fff;">
            </div>
            <div style="margin-bottom: 10px;">
                <label style="font-size: 13px; color: #ccc;">Твой контакт (Telegram / Email):</label><br>
                <input type="text" name="Контакты" required style="width: 100%; padding: 8px; border-radius: 6px; border: 1px solid #444; background: #222; color: #fff;">
            </div>
            <div style="margin-bottom: 12px;">
                <label style="font-size: 13px; color: #ccc;">Твой вопрос или проблема:</label><br>
                <textarea name="Сообщение" rows="4" required style="width: 100%; padding: 8px; border-radius: 6px; border: 1px solid #444; background: #222; color: #fff;"></textarea>
            </div>
            <button type="submit" style="width: 100%; background: #007bff; color: white; border: none; padding: 10px; border-radius: 6px; cursor: pointer; font-weight: bold;">
                ✉️ Отправить на почту
            </button>
        </form>
        """
        st.components.v1.html(support_html, height=330)

    st.markdown("---")
    st.caption(disclaimer_text)

# 7. Верхняя панель
top_col_left, top_col_guide, top_col_settings = st.columns([2.5, 0.9, 0.9])

with top_col_left:
    app_category = st.radio(
        "Категория:",
        ["🎓 Обычный (Навигатор)", "🎯 Интерактивный тренажёр"],
        horizontal=True,
        key="radio_category",
        label_visibility="collapsed"
    )

with top_col_guide:
    with st.popover("📖 Инструкция", use_container_width=True):
        st.markdown("""
        ### 📖 Руководство пользователя
        
        **1. Быстрый старт:**
        * Откройте **«⚙️ Настройки ИИ»** и введите ваш API-ключ Gemini.
        
        ---
        **2. Режимы работы:**
        * **🎓 Обычный (Навигатор)** — подбор вузов РФ по баллам ЕГЭ, проверка общежитий и военной кафедры, аудит портфолио и поиск стажировок.
        * **🎯 Интерактивный тренажёр** — решение проблемных кейсов (выбор вуза, собеседование, адаптация).
        """)

with top_col_settings:
    with st.popover("⚙️ Настройки ИИ", use_container_width=True):
        st.markdown("#### ⚙️ Параметры Gemini и поиска")
        
        st.session_state.api_key = st.text_input(
            "Введите свой API ключ", 
            value=st.session_state.api_key, 
            type="password", 
            placeholder="Введите свой API ключ",
            key="input_gemini_key"
        )
        st.markdown("[🔑 Получить ключ Google Gemini](https://aistudio.google.com/app/apikey)")
        
        st.session_state.gemini_model = st.selectbox(
            "Модель Gemini:",
            ["gemini-3.8-flash", "gemini-3.5-flash"],
            index=0,
            key="select_gemini_model"
        )

        st.session_state.detail_mode = st.radio(
            "Глубина ответов:",
            ["Подробный разбор с примерами", "Кратко и по делу"],
            index=0 if "Подробный" in st.session_state.detail_mode else 1,
            key="radio_detail_mode"
        )
        
        st.session_state.use_search = st.toggle(
            "🌐 Поиск по официальным сайтам",
            value=st.session_state.use_search,
            key="toggle_use_search"
        )
        
        st.session_state.creativity = st.slider(
            "🎨 Креативность ответа:",
            0.0, 1.0, float(st.session_state.creativity), 0.1,
            key="slider_creativity"
        )

# 8. Содержимое категории
is_trainer_mode = (app_category == "🎯 Интерактивный тренажёр")

if is_trainer_mode:
    st.markdown("### 🎯 Интерактивный тренажёр кейсов")
    st.caption("Отработка проблемных ситуаций. Бот оценит твой ответ и предложит экспертное улучшение.")
    
    scenarios_data = kb_data.get("scenarios", {})
    t_tab1, t_tab2, t_tab3 = st.tabs(["🎓 1. Выбор вуза", "💼 2. Собеседование", "🚀 3. Адаптация в IT"])
    quick_prompt = None

    with t_tab1:
        c1, c2, c3 = st.columns(3)
        cases_1 = scenarios_data.get("1", {}).get("cases", [])
        if len(cases_1) > 0 and c1.button("Кейс 1: Внутренняя кухня", use_container_width=True, key="btn_c1_1"):
            quick_prompt = f"Запусти кейс: {cases_1[0]['question']}"
        if len(cases_1) > 1 and c2.button("Кейс 2: Риски баллов", use_container_width=True, key="btn_c1_2"):
            quick_prompt = f"Запусти кейс: {cases_1[1]['question']}"
        if len(cases_1) > 2 and c3.button("Кейс 3: Аккредитация", use_container_width=True, key="btn_c1_3"):
            quick_prompt = f"Запусти кейс: {cases_1[2]['question']}"

    with t_tab2:
        c4, c5, c6 = st.columns(3)
        cases_2 = scenarios_data.get("2", {}).get("cases", [])
        if len(cases_2) > 0 and c4.button("Кейс 1: Провал в проекте", use_container_width=True, key="btn_c2_1"):
            quick_prompt = f"Запусти кейс: {cases_2[0]['question']}"
        if len(cases_2) > 1 and c5.button("Кейс 2: Пустое резюме", use_container_width=True, key="btn_c2_2"):
            quick_prompt = f"Запусти кейс: {cases_2[1]['question']}"
        if len(cases_2) > 2 and c6.button("Кейс 3: Сложный вопрос", use_container_width=True, key="btn_c2_3"):
            quick_prompt = f"Запусти кейс: {cases_2[2]['question']}"

    with t_tab3:
        c7, c8, c9 = st.columns(3)
        cases_3 = scenarios_data.get("3", {}).get("cases", [])
        if len(cases_3) > 0 and c7.button("Кейс 1: Застрял на задаче", use_container_width=True, key="btn_c3_1"):
            quick_prompt = f"Запусти кейс: {cases_3[0]['question']}"
        if len(cases_3) > 1 and c8.button("Кейс 2: Неясные требования", use_container_width=True, key="btn_c3_2"):
            quick_prompt = f"Запусти кейс: {cases_3[1]['question']}"
        if len(cases_3) > 2 and c9.button("Кейс 3: Ошибка в git/стенде", use_container_width=True, key="btn_c3_3"):
            quick_prompt = f"Запусти кейс: {cases_3[2]['question']}"

else:
    st.markdown("### 🎓 Карьерный и образовательный навигатор")
    st.caption("Поиск вузов по РФ, анализ портфолио и подбор вакансий/стажировок.")
    
    col_n1, col_n2 = st.columns(2)
    quick_prompt = None
    with col_n1:
        if st.button("🏛 Подобрать вуз под портфолио и баллы", use_container_width=True, key="btn_nav_vuz"):
            quick_prompt = "Помоги подобрать вузы в РФ. Кратко спроси у меня нужные данные: город, баллы ЕГЭ (до 100 за предмет), направление и наличие проектов."
    with col_n2:
        if st.button("💼 Как найти стажировку без опыта", use_container_width=True, key="btn_nav_intern"):
            quick_prompt = "Расскажи подробно, как студенту или абитуриенту найти первую стажировку в IT по РФ (включая проекты Софтлайн)."

st.divider()

# 9. Отрисовка сообщений
chat_box = st.container()
with chat_box:
    for idx, message in enumerate(current_messages):
        if message["role"] == "assistant":
            with st.chat_message("assistant"):
                st.markdown(message["content"])
        elif message["role"] == "user" and not message.get("is_button", False):
            with st.chat_message("user"):
                st.markdown(message["content"])

# 10. Ввод сообщений
user_input = st.chat_input(
    "Введите ваш ответ на кейс тренажёра..." if is_trainer_mode else "Задайте вопрос о вузах, экзаменах, стажировках...",
    key="chat_input_box"
)

active_prompt = None
is_button_action = False

if quick_prompt:
    active_prompt = quick_prompt
    is_button_action = True
elif user_input:
    active_prompt = user_input
    is_button_action = False

if active_prompt:
    current_messages.append({
        "role": "user",
        "content": active_prompt,
        "is_button": is_button_action
    })

    if not is_button_action:
        with chat_box:
            with st.chat_message("user"):
                st.markdown(active_prompt)

    if not st.session_state.api_key:
        with chat_box:
            with st.chat_message("assistant"):
                st.error("Пожалуйста, укажите API-ключ Gemini в окне «⚙️ Настройки ИИ»!")
    else:
        with chat_box:
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                
                web_context = ""
                if st.session_state.use_search and not is_trainer_mode:
                    with st.spinner("🔍 Проверяю официальные сайты вузов..."):
                        web_context = search_official_sources(active_prompt)

                with st.spinner("AI готовит ответ..."):
                    if is_trainer_mode:
                        mode_instruction = """
Ты работаешь в режиме «ТРЕНАЖЁР-ЭКЗАМЕНАТОР».
Твоя цель — проверить и разобрать ответ пользователя на проблемный кейс.
Если пользователь только что нажал кнопку запуска кейса, задай вопрос кейса живо и пригласи к ответу.
Если пользователь ответил на кейс, обязательно структурируй разбор строго по 3 блокам:
1. «Это верно»: похвали за правильные мысли и точные акценты.
2. «Вот что можно улучшить»: мягко укажи на упущенные риски, типичные ошибки новичка и слабую аргументацию.
3. «Вот удачный пример ответа»: покажи готовую экспертную формулировку ответа из базы знаний.
Тон: доброжелательный, опытный старший наставник (IT-ментор компании «Софтлайн»).
"""
                    else:
                        detail_instruction = (
                            "Отвечай глубоко, пошагово, с конкретными примерами и кликабельными ссылками на официальные источники [Название](URL)."
                            if "Подробный" in st.session_state.detail_mode
                            else "Отвечай структурированно, кратко и строго по пунктам."
                        )
                        mode_instruction = f"""
Ты работаешь в режиме «ОБЫЧНЫЙ НАВИГАТОР». Выдавай проверенную информацию по вузам, баллам, общежитиям, аккредитации и стажировкам.
{detail_instruction}
"""

                    system_instruction = f"""
Ты — специализированный виртуальный AI-наставник и карьерный консультант компании «Софтлайн Решения».

КРИТИЧЕСКИ ВАЖНОЕ ПРАВИЛО ТЕМАТИКИ:
Ты отвечаешь ИСКЛЮЧИТЕЛЬНО на темы ОБРАЗОВАНИЯ, ВУЗОВ, КОЛЛЕДЖЕЙ, ЭКЗАМЕНОВ (ЕГЭ/ОГЭ/ДВИ), ПОРТФОЛИО, СТАЖИРОВОК И КАРЬЕРЫ В IT.
На любые посторонние темы (игры, кино, рецепты, быт) вежливо откажи и верни диалог к теме учебы.

ПРАВИЛА РОССИЙСКОЙ СИСТЕМЫ ОБРАЗОВАНИЯ:
- Баллы ЕГЭ строго от 0 до 100 за один предмет. Сумма за 3 предмета — до 300 (до 310 с учетом личных достижений).

ЕСЛИ ПОЛЬЗОВАТЕЛЬ ПРОСИТ ПОМОЩЬ ЧЕЛОВЕКА ИЛИ ТЕХПОДДЕРЖКУ:
Вежливо подскажи, что ты AI-ассистент, и направь его в форму поддержки в боковой панели (кнопка «🆘 Поддержка и кураторы»), либо предложи написать кураторам напрямую на почту den13ast@mail.ru.

БАЗА ЗНАНИЙ (JSON):
{knowledge_base_text}

ДАННЫЕ С ОФИЦИАЛЬНЫХ САЙТОВ:
{web_context if web_context else "Прямой поиск отключен или не требовался в этом режиме."}

{mode_instruction}

В конце ответа всегда добавляй короткое примечание:
«{disclaimer_text}»
"""
                    clean_key = st.session_state.api_key.strip()
                    context_messages = current_messages[-6:]

                    try:
                        client = genai.Client(api_key=clean_key)
                        
                        gemini_contents = []
                        for msg in context_messages:
                            role = "user" if msg["role"] == "user" else "model"
                            gemini_contents.append(
                                types.Content(
                                    role=role,
                                    parts=[types.Part.from_text(text=msg["content"])]
                                )
                            )

                        response = client.models.generate_content(
                            model=st.session_state.gemini_model,
                            contents=gemini_contents,
                            config=types.GenerateContentConfig(
                                system_instruction=system_instruction,
                                temperature=float(st.session_state.creativity),
                                max_output_tokens=2500,
                            )
                        )

                        bot_reply = response.text
                        message_placeholder.markdown(bot_reply)
                        current_messages.append({"role": "assistant", "content": bot_reply, "is_button": False})

                    except Exception as e:
                        message_placeholder.error(f"Ошибка вызова Gemini API: {e}")
