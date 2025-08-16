from sqlalchemy import create_engine
from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain_ollama import OllamaLLM
from langchain.tools import tool
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, HumanMessagePromptTemplate
from langchain_core.messages import SystemMessage
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.runnables import ConfigurableFieldSpec
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv
from whatsapp import WhatsappApi
from model_makers_tech import ChatBotModel
from db.connection import DatabaseStock
import uvicorn
import ollama
import os

# ---------------------------------------- LOAD() ---------------------------------------------------#
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

# Set up Memory Model
#--------------------------------------------------------------------------------------------------#
def get_session_history(session_id: str, user_id: str):
        return SQLChatMessageHistory(
        session_id=f"{user_id}---{session_id}",
        connection=engine)

model = OllamaLLM(model=bot.name_model)

pchat_prompt_template = ChatPromptTemplate.from_messages(
        [SystemMessage(content="Eres un asistente útil de Makers Tech."),
         MessagesPlaceholder(variable_name="history"),
         HumanMessagePromptTemplate.from_template("{question}")]
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
@tool
def generate_image():
    return bot.generate_image_stock()
@tool
def search_db(objecto_stock: str):
    rows = db.get_data_by_macht(objecto_stock)
    prodcuts = []
    product = {}
    for row in rows:
        product = {
            "id": row[0],
            "nombre": row[1],
            "categoria": row[2],
            "subcategoria": row[3],
            "marca": row[4],
            "cpu": row[5],
            "gpu": row[6],   # puede venir None
            "ram": row[7],
            "almacenamiento": row[8],
            "precio": row[9],
            "recomendacion_nivel": row[11],
            "recomendacion_stars": row[12]
        }
    
    prodcuts.append(product)



def get_tools_ceo(to: str):

    system_message = {
        'role':'system',
        'content': """You're a useful assistant who helps the CEO of Makers Tech generate inventory charts. For that, you can use the "generate_image" 
                  function. This function doesn't take parameters."""
    }

    user_message = {
        'role':'user',
        'content': 'Generate image of stock'
    }

    available_functions = {
        "generate_image": generate_image,
    }

    response = ollama.chat(
    messages=[system_message, user_message],
    model=bot.name_model, 
    tools=[generate_image]  # pass the actual function object as a tool
    )

    if response.message.tool_calls:
        for tool in response.message.tool_calls:
            function = available_functions.get(tool.function.name)
            if function:
                path_to_image = function(**tool.function.arguments)
                print(path_to_image)
                if path_to_image != None:
                    flag = wp.send_graphics(path_to_image, to)
                    print("Resultado: ", flag)


# -----------------------------------------------------------------------------------------------------------------------------------------#


# ---------------------------------------------------------------- API ---------------------------------------------------------------------#

@app.get("/webhook", response_class=PlainTextResponse)
async def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge  # WhatsApp espera este valor
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

        # 1. Modo CEO
        if str(PASS_ADMIN_TECH) in content_message:
            response = bot.ask_model(runnable_with_history,"CEO",number)
            wp.send_message(context=response, to=number)
            get_tools_ceo(number)
            return {"status": "ok CEO"}
        
        # Modificar
        """
        if content_message.lower().startswith("vender "):
            match = re.match(r"^vender\s+(.+)$", content_message, re.IGNORECASE)
            if match:
                brand = match.group(1).strip()
                rows = db.get_data_by_macht(brand)
                if rows:
                    context = f"INFORMACIÓN DE STOCK: {rows}. Responde al cliente con esta información, clara y brevemente."
                    response = bot.ask_model(context)
                else:
                    response = "No tenemos productos de esa marca en este momento."
                wp.send_message(context=response, to=number)
                return {"status": "ok vender"}
                """

        # 3. Modo cliente normal
        response_text = bot.ask_model(runnable_with_history, message=content_message, number=number )
        wp.send_message(context=response_text, to=number)
        return {"status": "200 OK"}

    except Exception as e:
        print(f"Error en webhook: {e}")
        # Opcional: enviar mensaje de error al cliente
        return {"status": "error", "detail": str(e)}

# ------------------------------------------------------------------------------------------------------------------------------------------ #

if __name__ == "__main__":
    uvicorn.run("app:app", port=8000 ,reload=True)