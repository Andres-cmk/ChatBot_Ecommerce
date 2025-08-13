import model_makers_tech
import datetime

class ComputerStoreBot:

    def __init__(self):
        
        # History of conversations
        self.chats = {}

    def update_chats(self, number: str, name: str):
        if number not in self.chats:
            self.chats[number] = name
        return self.chats
    
    def get_response_model(self):
        return 
    
    def make_graphics(self):
        return 
    
    def show_history(self, json_history):
        return

    






    
    