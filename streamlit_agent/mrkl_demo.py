from pathlib import Path

import streamlit as st

from langchain import (
    LLMMathChain,
    OpenAI,
    SQLDatabase,
    SQLDatabaseChain,
)
from langchain.agents import AgentType
from langchain.agents import initialize_agent, Tool
from langchain.callbacks import StreamlitCallbackHandler
from langchain.utilities import DuckDuckGoSearchAPIWrapper

from streamlit_agent.callbacks.capturing_callback_handler import playback_callbacks
from streamlit_agent.clear_results import with_clear_container

DB_PATH = (Path(__file__).parent / "Chinook.db").absolute()

SAVED_SESSIONS = {
    "Who is Leo DiCaprio's girlfriend? What is her current age raised to the 0.43 power?": "leo.pickle",
    "What is the full name of the artist who recently released an album called "
    "'The Storm Before the Calm' and are they in the FooBar database? If so, what albums of theirs "
    "are in the FooBar database?": "alanis.pickle",
}

st.set_page_config(page_title="MRKL", page_icon="🦜", layout="wide", initial_sidebar_state="collapsed")

"# 🦜🔗 MRKL"

# Setup credentials in Streamlit
user_openai_api_key = st.sidebar.text_input(
    "OpenAI API Key", type="password", help="Set this to run your own custom questions."
)

if user_openai_api_key:
    openai_api_key = user_openai_api_key
    enable_custom = True
else:
    openai_api_key = "not_supplied"
    enable_custom = False

# Tools setup
llm = OpenAI(temperature=0, openai_api_key=openai_api_key, streaming=True)
search = DuckDuckGoSearchAPIWrapper()
llm_math_chain = LLMMathChain(llm=llm, verbose=True)
db = SQLDatabase.from_uri(f"sqlite:///{DB_PATH}")
db_chain = SQLDatabaseChain.from_llm(llm, db, verbose=True)
tools = [
    Tool(
        name="Search",
        func=search.run,
        description="useful for when you need to answer questions about current events. You should ask targeted questions",
    ),
    Tool(
        name="Calculator",
        func=llm_math_chain.run,
        description="useful for when you need to answer questions about math",
    ),
    Tool(
        name="FooBar DB",
        func=db_chain.run,
        description="useful for when you need to answer questions about FooBar. Input should be in the form of a question containing full context",
    ),
]

# Initialize agent
mrkl = initialize_agent(
    tools, llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, verbose=True
)

if "latest_user_input" not in st.session_state:
    st.session_state["latest_user_input"] = ""

if "latest_user_input_executed" not in st.session_state:
    st.session_state["latest_user_input_executed"] = False

if "dirty_state" not in st.session_state:
    st.session_state["dirty_state"] = "initial"

with st.form(key="form"):
    if not enable_custom:
        "Ask one of the sample questions, or enter your API Keys in the sidebar to ask your own custom questions."
    prefilled = st.selectbox("Sample questions", sorted(SAVED_SESSIONS.keys())) or ""
    mrkl_input = ""

    if enable_custom:
        user_input = st.text_input("Or, ask your own question")
    if not mrkl_input:
        user_input = prefilled
    submit_clicked = st.form_submit_button("Submit Question")

if submit_clicked:
    st.session_state["latest_user_input"] = user_input
    st.session_state["latest_user_input_executed"] = False

if st.session_state["dirty_state"] == "dirty":
    st.session_state["dirty_state"] = "initial"
    for i in range(10):
        st.empty()
    st.experimental_rerun()

if not st.session_state["latest_user_input_executed"] and st.session_state["dirty_state"] == "initial":
    if st.session_state["latest_user_input"]:
        st.chat_message("user").write(st.session_state["latest_user_input"])

        result_container = st.chat_message("assistant", avatar="🦜")
        st_callback = StreamlitCallbackHandler(result_container)

        # If we've saved this question, play it back instead of actually running LangChain
        # (so that we don't exhaust our API calls unnecessarily)
        if st.session_state["latest_user_input"] in SAVED_SESSIONS:
            session_name = SAVED_SESSIONS[st.session_state["latest_user_input"]]
            session_path = Path(__file__).parent / "runs" / session_name
            print(f"Playing saved session: {session_path}")
            answer = playback_callbacks(
                [st_callback], str(session_path), max_pause_time=3
            )
        else:
            answer = mrkl.run(st.session_state["latest_user_input"], callbacks=[st_callback])

        result_container.write(answer)
        st.session_state["dirty_state"] = "dirty"
        st.session_state["latest_user_input_executed"] = True

for i in range(10):
    st.empty()
