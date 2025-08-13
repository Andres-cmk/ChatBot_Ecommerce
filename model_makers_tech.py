from ollama import chat
from ollama import ChatResponse
from db.connection import DatabaseStock
import matplotlib.pyplot as plt
import datetime as dt

class ChatBotModel:
  def __init__(self):
    self.name_model = "makers_tech"
    self.db = DatabaseStock()
    
  def ask_model_client(self,prompt: str):
    response: ChatResponse = chat(model=self.name_model, messages=[
        {
          'role': 'user',
          'content': prompt,
        },
        ])
    return response.message.content
  
  def generate_image_stock(self):

    data = self.db.get_by_query("SELECT nombre, stock FROM productos WHERE stock > 0")
    if len(data) != 0:
      names_products = [p[0] for p in data]
      stocks = [p[1] for p in data]
      plt.figure(figsize=(10,6))
      bars = plt.bar(names_products, stocks, color='skyblue', edgecolor='navy', linewidth=1.2)

      plt.title('Current inventoryu - Makers Tech', fontsize=16, fontweight='bold')
      plt.xlabel('Products', fontsize=12)
      plt.ylabel('amount', fontsize=12)
      plt.xticks(rotation=45, ha='right')

      # Añadir valores encima de las barras
      for bar, stock in zip(bars, stocks):
        plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1, 
                 str(stock), ha='center', va='bottom', fontsize=10, fontweight='bold')
      plt.savefig(f"C:\\Users\\ramir\\Desktop\\ChatBot\\images\\image_{dt.datetime.now()}")
      plt.show()
  
  def update_stock_database(self, name: str):
    if self.db.update_db(name):
      return "Ok"
    else: 
      return "NOT OK"
    

  