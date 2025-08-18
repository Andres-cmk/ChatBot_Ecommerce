from sqlalchemy import create_engine 
from langchain_community.chat_message_histories import SQLChatMessageHistory 
from langchain.memory import ConversationBufferMemory 
from langchain_ollama import OllamaLLM
from langchain.tools import Tool
from langchain.agents import initialize_agent, AgentType
from langchain_core.output_parsers import StrOutputParser 
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, HumanMessagePromptTemplate 
from langchain_core.messages import SystemMessage 
from langchain_core.runnables.history import RunnableWithMessageHistory 
from langchain_core.runnables import ConfigurableFieldSpec 
from langchain.vectorstores import Chroma
from langchain.schema import Document
from langchain.embeddings import OllamaEmbeddings
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

# --------------------------------------- RAG SETUP ------------------------------------------------------#
embeddings = OllamaEmbeddings(model=bot.name_model)
# Carpeta donde guardas ChromaDB
persist_dir = "./chromadb"

if os.path.exists(persist_dir) and os.listdir(persist_dir):
    
    print("Cargando ChromaDB existente...")
    vectorstore = Chroma(persist_directory=persist_dir, embedding_function=embeddings)
else:
    # Si no existe, generas todo desde cero
    print("Creando ChromaDB desde documentos...")
    products = db.get_all()
    docs = []
    for pro in products:
        doc_content = (
            f"{pro[1]} | {pro[2]} | {pro[3]} | {pro[5]} | {pro[6]} | {pro[7]} | "
            f"{pro[8]} | {pro[9]} | {pro[10]}"
        )
        docs.append(doc_content)

    vectorstore = Chroma.from_texts(
        texts=docs,
        embedding=embeddings,
        metadatas=[{"id": str(pro[0])} for pro in products],
        persist_directory=persist_dir
    )

vectorstore.persist()

# ---------------------------------------------------------------------------------------------------------#

# ----------------------------- SETUP MEMORY MODEL ----------------------------------------------------#
def get_session_history(session_id: str, user_id: str):
    return SQLChatMessageHistory(
        session_id=f"{user_id}---{session_id}", 
        connection=engine
    )

model = OllamaLLM(model=bot.name_model, temperature=0.4, top_p=0.9, top_k=40, num_ctx=4096)

system_prompt = SystemMessage(content="""
Eres MakersBot de Makers Tech 💻. 
- Solo usa los resultados de la herramienta de inventario.
- No inventes productos.
- Lista únicamente nombre, categoría y precio.
- Si no hay resultados, responde: "No se encontraron coincidencias."
- Mantén la respuesta clara y amigable, 1-3 líneas máximo.
""")

pchat_prompt_template = ChatPromptTemplate.from_messages(
    [
        system_prompt,
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
def search_products_rag(query: str, top_k: int = 5):
    """Busca productos usando RAG: ChromaDB + detalles desde SQL"""
    # 1. Búsqueda semántica en ChromaDB
    results = vectorstore.similarity_search(query, k=top_k)
    if not results:
        return json.dumps([])  # Devuelve lista vacía si no hay coincidencias

    output = []
    for r in results:
        # Extrae nombre de producto desde ChromaDB
        nombre = r.page_content.split("|")[0].strip()
        # Busca detalles completos en la base de datos
        db_results = db.get_data_by_macht(nombre)
        for row in db_results:
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
                "stock": row[10],
                "recomendacion_nivel": row[11],
                "recomendacion_stars": row[12]
            }
            output.append(product)
    return json.dumps(output)


def get_amount_stock_by_name(s: str):
    return json.dumps(bot.get_amount_stock(s))


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
            "stock": row[10],
            "recomendacion_nivel": row[11],
            "recomendacion_stars": row[12]
        }
        prodcuts.append(product)

    return json.dumps(prodcuts)

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
    ),
    Tool(
        name="search_products_rag",
        func=search_products_rag,
        description="Usa esta herramienta **para preguntas complejas o búsquedas semánticas** "
            "que incluyan características, RAM, CPU, cantidad de productos en stock, precio, categoria, subcategoria. Devuelve resultados detallados.",
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

        print("MENSAJE REGRESADO:",response_text)
        wp.send_message(context=bot.format_response(response_text), to=number)

        return http.HTTPStatus.OK

    except Exception as e:
        print(f"Error en webhook: {e}")
        return {"status": "error", "detail": str(e)}

# ---------------------------------------------------------------------------------------------------------------------------------#

if __name__ == "__main__":
    uvicorn.run("app:app", port=8000 ,reload=True)
