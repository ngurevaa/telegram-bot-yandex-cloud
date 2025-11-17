import os
import json
import logging
import requests
from typing import Optional
import base64

class TelegramBot:
    def __init__(self):
        self.token = os.environ['TG_BOT_TOKEN']
        self.folder_id = os.environ['FOLDER_ID']
        self.bucket_name = os.environ['BUCKET_NAME']
        self.oauth_token = os.environ['YANDEX_OAUTH_TOKEN']
        
        self.ai_studio_url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

        self.classification_instruction = self.get_instructions("classification_instruction.txt")
        self.answer_instruction = self.get_instructions("answer_instruction.txt")

    def get_instructions(self, filename: str) -> Optional[str]:
        """Получение инструкций из Yandex Object Storage"""
        try:
            url = f"https://storage.yandexcloud.net/{self.bucket_name}/{filename}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                content = response.text.strip()
                return content
            else:
                return None
        except Exception as e:
            return None

    def call_yandex_ai_studio(self, messages: list, temperature: float = 0.1, max_tokens: int = 100) -> Optional[str]:
        """Вызов Yandex AI Studio API"""
        headers = {
            "Authorization": f"Bearer {self.oauth_token}",
            "Content-Type": "application/json"
        }

        data = {
            "modelUri": f"gpt://{self.folder_id}/yandexgpt/latest",
            "completionOptions": {
                "stream": False,
                "temperature": temperature,
                "maxTokens": max_tokens
            },
            "messages": messages
        }

        try:
            response = requests.post(
                self.ai_studio_url,
                headers=headers,
                json=data,
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            if 'result' in result and 'alternatives' in result['result'] and len(result['result']['alternatives']) > 0:
                text = result['result']['alternatives'][0]['message']['text'].strip()
                return text
            else:
                return None
        except Exception as e:
            return None

    def classify_question(self, text: str) -> Optional[bool]:
        """Классификация вопроса через Yandex AI Studio"""
        if not self.classification_instruction:
            return None

        messages = [
            {
                "role": "system",
                "text": self.classification_instruction
            },
            {
                "role": "user", 
                "text": f"Текст: {text}"
            }
        ]

        result = self.call_yandex_ai_studio(messages, temperature=0.1, max_tokens=10)

        if result:
            clean_result = result.strip().upper()

            if 'ДА' in clean_result:
                return True
            elif 'НЕТ' in clean_result:
                return False

        return None

    def generate_answer(self, text: str) -> Optional[str]:
        """Генерация ответа через Yandex AI Studio"""
        if not self.answer_instruction:
            return None
        
        messages = [
            {
                "role": "system",
                "text": self.answer_instruction
            },
            {
                "role": "user",
                "text": f"Вопрос: {text}"
            }
        ]

        answer = self.call_yandex_ai_studio(messages, temperature=0.3, max_tokens=1000)
        return answer

    def send_message(self, chat_id, text):
        """Отправка ответа"""
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}

        response = requests.post(url, json=data, timeout=10)

    def process_text(self, chat_id, text):
        if text in ['/start', '/help']:
            self.send_message(
                chat_id,
                "Я помогу ответить на экзаменационный вопрос по «Операционным системам».\nПрисылайте вопрос — фото или текстом."
            )
            return

        if not self.classification_instruction or not self.answer_instruction:
            self.send_message(
                chat_id,
                "Я не смог подготовить ответ на экзаменационный вопрос."
            )
            return

        is_exam_question = self.classify_question(text)
        if is_exam_question is None:
            self.send_message(chat_id, "Я не смог подготовить ответ на экзаменационный вопрос.")
            return

        if not is_exam_question:
            self.send_message(
                chat_id,
                "Я не могу понять вопрос.\nПришлите экзаменационный вопрос по «Операционным системам» — фото или текстом."
            )
            return

        answer = self.generate_answer(text)
        
        if answer:
            self.send_message(chat_id, answer)
        else:
            self.send_message(
                chat_id,
                "Я не смог подготовить ответ на экзаменационный вопрос."
            )

    def process_photo(self, chat_id, photos):
        """Обработка фотографии с помощью Yandex Vision OCR"""
        if photos:
            try:
                photo = photos[-1]
                file_id = photo['file_id']

                file_url = f"https://api.telegram.org/bot{self.token}/getFile"
                file_response = requests.post(file_url, json={"file_id": file_id})
                file_info = file_response.json()
            
                if not file_info.get('ok'):
                    self.send_message(chat_id, "Я не могу обработать эту фотографию.")
                    return
            
                file_path = file_info['result']['file_path']
            
                download_url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
                photo_response = requests.get(download_url)
            
                if photo_response.status_code != 200:
                    self.send_message(chat_id, "Я не могу обработать эту фотографию.")
                    return
            
                recognized_text = self.recognize_text_with_vision(photo_response.content)
                if recognized_text:
                    self.process_text(chat_id, recognized_text)
                else:
                    self.send_message(chat_id, "Я не могу обработать эту фотографию.")
                
            except Exception as e:
                self.send_message(chat_id, "Я не могу обработать эту фотографию.")
        else:
            self.send_message(chat_id, "Я не могу обработать эту фотографию.")

    def recognize_text_with_vision(self, image_content: bytes) -> Optional[str]:
        """Распознавание текста с фото через Yandex Vision OCR"""
        encoded_image = base64.b64encode(image_content).decode('utf-8')
        vision_url = "https://ocr.api.cloud.yandex.net/ocr/v1/recognizeText"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.oauth_token}",
            "x-folder-id": self.folder_id,
            "x-data-logging-enabled": "true"
        }
        
        payload = {
            "mimeType": "JPEG",
            "languageCodes": ["*"],
            "model": "page",
            "content": encoded_image
        }
        
        response = requests.post(vision_url, headers=headers, data=json.dumps(payload), timeout=30)
        if response.status_code == 200:
            result = response.json()
            if 'result' in result and 'textAnnotation' in result['result']:
                text_annotation = result['result']['textAnnotation']
                if 'fullText' in text_annotation:
                    full_text = text_annotation['fullText']
                    return full_text
        return None

    def handle_webhook(self, update):
        if 'message' not in update:
            return

        message = update['message']
        chat_id = message['chat']['id']

        if 'text' in message:
            self.process_text(chat_id, message['text'])
        elif 'photo' in message:
            self.process_photo(chat_id, message['photo'])
        else:
            self.send_message(
                chat_id,
                "Я могу обработать только текстовое сообщение или фотографию."
            )

bot = TelegramBot()

def handler(event, context):
    try:
        update = json.loads(event['body'])
        bot.handle_webhook(update)
        return {'statusCode': 200, 'body': 'OK'}
    except Exception as e:
        return {'statusCode': 200, 'body': 'OK'}
