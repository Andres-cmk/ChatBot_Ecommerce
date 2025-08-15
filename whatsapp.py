import requests
import os

class WhatsappApi:
    def __init__(self, token):
        self.token_access = token
        self.url_base = "https://graph.facebook.com/v22.0/668381476368080/messages"
        self.headers = { "Authorization": f"Bearer {self.token_access}", "Content-Type": "application/json" }

    
    def get_id_meta(self, local_image_path):
    
        upload_url = "https://graph.facebook.com/v22.0/668381476368080/media"
    
        
        headers = {
        "Authorization": f"Bearer {self.token_access}"
        }
    
        with open(local_image_path, "rb") as img:
            files = {"file": (os.path.basename(local_image_path), img, "image/png")  }
            data = {
            "messaging_product": "whatsapp",
            "type": "image/png"
            }
        
            response = requests.post( url=upload_url, headers=headers, data=data, files=files)
            re = response.json()
            print("[DEBUG]", re)
            if "id" in re:
                return re["id"]
            else:
                raise Exception(f"Error al subir la imagen: {re}")
    
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
            "recipient_type": "individual",
            "to": number,
            "type": "image",
            "image": {
                "id": self.get_id_meta(url_to_image),
                "caption": "image"
            }
        }
        try:
            requests.post(self.url_base, headers=self.headers, json=data)
            return True
        except requests.exceptions.RequestException as e:
            print(e)
            return False





        
