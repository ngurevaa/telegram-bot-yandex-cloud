import os
import json
import requests

def handler(event, context):
    update = json.loads(event['body'])
    message = update['message']
    chat_id = message['chat']['id']
    
    if 'text' in message:
        text = message['text']
        
        if text in ['/start', '/help']:
            send_message(chat_id, "✅ Бот работает! Привет!")
        else:
            # Просто возвращаем эхо
            send_message(chat_id, f"🤖 Вы написали: {text}")
    
    return {'statusCode': 200}

def send_message(chat_id, text):
    token = os.environ['TG_BOT_TOKEN']
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {"chat_id": chat_id, "text": text}
    requests.post(url, json=data)
