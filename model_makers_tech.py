from ollama import chat
from ollama import ChatResponse
from db.connection import DatabaseStock
from langchain_core.runnables.history import RunnableWithMessageHistory
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import datetime as dt
import os
import re

class ChatBotModel:
  def __init__(self):
    load_dotenv()
    self.secret_pass = os.getenv("PASS_OF_ADMIN")
    self.name_model = "llama3.2:3b"
    self.db = DatabaseStock()

  def format_response(self, texto: str):
    # Eliminar pensamientos (si existen)
    texto = re.sub(r"<think>.*?</think>", "", texto, flags=re.DOTALL)
    # Eliminar markdown: negritas, etc.
    texto = re.sub(r"\*([^*]+)\*", r"\1", texto)  # quita *
    # Limpiar espacios extra
    texto = re.sub(r"\n+", "\n", texto.strip())
    return texto.strip()
  
  def ask_model(self, text: RunnableWithMessageHistory, message, number):
        response_text = text.invoke({"question": message}, 
                        config={"configurable": {"session_id": number, "user_id": number}})
        return response_text
  
  
  
  def generate_image_stock(self):
     data = self.db.get_by_query("SELECT nombre, stock FROM productos WHERE stock > 0")
     if len(data) != 0:
      names_products = [p[0] for p in data]
      stocks = [p[1] for p in data]
      fig_width = max(12, len(names_products) * 0.5)
      plt.figure(figsize=(fig_width, 8))

      colors = plt.cm.get_cmap('hsv')(range(len(names_products)))
      print(colors)

      bars = plt.bar(names_products, stocks, color=colors, edgecolor='navy', linewidth=1.2)

      plt.title('Current inventory - Makers Tech', fontsize=18, fontweight='bold')
      plt.xlabel('Products', fontsize=14)
      plt.ylabel('Amount', fontsize=14)

      plt.xticks(rotation=75, ha='right', fontsize=10)

      for bar, stock in zip(bars, stocks):
        plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                 str(stock), ha='center', va='bottom', fontsize=9, fontweight='bold')

      plt.tight_layout() 


      name_image_cm = dt.datetime.now()
      name_image = f"image_{name_image_cm.strftime('%Y%m%d_%H%M%S')}"
      path = os.path.join(r"C:\Users\ramir\Desktop\ChatBot\images", f"{name_image}.png")
      plt.savefig(path, dpi=150)
      plt.close()

      return path

  