import streamlit as st
import requests
from requests.exceptions import RequestException
import uuid
from langchain_groq import ChatGroq
import os
# ============================================================
# Configuration
# ============================================================
from dotenv import load_dotenv
load_dotenv()  

API_URL = "http://127.0.0.1:8000/api/v1/chat/stream/test"
TIMEOUT_SECONDS = 25  # Slightly higher than backend timeout
MAX_INPUT_LENGTH = 2000

def generate_thread_id():
    thread_id=str(uuid.uuid4())
    return thread_id

def reset_chat():
    thread_id=generate_thread_id()
    st.session_state['thread_id'] = thread_id
    # add_thread(thread_id)  # Add it to history right away so it shows up in sidebar
    # st.session_state['chat_titles'][thread_id] = "New Chat" # Default name
    st.session_state['history']=[]

def add_thread(thread_id):
     if thread_id not in st.session_state['chat_thread']:
         st.session_state['chat_thread'].insert(0, thread_id)

# chatbot.get_state(config={'configurable':{'thread_id':thread_id}}).values['messages']

def generate_chat_title(user_input):
    # Prompt the LLM to create a short 3-5 word title
    prompt = f"Give a short, punchy 3-5 word title for a chat that starts with this message: '{user_input}'. Return ONLY the title, no quotes."
    model_name = os.getenv("MODEL_NAME")
    model = ChatGroq(model=model_name, max_tokens=50)
    # You can invoke your model here. (If using LangChain/ChatGroq/etc.):
    response = model.invoke(prompt)
    return response.content.strip()

st.set_page_config(
    page_title="Real-Time AI Support Assistant",
    page_icon="🤖",
    layout="centered",
)

st.title("🤖 Real-Time AI Support Assistant")
st.caption("Intent-aware • Retrieval-augmented • SaaS-ready architecture")

# ============================================================
# Session State
# ============================================================
if 'chat_thread' not in st.session_state:
    response = requests.get("http://127.0.0.1:8000/api/v1/chat/stream/threads")
    threads_data = response.json().get("threads", [])
    # API now returns list of dicts: {thread_id, chat_title, created_at}
    # Extract plain thread_id strings for internal use
    st.session_state['chat_thread'] = [t["thread_id"] for t in threads_data]
    # Store chat_titles from DB directly (no need to generate via LLM)
    st.session_state['chat_titles'] = {t["thread_id"]: t["chat_title"] for t in threads_data}

if "history" not in st.session_state:
    st.session_state.history = []

# if "thread_id" not in st.session_state:
#     existing_threads = st.session_state['chat_thread']
#     # chat_thread now holds plain thread_id strings — safe to use directly
#     st.session_state['thread_id'] = existing_threads[-1] if existing_threads else generate_thread_id()

#     if existing_threads:
#         response = requests.get(f"http://127.0.0.1:8000/api/v1/chat/stream/history/{st.session_state['thread_id']}")
#         messages = response.json().get("messages", [])
#         temp_message = []
#         for msg in messages:
#             role = 'user' if msg.get('type') == 'human' else 'assistant'
#             speaker = 'You' if role == 'user' else 'Assistant'
#             temp_message.append((speaker, msg.get('content', '')))  
#         st.session_state['history'] = temp_message

if "thread_id" not in st.session_state:
    # Always start a fresh, empty session on page load/refresh
    st.session_state['thread_id'] = generate_thread_id()
    st.session_state['history'] = []

if 'chat_titles' not in st.session_state:
    # chat_titles is already populated above when chat_thread was loaded
    # This block is a safety fallback in case session state is partially initialised
    st.session_state['chat_titles'] = {
        t_id: "New Chat" for t_id in st.session_state.get('chat_thread', [])
    }

if "last_request_id" not in st.session_state:
    st.session_state.last_request_id = None

if "messages" not in st.session_state:
    st.session_state.messages = []

st.sidebar.title("ChatBot")
if st.sidebar.button('New Chat'):
    reset_chat()

# ============================================================
# Input Form
# ============================================================
# if st.sidebar.button("New Chat"):
#   st.session_state.thread_id = str(uuid.uuid4())
#   st.session_state.messages = []  # clear UI messages if you track them separately
#   st.rerun()

st.sidebar.header('My Conversations')

for thread_id in st.session_state['chat_thread']:
    # 1. Look up the title, fallback to the string version of UUID if not found
    button_label = st.session_state['chat_titles'].get(thread_id, str(thread_id))

    is_active = (thread_id == st.session_state['thread_id'])

    button_type = "primary" if is_active else "secondary" 
    
    if st.sidebar.button(button_label, key=str(thread_id), type=button_type):
        st.session_state['thread_id']= thread_id
        response = requests.get(f"http://127.0.0.1:8000/api/v1/chat/stream/history/{st.session_state['thread_id']}")
        messages = response.json().get("messages", [])

        temp_message=[]

        for msg in messages:
            role = 'user' if msg.get('type') == 'human' else 'assistant'
            speaker = 'You' if role == 'user' else 'Assistant'
            temp_message.append((speaker, msg.get('content', '')))

        st.session_state['history']= temp_message
        st.rerun()

with st.form("chat_form", clear_on_submit=True):
    user_input = st.text_input(
        "Ask your question",
        max_chars=MAX_INPUT_LENGTH,
        placeholder="e.g., How do I upgrade my billing plan?",
    )

    submitted = st.form_submit_button("Send")


if submitted:

    if not user_input or not user_input.strip() or user_input == " ":
            st.warning("Please enter a valid question.")
    else:
        placeholder = st.empty()
        try:
            with placeholder.container():
                st.info("Sending request to backend...")

                # Generate title only for the first message of a new conversation
                is_new_chat = st.session_state['thread_id'] not in st.session_state['chat_titles'] \
                            or st.session_state['chat_titles'].get(st.session_state['thread_id']) == "New Chat"
                chat_title = generate_chat_title(user_input.strip()) if is_new_chat else \
                            st.session_state['chat_titles'].get(st.session_state['thread_id'], "New Chat")

                response = requests.post(
                    API_URL,
                    json={
                        "messages": user_input.strip(),
                        "thread_id": st.session_state.thread_id,
                        "chat_title": chat_title        # ← send title to backend
                    },
                    timeout=TIMEOUT_SECONDS,
                )
                # Save the title locally in session state too
                st.session_state['chat_titles'][st.session_state['thread_id']] = chat_title

                response.raise_for_status()
                data = response.json()

                messages_list = data.get("reply", [])
                # answer = messages_list[-1].get("content", "No response returned.") if messages_list else "No response returned."
                # print("============Answers============\n",answer)
                # Store conversation
                st.session_state.history.append(("You", user_input.strip()))
                st.session_state.history.append(("Assistant", messages_list))
                current_thread=st.session_state['thread_id']
                
                if current_thread not in st.session_state['chat_thread']:
                    st.session_state['chat_thread'].insert(0, current_thread)
                    st.session_state['chat_titles'][current_thread]=chat_title
                    
                st.rerun()
        except RequestException as e:
            st.error("Backend request failed.")
            st.exception(e)
        else:
            placeholder = st.empty()


# ============================================================
# Chat History Rendering
# ============================================================

if st.session_state.history:
    st.divider()
    st.subheader("Conversation")

    for speaker, text in st.session_state.history:
        if speaker == "You":
            st.markdown(f"**🧑 You:** {text}")
        else:
            st.markdown(f"**🤖+ Assistant:** {text}")

# with st.sidebar:
#     st.info(f"**Current Session Thread ID:**\n`{st.session_state.thread_id}`")
#     if st.button("Clear Local View & Restart Thread"):
#         st.session_state.thread_id = str(uuid.uuid4())
#         st.session_state.messages = []
#         st.rerun()
