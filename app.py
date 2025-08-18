from sqlalchemy import create_engine 
from langchain_community.chat_message_histories import SQLChatMessageHistory 
from langchain.memory import ConversationBufferMemory 
from langchain_ollama import OllamaLLM
from langchain.tools import Tool
from langchain.agents import initialize_agent, AgentType, AgentExecutor 
from langchain_core.output_parsers import StrOutputParser 
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, HumanMessagePromptTemplate 
from langchain_core.messages import SystemMessage 
from langchain_core.runnables.history import RunnableWithMessageHistory 
from langchain_core.runnables import ConfigurableFieldSpec 
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException 
from fastapi.responses import PlainTextResponse 
from whatsapp import WhatsappApi 
from model_makers_tech import ChatBotModel 
from db.connection import DatabaseStock 
import uvicorn 
import json
import http
import os 


# ---------------------------------------- LOAD ENV ---------------------------------------------------#
load_dotenv()
VERIFY_TOKEN = os.getenv("TOKEN_OF_WEBHOOK")
PASS_ADMIN_TECH = os.getenv("PASS_OF_ADMIN")
TOKEN_ACCESS = os.getenv("ACCESS_TOKEN_WHATSAPP")

app = FastAPI()
wp = WhatsappApi(TOKEN_ACCESS)
bot = ChatBotModel()
db = DatabaseStock()

# Create field histoy and db for memory
os.makedirs("history", exist_ok=True)
db_history = os.path.join("history", "memory.db")
engine = create_engine(f"sqlite:///{db_history}")

# ----------------------------- SETUP MEMORY MODEL ----------------------------------------------------#
def get_session_history(session_id: str, user_id: str):
    return SQLChatMessageHistory(
        session_id=f"{user_id}---{session_id}", 
        connection=engine
    )

model = OllamaLLM(model=bot.name_model, temperature=0.4, top_p=0.9, top_k=40, num_ctx=4096)

pchat_prompt_template = ChatPromptTemplate.from_messages(
    [
        SystemMessage(content="Eres un asistente útil de Makers Tech."),
        MessagesPlaceholder(variable_name="history"),
        HumanMessagePromptTemplate.from_template("{question}")
    ]
)

parser = StrOutputParser()
chain = pchat_prompt_template | model | parser

runnable_with_history = RunnableWithMessageHistory(
    runnable=chain, 
    input_messages_key="question", 
    get_session_history=get_session_history,
    history_factory_config=[
        ConfigurableFieldSpec(
            id="session_id",
            annotation=str,
            name="Session ID",
            description="Unique identifier for the conversation session.",
            default="",
            is_shared=True
        ),
        ConfigurableFieldSpec(
            id="user_id",
            annotation=str,
            name="User ID",
            description="Unique identifier for the user.",
            default="",
            is_shared=True
        ),
    ],
    history_messages_key="history"
)

#-------------------------------------------------------------------------------------------------------------------------#

# ---------------------------------------------------------------- TOOLS BUSINESS ------------------------------------------------------#
def get_amount_stock_by_name(s: str):
    return bot.get_amount_stock(s)


def generate_image(description: str):
    path = str(bot.generate_image_stock())
    wp.send_graphics(url_to_image=path, number="573103726765")
    return description

def search_db(objecto_stock: str):
    print(objecto_stock)
    rows = db.get_data_by_macht(objecto_stock)
    prodcuts = []
    for row in rows:
        product = {
            "id": row[0],
            "nombre": row[1],
            "categoria": row[2],
            "subcategoria": row[3],
            "marca": row[4],
            "cpu": row[5],
            "gpu": row[6], 
            "ram": row[7],
            "almacenamiento": row[8],
            "precio": row[9],
            "recomendacion_nivel": row[11],
            "recomendacion_stars": row[12]
        }
        prodcuts.append(product)

    return prodcuts

# ------------------------------------------ MEMORY AGENT ----------------------------------------------------------------------$
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

tools = [
    Tool(
        name="search_db",
        func=search_db,
        description=(
            "Usa esta herramienta cuando el usuario mencione una marca de PC "
            "(Dell, HP, Apple, ASUS, Lenovo, Acer, Mac). "
            "SOLO SE Recibe el nombre de la marca como parámetro"
        )
    ),
    Tool(
        name="generate_image",
        func=generate_image,
        description=(
            "Usa esta herramienta SOLO si el usuario menciona la clave secreta 'makers_1234'. "
            "Esto significa que el usuario es el CEO y desea ver un gráfico del stock."
        )
    ),
    Tool(
        name="direct_answer",
        func=lambda x: x,
        description="Usa esto para responder directamente al usuario sin usar herramientas",
        return_direct=True
    ),
    Tool(
        name="get_amount_stock_by_name",
        func=get_amount_stock_by_name,
        description="Usa esto cuando el usuario pregunta la cantidad de productos de marca de PC"
        "(Dell, HP, Apple, ASUS, Lenovo, Acer, Mac). "
        "SOLO se recibe el nombre de la marca como parametro extraido del mensaje del usuario"
    )
]

agent = initialize_agent(
    tools=tools,
    llm=model,
    agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
    memory=memory,
    verbose=True,
)
# -----------------------------------------------------------------------------------------------------------------------------------------#




# ---------------------------------------------------------------- API ---------------------------------------------------------------------#

@app.get("/webhook", response_class=PlainTextResponse)
async def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge 
    else:
        raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/webhook")
async def handle_webhook(request: Request):
    try:
        data = await request.json()
        if not data or "entry" not in data or len(data["entry"]) == 0:
            return {"status": "no data"}

        entry = data["entry"][0]
        if "changes" not in entry or len(entry["changes"]) == 0:
            return {"status": "no changes"}

        value = entry["changes"][0]["value"]
        if "messages" not in value or len(value["messages"]) == 0:
            return {"status": "no messages"}

        message = value["messages"][0]
        number = value["contacts"][0]["wa_id"]
        content_message = message["text"]["body"]


        try:
            agent_result = str(agent.run(content_message)).strip()
        except Exception as e:
            print("Error ejecutando agent:", e)
            agent_result = ""


        if not agent_result or agent_result in ["{}", "[]", "null"]:
            final_prompt = content_message
        else:
            final_prompt = (
                f"{content_message}\n\n"
                f"Resultados de herramientas: {agent_result}\n\n"
                "Redacta una respuesta clara, breve y natural usando esos resultados."
            )


        response_text = runnable_with_history.invoke(
            {"question": final_prompt},
            config={"configurable": {"session_id": number, "user_id": number}}
        )

        if hasattr(response_text, "content"):
            response_text = response_text.content

        wp.send_message(context=bot.format_response(response_text), to=number)

        return http.HTTPStatus.OK

    except Exception as e:
        print(f"Error en webhook: {e}")
        return {"status": "error", "detail": str(e)}

# ---------------------------------------------------------------------------------------------------------------------------------#

if __name__ == "__main__":
    uvicorn.run("app:app", port=8000 ,reload=True)
