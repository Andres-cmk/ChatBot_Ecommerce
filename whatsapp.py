import requests

class WhatsappApi:
    def __init__(self, token: str, id_number: str):
        self.id = id_number
        self.token_access = token
        self.url_base = f"https://graph.facebook.com/v22.0/{id}/messages"
        self.headers = { "Authorization": f"Bearer {self.token_access}", "Content-Type": "application/json" }
    
    def send_message(self, context: str, to: str) -> bool:

        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": context}
        }

        try:
            response = requests.post(self.url_base, json=payload, headers=self.headers)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(e)
            return False
    
    def send_graphics(self, url_to_image: str = "", number: str = "") -> bool:
        
        data = {
            "messaging_product": "whatsapp",
            "to": number,
            "type": "image",
            "image": {
                "link": url_to_image,
                "caption": "image"
            }
        }

        try:
            requests.post(self.url_base, headers=self.headers, json=data)
            return True
        except requests.exceptions.RequestException as e:
            print(e)
            return False





        
