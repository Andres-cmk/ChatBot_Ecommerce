from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv
from makersTech import ComputerStoreBot
from whatsapp import WhatsappApi
import uvicorn
import json
import os

load_dotenv()

VERIFY_TOKEN = os.getenv("TOKEN_OF_WEBHOOK")
PASS_ADMIN_TECH = os.getenv("PASS_OF_ADMIN")
TOKEN_ACCESS = str(os.getenv("ACCESS_TOKEN_WHATSAPP"))
ID_NUMBER = str(os.getenv("ID_NUMBER"))

app = FastAPI()
makers = ComputerStoreBot()
wp = WhatsappApi(TOKEN_ACCESS,ID_NUMBER)


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
    data = await request.json()
    print(json.dumps(data, ensure_ascii=False))

    contex = data
    
    # Aquí procesarás los mensajes de WhatsApp
    # Ejemplo: extraer el mensaje del cliente y responder

    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("app:app", port=8000 ,reload=True)