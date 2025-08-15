from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv
from whatsapp import WhatsappApi
from model_makers_tech import ChatBotModel
from db.connection import DatabaseStock
import uvicorn
import datetime as dt
import ollama
import os
import re

load_dotenv()

VERIFY_TOKEN = os.getenv("TOKEN_OF_WEBHOOK")
PASS_ADMIN_TECH = os.getenv("PASS_OF_ADMIN")
TOKEN_ACCESS = os.getenv("ACCESS_TOKEN_WHATSAPP")

app = FastAPI()
wp = WhatsappApi(TOKEN_ACCESS)
bot = ChatBotModel()
db = DatabaseStock()


# Tools
def update_db(name: str, n: int):
    return bot.update_stock_database(name=name, p=n)
def generate_image():
    return bot.generate_image_stock()

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




# verify of token
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

        # Validar estructura mínima
        if not data or "entry" not in data or len(data["entry"]) == 0:
            return {"status": "no data"}

        entry = data["entry"][0]
        if "changes" not in entry or len(entry["changes"]) == 0:
            return {"status": "no changes"}

        value = entry["changes"][0]["value"]

        # Verificar si es mensaje entrante
        if "messages" not in value or len(value["messages"]) == 0:
            return {"status": "no messages"}

        message = value["messages"][0]
        number = value["contacts"][0]["wa_id"]
        content_message = message["text"]["body"].strip()

        # 1. Modo CEO
        if str(PASS_ADMIN_TECH).lower() in content_message.lower():
            response = bot.ask_model("CEO")
            wp.send_message(context=response, to=number)
            get_tools_ceo(number)
            content_message = ""
            return {"status": "ok CEO"}

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

        # 3. Modo cliente normal
        response = bot.ask_model(prompt=content_message)
        content_message = ""
        wp.send_message(context=response, to=number)
        return {"status": "ok"}

    except Exception as e:
        print(f"Error en webhook: {e}")
        # Opcional: enviar mensaje de error al cliente
        return {"status": "error", "detail": str(e)}
    

if __name__ == "__main__":
    uvicorn.run("app:app", port=8000 ,reload=True)