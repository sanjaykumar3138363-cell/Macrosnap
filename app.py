from google import genai
from google.genai import types
import streamlit as st
from prompts import SYSTEM_PROMPT,WELCOME_MESSAGE_PROMPT,SUMMARY_REQUEST_PROMPT
import asyncio
from telegram import Bot
import requests


TOKEN="8693370227:AAHtuS5HKit1o8By7duD8lbVKdVk-RK44yw"
url=f"https://api.telegram.org/bot{TOKEN}/getUpdates"
response=requests.get(url)
print(response.json())

TELEGRAM_BOT_TOKEN = st.secrets["TELEGRAM_BOT_TOKEN"]
GEMINI_API_KEY=st.secrets["GEMINI_API_KEY"]

def send_to_telegram(summary):
    bot_token = st.secrets["TELEGRAM_BOT_TOKEN"]
    chat_id = st.secrets["TELEGRAM_CHAT_ID"]

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    response = requests.post(
        url,
        data={
            "chat_id": chat_id,
            "text": f"📸 MacroSnap Summary\n\n{summary}"
        }
    )

    return response.ok


def send_telegram(chat_id,text):
    bot=Bot(token=TELEGRAM_BOT_TOKEN)
    asyncio.run(bot.send_message(chat_id=chat_id,text=text))


@ st.cache_resource
def get_gemnini_Client():
    return genai.Client(api_key=GEMINI_API_KEY)
gemini_client=get_gemnini_Client()
MODEL_NAME="gemini-3.8-flash"

def render_message(message):
    with st.chat_message(message["role"]):
        if message["kind"]=="text":
            st.write(message["content"])
        elif message["kind"] =="image":
            st.image(message["content"])
def add_message(role,kind,content):
    st.session_state.messages.append({
        "role":role,
        "kind":kind,
        "content":content
        })
    render_message(st.session_state.messages[-1])


def ask_gemini(parts):
    try:
        return st.session_state.chat.send_message(parts).text
    except Exception as error:
        return f"sorry, something went wrong: {error}"

if "chat" not in st.session_state:
    st.session_state.chat = []

#step-1 onbording(user_name and number)
if "onboarded" not in st.session_state:
    st.title("Macrosnap!!..") 
    st.caption("👁️ See It. 💬 Ask It. 🧠 Know It.")
    with st.form("onboarded_form"):
        name= st.text_input("name")
        whatsapp_number=st.text_input("whatsapp_number(with country code)",placeholder="+91XXXXXXXXXX",help="This is number Macrosnap will text your summary to.")
        submitted=st.form_submit_button("let's goo!!..")
    if submitted:
        if not name.strip() or not whatsapp_number.strip():
            st.warning("Please fill both the your name and whatsapp_number")
        else:
            st.session_state.name=name.strip()
            st.session_state.whatsapp_number=whatsapp_number.strip()
            st.session_state.chat=gemini_client.chats.create(
                model=MODEL_NAME,config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
            )
            st.session_state.messages=[]
            st.session_state.onboarded = True
            st.rerun()
    st.stop()

 
#char interface
if not st.session_state.messages:
    add_message("assistant","text",WELCOME_MESSAGE_PROMPT.format(name=st.session_state.name))
else:
    for message in st.session_state.messages:
        render_message(message)

#user_input

User_input=st.chat_input(
    "Ask a question, or attach a photo of your meal",
    accept_file=True,
    file_type=["jpg","jpeg","png"]
)

if User_input:
    photo=User_input.files[0] if User_input.files else None
    text=User_input.text 
    parts=[]

    if photo is not None:
        photo_bytes=photo.getvalue()
        add_message("user","image", photo_bytes)
        parts.append(types.Part.from_bytes(data=photo_bytes, mime_type=photo.type))
    if text:
        add_message("user","text",text)
        parts.append(text)
    elif photo is not None:
        parts.append("What is this meal? Give me the calories and macros.")
    with st.spinner("Crunching the numbers..."):
        answer=ask_gemini(parts)
    add_message("assistant","text",answer)


if st.button("📲 Send Summary to Telegram"):

    SUMMARY_REQUEST_PROMPT = "User asked about the text in the uploaded image. The image contains information about a product and its key details were explained by the assistant.."

    if send_to_telegram(SUMMARY_REQUEST_PROMPT):
        st.success("✅ Summary sent to Telegram!")
    else:
        st.error("❌ Failed to send summary.")