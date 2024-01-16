from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain_community.chat_message_histories import StreamlitChatMessageHistory
from langchain_core.runnables import RunnableConfig
from langchain_core.tracers import LangChainTracer
from langchain_core.tracers.run_collector import RunCollectorCallbackHandler
from langchain_openai import OpenAI
from langsmith import Client
import streamlit as st
from streamlit_feedback import streamlit_feedback
import time

st.set_page_config(page_title="LangChain: Simple feedback", page_icon="🦜")
st.title("🦜 LangChain: Simple feedback")

openai_api_key = st.secrets.get("OPENAI_API_KEY")
if not openai_api_key:
    openai_api_key = st.sidebar.text_input("OpenAI API Key", type="password")
langchain_api_key = st.secrets.get("LANGCHAIN_API_KEY")
if not langchain_api_key:
    langchain_api_key = st.sidebar.text_input("LangChain API Key", type="password")
project = st.sidebar.text_input("LangSmith Project", value="default")
if not langchain_api_key or not openai_api_key:
    st.warning("Please add an OpenAI API Key and LangChain API Key to continue")
    st.stop()

# Customize if needed
langchain_endpoint = "https://api.smith.langchain.com"
client = Client(api_url=langchain_endpoint, api_key=langchain_api_key)
ls_tracer = LangChainTracer(project_name=project, client=client)
run_collector = RunCollectorCallbackHandler()
cfg = RunnableConfig()
cfg["callbacks"] = [ls_tracer, run_collector]

msgs = StreamlitChatMessageHistory()
memory = ConversationBufferMemory(chat_memory=msgs)
llm_chain = ConversationChain(llm=OpenAI(openai_api_key=openai_api_key), memory=memory)

reset_history = st.sidebar.button("Reset chat history")
if len(msgs.messages) == 0 or reset_history:
    msgs.clear()
    msgs.add_ai_message("How can I help you?")
    st.session_state["last_run"] = None

avatars = {"human": "user", "ai": "assistant"}
for msg in msgs.messages:
    st.chat_message(avatars[msg.type]).write(msg.content)

if input := st.chat_input(placeholder="Tell me a joke about a shark?"):
    st.chat_message("user").write(input)
    with st.chat_message("assistant"):
        response = llm_chain.invoke(input, cfg)
        st.write(response["response"])
        st.session_state.last_run = run_collector.traced_runs[0].id


@st.cache_data(ttl="2h", show_spinner=False)
def get_run_url(run_id):
    time.sleep(1)
    return client.read_run(run_id).url


if st.session_state.get("last_run"):
    run_url = get_run_url(st.session_state.last_run)
    st.sidebar.markdown(f"[Latest Trace: 🛠️]({run_url})")
    feedback = streamlit_feedback(
        feedback_type="faces",
        optional_text_label="[Optional] Please provide an explanation",
        key=f"feedback_{st.session_state.last_run}",
    )
    if feedback:
        scores = {"😀": 1, "🙂": 0.75, "😐": 0.5, "🙁": 0.25, "😞": 0}
        client.create_feedback(
            st.session_state.last_run,
            feedback["type"],
            score=scores[feedback["score"]],
            comment=feedback.get("text", None),
        )
        st.toast("Feedback recorded!", icon="📝")
