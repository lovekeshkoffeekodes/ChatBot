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

API_URL = "http://127.0.0.1:8000/chat/stream"
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
    response = requests.get("http://127.0.0.1:8000/conversations")
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

# ============================================================
# Sidebar
# ============================================================

st.sidebar.title("Weave")
if st.sidebar.button('New Chat'):
    reset_chat()
st.sidebar.markdown("---")
st.sidebar.header('My Conversations')

for thread_id in list(st.session_state['chat_thread']):
    # 1. Look up the title, fallback to the string version of UUID if not found
    button_label = st.session_state['chat_titles'].get(thread_id, str(thread_id))
    is_active = (thread_id == st.session_state['thread_id'])
    button_type = "primary" if is_active else "secondary" 
    col_title, col_menu = st.sidebar.columns([0.75, 0.25])

    with col_title:
        if st.sidebar.button(button_label, key=str(thread_id), type=button_type):
            st.session_state['thread_id']= thread_id 
            st.session_state['menu_thread_id'] = None
            st.session_state['editing_thread_id'] = None
            st.session_state['deleting_thread_id'] = None
            try:
                response = requests.get(f"http://127.0.0.1:8000/conversations/{st.session_state['thread_id']}/messsages")
                messages = response.json().get("messages", [])

                temp_message=[]

                for msg in messages:
                    msg_type = msg.get('type', '').lower()
                    msg_role = msg.get('role', '').lower()

                    is_user = msg_type in ['human', 'user'] or msg_role in ['human', 'user']
                    speaker = 'You' if is_user else 'Assistant'

                    temp_message.append((speaker, msg.get('content', '')))

                st.session_state['history']= temp_message
            except RequestException:
                st.error("Failed to load chat history.")
            st.rerun()
    with col_menu:
        if st.button("...", key=f"menu_btn_{thread_id}", help="Options"):
            # Toggle the menu state for this specific thread
            if st.session_state.get('menu_thread_id') == thread_id:
                st.session_state['menu_thread_id'] = None
            else:
                st.session_state['menu_thread_id'] = thread_id
                st.session_state['editing_thread_id'] = None
                st.session_state['deleting_thread_id'] = None
            st.rerun()

    # If this thread's "..." menu is opened, render options directly below it
    if st.session_state.get('menu_thread_id') == thread_id:
        
        # 1. Renaming state
        if st.session_state.get('editing_thread_id') == thread_id:
            new_title = st.sidebar.text_input("New title", value=button_label, key=f"input_rename_{thread_id}")
            col_save, col_cancel = st.sidebar.columns(2)
            with col_save:
                if st.sidebar.button("Save", key=f"save_title_{thread_id}", use_container_width=True):
                    try:
                        patch_url = f"http://127.0.0.1:8000/conversations/{thread_id}"
                        resp = requests.patch(patch_url, json={"chat_title": new_title.strip()})
                        if resp.status_code == 200:
                            st.session_state['chat_titles'][thread_id] = new_title.strip()
                            st.session_state['menu_thread_id'] = None
                            st.session_state['editing_thread_id'] = None
                            st.success("Title updated!")
                            st.rerun()
                    except RequestException:
                        st.sidebar.error("Failed to update.")
            with col_cancel:
                if st.sidebar.button("Cancel", key=f"cancel_rename_{thread_id}", use_container_width=True):
                    st.session_state['editing_thread_id'] = None
                    st.rerun()

        # 2. Delete confirmation state
        elif st.session_state.get('deleting_thread_id') == thread_id:
            st.sidebar.warning("Delete this chat?")
            col_yes, col_no = st.sidebar.columns(2)
            with col_yes:
                if st.sidebar.button("Yes", key=f"del_yes_{thread_id}", use_container_width=True):
                    try:
                        delete_url = f"http://127.0.0.1:8000/api/v1/chat/stream/conversations/{thread_id}"
                        response = requests.delete(delete_url)
                        if response.status_code == 200:
                            st.session_state['chat_thread'].remove(thread_id)
                            if thread_id in st.session_state['chat_titles']:
                                del st.session_state['chat_titles'][thread_id]
                            st.session_state['menu_thread_id'] = None
                            st.session_state['deleting_thread_id'] = None
                            if st.session_state['thread_id'] == thread_id:
                                reset_chat()
                            st.success("Deleted.")
                            st.rerun()
                    except RequestException:
                        st.sidebar.error("Failed to delete.")
            with col_no:
                if st.sidebar.button("No", key=f"del_no_{thread_id}", use_container_width=True):
                    st.session_state['deleting_thread_id'] = None
                    st.rerun()

        # 3. Default menu options (Edit / Delete)
        else:
            col_opt1, col_opt2 = st.sidebar.columns(2)
            with col_opt1:
                if st.sidebar.button("✏️ Edit", key=f"opt_edit_{thread_id}", use_container_width=True):
                    st.session_state['editing_thread_id'] = thread_id
                    st.rerun()
            with col_opt2:
                if st.sidebar.button("🗑️ Delete", key=f"opt_del_{thread_id}", use_container_width=True):
                    st.session_state['deleting_thread_id'] = thread_id
                    st.rerun()
        
        st.sidebar.markdown("---")

# ============================================================
# Chat History Rendering (Native Chat Bubbles)
# ============================================================
for speaker, text in st.session_state.history:
    role = "user" if speaker == "You" else "ai"
    with st.chat_message(role):
        st.markdown(text)


if user_input := st.chat_input("Ask your question...", max_chars=MAX_INPUT_LENGTH):

    if not user_input or not user_input.strip() or user_input == " ":
            st.warning("Please enter a valid question.")
    else:
        try:    
            # Generate title only for the first message of a new conversation
            is_new_chat = st.session_state['thread_id'] not in st.session_state['chat_titles'] \
                        or st.session_state['chat_titles'].get(st.session_state['thread_id']) == "New Chat"
            chat_title = generate_chat_title(user_input.strip()) if is_new_chat else \
                        st.session_state['chat_titles'].get(st.session_state['thread_id'], "New Chat")

            st.session_state.history.append(("You", user_input.strip()))
            with st.chat_message("user"):
                st.markdown(user_input.strip())
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
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
                    # Safely parse response whether it's a list or string
                    if isinstance(messages_list, list) and messages_list:
                        assistant_reply = messages_list[-1].get("content", str(messages_list))
                    else:
                        assistant_reply = str(messages_list)

                    st.markdown(assistant_reply)

                    # st.session_state.history.append(("You", user_input.strip()))
                    st.session_state.history.append(("Assistant", assistant_reply))
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
