import streamlit as st
from characters import CHARACTERS
from model_chat import Character

st.set_page_config(page_title="Mindspace", page_icon="✶", layout="wide")

# ---------------------------------------------------------------------------
# Styling — dark, warm, Character.AI-ish. All CSS lives here, single file.
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400..600&family=Inter:wght@400;500;600&display=swap');

    html, body, [class*="css"]  {
        font-family: 'Inter', sans-serif;
    }

    .stApp {
        background: #0F1A1C;
        color: #EDE6D8;
    }

    h1, h2, h3 {
        font-family: 'Fraunces', serif !important;
        color: #EDE6D8 !important;
    }

    /* Character picker cards */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: #1B2C2F;
        border: 1px solid rgba(237, 230, 216, 0.1) !important;
        border-radius: 16px;
        transition: border-color 0.2s, transform 0.2s;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color: #7FA399 !important;
        transform: translateY(-2px);
    }

    .char-avatar {
        width: 52px;
        height: 52px;
        border-radius: 50%;
        background: rgba(217, 142, 142, 0.18);
        border: 1px solid rgba(217, 142, 142, 0.5);
        color: #D98E8E;
        font-family: 'Fraunces', serif;
        font-size: 1.3rem;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 10px;
    }

    .char-name {
        font-family: 'Fraunces', serif;
        font-size: 1.15rem;
        margin: 0 0 4px;
    }

    .eyebrow {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.78rem;
        letter-spacing: 0.05em;
        color: #7FA399;
        text-transform: lowercase;
        margin-bottom: 6px;
    }

    /* Chat bubbles */
    div[data-testid="stChatMessage"] {
        background: transparent;
    }

    /* Buttons */
    .stButton button {
        border-radius: 100px !important;
        border: 1px solid rgba(237, 230, 216, 0.15) !important;
        background: #1B2C2F !important;
        color: #EDE6D8 !important;
    }
    .stButton button:hover {
        border-color: #D98E8E !important;
        color: #D98E8E !important;
    }

    section[data-testid="stSidebar"] {
        background: #162427;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "active_character" not in st.session_state:
    st.session_state.active_character = None
if "character_instances" not in st.session_state:
    st.session_state.character_instances = {}
if "display_history" not in st.session_state:
    st.session_state.display_history = {}  # per-character list of {role, content} for rendering


def get_character_instance(char_id):
    """Lazily create and cache a Character() per id so its .history persists
    across reruns within the session."""
    if char_id not in st.session_state.character_instances:
        st.session_state.character_instances[char_id] = Character(char_id)
        st.session_state.display_history[char_id] = []
    return st.session_state.character_instances[char_id]


def go_to_character(char_id):
    st.session_state.active_character = char_id
    st.rerun()


def go_home():
    st.session_state.active_character = None
    st.rerun()


# ---------------------------------------------------------------------------
# View: Character select
# ---------------------------------------------------------------------------
def render_character_select():
    st.markdown('<p class="eyebrow">who do you want to talk to today?</p>', unsafe_allow_html=True)
    st.markdown("## Choose a voice")
    st.write("")

    char_ids = list(CHARACTERS.keys())

    if not char_ids:
        st.info(
            "No characters defined yet. Add some to `characters.py` — there's "
            "a template at the bottom of the file ready to fill in."
        )
        return

    cols = st.columns(3)
    for i, char_id in enumerate(char_ids):
        char = CHARACTERS[char_id]
        col = cols[i % 3]
        with col:
            with st.container(border=True):
                initial = char["name"][0].upper()
                st.markdown(f'<div class="char-avatar">{initial}</div>', unsafe_allow_html=True)
                st.markdown(f'<p class="char-name">{char["name"]}</p>', unsafe_allow_html=True)
                st.caption("Tap to start a conversation")
                if st.button("Start chat →", key=f"select_{char_id}", use_container_width=True):
                    go_to_character(char_id)


# ---------------------------------------------------------------------------
# View: Chat
# ---------------------------------------------------------------------------
def render_chat(char_id):
    char_data = CHARACTERS[char_id]
    character = get_character_instance(char_id)

    header_col1, header_col2 = st.columns([1, 8])
    with header_col1:
        if st.button("← back"):
            go_home()
    with header_col2:
        st.markdown(f"### {char_data['name']}")

    st.divider()

    history = st.session_state.display_history[char_id]

    for msg in history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_input = st.chat_input(f"Message {char_data['name']}...")

    if user_input:
        history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            try:
                full_reply = character.chat(user_input)
                st.markdown(full_reply)
            except Exception as e:
                full_reply = None
                st.error(
                    f"Couldn't reach the model: {e}\n\n"
                    f"Check that Ollama is running and that the model "
                    f"`{character.model}` has been pulled (`ollama pull {character.model}`)."
                )

        if full_reply is not None:
            history.append({"role": "assistant", "content": full_reply})


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
if st.session_state.active_character is None:
    render_character_select()
else:
    render_chat(st.session_state.active_character)
