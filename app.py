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
            return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"База знаний не загружена: {e}"

knowledge_base_text = load_knowledge_base()

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
                    "Я специализируюсь **только на образовании и старте карьеры** в РФ:\n"
                    "• Подбор вузов и направлений по баллам ЕГЭ/ОГЭ и ДВИ.\n"
                    "• Оценка и сбор портфолио для поступления и стажировок.\n"
                    "• Поиск стажировок и вакансий для начинающих по всей России.\n\n"
                    "*Задайте вопрос в поле ввода или выберите одну из быстрых кнопок сценариев!*"
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

# 6. Боковая панель: Управление диалогами
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
        * **🎯 Интерактивный тренажёр** — решение кейсов: собеседования, выбор факультета, адаптация в IT.
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
    st.caption("Отработка реальных ситуаций: собеседование, выбор вуза, онбординг в IT-компании.")
    
    col_c1, col_c2, col_c3 = st.columns(3)
    quick_prompt = None
    with col_c1:
        if st.button("🎓 Кейс: Выбор вуза", use_container_width=True, key="btn_case_1"):
            quick_prompt = "Давай пройдем тренировочный кейс 1: Выбор вуза и поступление. Опиши проблемную ситуацию и задай кейс-вопрос."
    with col_c2:
        if st.button("💼 Кейс: Собеседование", use_container_width=True, key="btn_case_2"):
            quick_prompt = "Давай пройдем кейс 2: Собеседование и вопрос о провале в проекте. Задай вопрос работодателя."
    with col_c3:
        if st.button("🚀 Кейс: Адаптация стажёра", use_container_width=True, key="btn_case_3"):
            quick_prompt = "Давай пройдем кейс 3: Застрял на рабочей задаче в компании. Задай кейс."
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
    "Введите ваш ответ на кейс..." if is_trainer_mode else "Задайте вопрос о вузах, экзаменах, стажировках...",
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
                if st.session_state.use_search:
                    with st.spinner("🔍 Проверяю официальные сайты вузов..."):
                        web_context = search_official_sources(active_prompt)

                with st.spinner("AI готовит ответ..."):
                    detail_instruction = (
                        "Отвечай глубоко, пошагово, с конкретными примерами и кликабельными ссылками на официальные источники [Название](URL)."
                        if "Подробный" in st.session_state.detail_mode
                        else "Отвечай структурированно, кратко и строго по пунктам."
                    )

                    system_instruction = f"""
Ты — специализированный виртуальный AI-наставник и карьерный консультант компании «Софтлайн Решения».

КРИТИЧЕСКИ ВАЖНОЕ ПРАВИЛО ТЕМАТИКИ:
Ты отвечаешь ИСКЛЮЧИТЕЛЬНО на темы ОБРАЗОВАНИЯ, ВУЗОВ, КОЛЛЕДЖЕЙ, ЭКЗАМЕНОВ (ЕГЭ/ОГЭ/ДВИ), ПОРТФОЛИО, СТАЖИРОВОК И КАРЬЕРЫ В IT.
На любые посторонние темы (игры, кино, рецепты, быт) вежливо откажи и верни диалог к теме учебы.

ПРАВИЛА РОССИЙСКОЙ СИСТЕМЫ ОБРАЗОВАНИЯ:
- Баллы ЕГЭ строго от 0 до 100 за один предмет. Сумма за 3 предмета — до 300.

БАЗА ЗНАНИЙ (JSON):
{knowledge_base_text}

ДАННЫЕ С ОФИЦИАЛЬНЫХ САЙТОВ:
{web_context if web_context else "Прямой поиск отключен или не дал результатов."}

ТЕКУЩИЙ РЕЖИМ РАБОТЫ: {'ИНТЕРАКТИВНЫЙ ТРЕНАЖЁР' if is_trainer_mode else 'ОБЫЧНЫЙ НАВИГАТОР'}

ТРЕБОВАНИЯ К ДЕТАЛИЗАЦИИ:
{detail_instruction}
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