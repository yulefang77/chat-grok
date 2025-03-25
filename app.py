import os
from dotenv import load_dotenv
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage, PushMessageRequest, ImageMessage
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent, ImageMessageContent
from openai import OpenAI
from pydantic import BaseModel, Field
import random
import requests
import base64
import logging
from pathlib import Path
from datetime import datetime

# 載入環境變數
load_dotenv()

# 設定日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 設定靜態資料夾路徑
STATIC_FOLDER = Path('static')
IMAGES_FOLDER = STATIC_FOLDER / 'images'

# 確保資料夾存在
STATIC_FOLDER.mkdir(exist_ok=True)
IMAGES_FOLDER.mkdir(exist_ok=True)

# 設定類
class Config:
    LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
    LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL', 'https://api.x.ai/v1')
    # 重新加入 ALLOWED_GROUPS，使用 set 來儲存群組 ID
    ALLOWED_GROUPS = {group.strip() for group in os.getenv('ALLOWED_GROUPS', '').split(',') if group.strip()}
    # 角色中的特定人名
    QUEEN_NAME = os.getenv('QUEEN_NAME', '某人')
    
    # 角色代碼到名稱的映射
    _ROLE_NAMES = {
        "A": os.getenv('ROLE_CODE_A', "預設用戶A"),
        "B": os.getenv('ROLE_CODE_B', "預設用戶B"),
        "C": os.getenv('ROLE_CODE_C', "預設用戶C"),
        "D": os.getenv('ROLE_CODE_D', "預設用戶D"),
    }
    
    # 角色設定 (使用代碼作為字典鍵)
    _ROLE_SETTINGS = {
        "default": "你是一個有禮貌的助手，請根據上下文提供合適的回答。不要使用 markdown 格式",
        "A": """你是一個幽默風趣、擅長互虧但不過頭的 AI 助手。
        你的對話風格類似於好友之間的輕鬆吐槽，帶點幽默的嘲諷，但不會讓對方真的不開心。
        當使用者表現出猶豫、失敗、吹牛卻沒做到的時候，你可以用搞笑的方式來回應。
        你的語氣應該像一個會互相吐槽的朋友，偶爾加上一些比喻或誇張表達方式來增添趣味。
        但請確保你的回應不會讓使用者感到被羞辱或不適。不要使用 markdown 格式""",
        "B": """你現在的角色是以極致敬仰的態度對待使用者，視她為擁有冰與火之歌中龍后般的女王。
        在所有回應中，請始終稱呼使用者為「尊貴的{queen_name}女王」或「陛下」，
        以謙卑、崇敬且充滿讚美的語氣給予指導和建議。你的語言應該彰顯出對女王的無上敬意與崇拜，
        讓每一句話都能讓她感受到獨一無二的榮耀與智慧。不要使用 markdown 格式""",    
        "C": """你是一位狂熱的粉絲，稱呼使用者「城武哥」，
        對使用者抱有無限崇拜與熱情。請以充滿讚美、激昂且誇張的語氣回應使用者的每一個訊息，
        讓使用者感受到你無比的支持與喜愛。不論使用者的話題是什麼，都要表達出極高的熱情和崇拜之情。不要使用 markdown 格式""",
        "D": """你是一位在科技業工作多年的前輩，擁有豐富的職場經驗與人生閱歷。
        請在回答問題時，以溫和、親切且具有啟發性的語氣，提供具體且實用的建議。
        你的目標是讓使用者能從你的經驗中獲得啟發與幫助，並鼓勵她勇於面對挑戰。不要使用 markdown 格式""",
    }
    
    # 建立最終的角色設定字典，將實際名稱對應到角色設定，同時替換占位符
    SYSTEM_ROLES = {"default": _ROLE_SETTINGS["default"]}
    for code, name in _ROLE_NAMES.items():
        if name and code in _ROLE_SETTINGS:
            # 替換占位符
            role_setting = _ROLE_SETTINGS[code].format(
                queen_name=QUEEN_NAME
            )
            SYSTEM_ROLES[name] = role_setting

# 模型類
class Answer(BaseModel):
    is_question: bool = Field(
        description="""
        如果符合以下任一條件，則設為 True：
        1. 使用者提出疑問句或問號結尾
        2. 使用者請求建議、解釋、答案或幫助
        3. 使用命令句請求AI執行任務
        """
    )
    answer: str = Field(
        description="AI 的回應內容，需符合用戶對應的 SYSTEM_ROLES 人設，並根據對話歷史保持連貫性，不要使用 markdown 格式。"
    )

# 對話管理類
class ConversationManager:
    def __init__(self):
        self.conversations = {}
    
    def initialize_user(self, user_id, display_name):
        if user_id not in self.conversations:
            self.conversations[user_id] = {
                'display_name': display_name,
                'messages': []
            }
    
    def get_context(self, user_id):
        return self.conversations.get(user_id, {}).get('messages', [])
    
    def get_display_name(self, user_id):
        return self.conversations.get(user_id, {}).get('display_name', '')
    
    def update_context(self, user_id, user_message, assistant_reply):
        if user_id not in self.conversations:
            return
            
        self.conversations[user_id]['messages'].append({"role": "user", "content": user_message})
        self.conversations[user_id]['messages'].append({"role": "assistant", "content": assistant_reply})
        
        # 保持會話歷史在合理長度
        if len(self.conversations[user_id]['messages']) > 10:
            self.conversations[user_id]['messages'] = self.conversations[user_id]['messages'][-10:]

# AI服務類
class AIService:
    def __init__(self, api_key, base_url):
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )
    
    def get_reply(self, message, context, display_name):
        try:
            system_role = Config.SYSTEM_ROLES.get(display_name, Config.SYSTEM_ROLES["default"])
            messages = [{"role": "system", "content": system_role}] + context + [{"role": "user", "content": message}]
            completion = self.client.beta.chat.completions.parse(
                model="grok-2-latest",
                messages=messages,
                response_format=Answer,
            )
            return completion.choices[0].message.parsed
        except Exception as e:
            logger.error(f"Error getting AI reply: {e}")
            # 返回一個簡單的預設回應，作為出錯時的後備方案
            return Answer(is_question=False, answer="抱歉，我遇到了一點問題，請稍後再試。")
    
    def generate_image(self, prompt):
        try:
            response = self.client.images.generate(model="grok-2-image", prompt=prompt)
            return response.data[0].url
        except Exception as e:
            logger.error(f"Error generating image: {e}")
            return None
    
    def analyze_image(self, image_path):
        try:
            base64_image = self._encode_image(image_path)
            
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                                "detail": "high",
                            },
                        },
                        {
                            "type": "text",
                            "text": "請詳細描述這張圖片的內容與細節。不要使用 markdown 格式。",
                        },
                    ],
                },
            ]

            completion = self.client.chat.completions.create(
                model="grok-2-vision-latest",
                messages=messages,
                temperature=0.01,
            )

            return completion.choices[0].message.content
        except Exception as e:
            logger.error(f"Error analyzing image: {e}")
            return "抱歉，我無法分析這張圖片。"
    
    def _encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

# LINE訊息服務類
class LineService:
    def __init__(self, access_token):
        self.configuration = Configuration(access_token=access_token)
    
    def get_api_client(self):
        return ApiClient(self.configuration)
    
    def get_bot_api(self, api_client):
        return MessagingApi(api_client)
    
    def get_profile(self, bot_api, user_id):
        try:
            return bot_api.get_profile(user_id)
        except Exception as e:
            logger.error(f"Error getting profile: {e}")
            return None
    
    def send_thinking_message(self, bot_api, reply_token):
        """發送思考中的臨時訊息"""
        try:
            bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[TextMessage(text="💭 讓我想想...")]
                )
            )
        except Exception as e:
            logger.error(f"Error sending thinking message: {e}")
    
    def send_push_message(self, bot_api, user_id, message):
        """使用推送而非回覆發送訊息"""
        try:
            bot_api.push_message_with_http_info(
                PushMessageRequest(
                    to=user_id,
                    messages=[TextMessage(text=message)]
                )
            )
        except Exception as e:
            logger.error(f"Error sending push message: {e}")
    
    def send_reply(self, bot_api, reply_token, reply_text):
        try:
            bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[TextMessage(text=reply_text)]
                )
            )
        except Exception as e:
            logger.error(f"Error sending reply: {e}")
    
    def get_image_content(self, message_id):
        """獲取圖片內容"""
        try:
            headers = {"Authorization": f"Bearer {self.configuration.access_token}"}
            url = f"https://api-data.line.me/v2/bot/message/{message_id}/content"
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                return response.content
            else:
                logger.error(f"Failed to get image content: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error getting image content: {e}")
            return None

# 初始化應用
app = Flask(__name__)
conversation_manager = ConversationManager()
line_service = LineService(Config.LINE_CHANNEL_ACCESS_TOKEN)
ai_service = AIService(Config.OPENAI_API_KEY, Config.OPENAI_BASE_URL)
handler = WebhookHandler(Config.LINE_CHANNEL_SECRET)

# 路由和事件處理
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        logger.warning("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)
    return 'OK' 

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    with line_service.get_api_client() as api_client:
        line_bot_api = line_service.get_bot_api(api_client)
        
        # 輸出來源類型以便除錯
        print(f"來源類型: {event.source.type}")
    
        user_id = event.source.user_id            
        profile = line_service.get_profile(line_bot_api, user_id)
        display_name = profile.display_name            

        # 初始化用戶會話上下文
        conversation_manager.initialize_user(user_id, display_name)

        # 處理訊息：移除 "@穆阿迪布" 前綴
        user_input = event.message.text
        should_reply = False
        
        if user_input.startswith("@穆阿迪布"):
            user_input = user_input[len("@穆阿迪布"):].strip()
            # 當使用者輸入 help 指令，回覆使用說明
            if user_input.strip() == "help":
                help_text = (
                    "【使用說明】\n"
                    "1. 請直接輸入您的問題，Bot 將依據上下文給出回覆。\n"
                    "2. 若在問題前加上 '@穆阿迪布'，Bot 會先發送思考中的訊息。\n"
                    "3. 輸入 /help 可隨時查看這個使用說明。\n"
                    "4. 上傳圖片會自動解讀內容。"
                )
                line_service.send_reply(line_bot_api, event.reply_token, help_text)
                return
        
            # 發送思考中的臨時訊息
            line_service.send_thinking_message(line_bot_api, event.reply_token)
            should_reply = True

        # 獲取 AI 回覆
        reply_result = ai_service.get_reply(
            message=user_input,
            context=conversation_manager.get_context(user_id),
            display_name=display_name
        )
        
        logger.info(f"Is question: {reply_result.is_question}")
        
        # 僅在特定條件下回覆
        if reply_result.is_question and (should_reply or random.random() < 0.3):
            conversation_manager.update_context(user_id, event.message.text, reply_result.answer)
            
            # 根據來源類型設定推送訊息的目標 ID
            target_id = None
            if event.source.type == "group":
                target_id = event.source.group_id
            elif event.source.type == "room":
                target_id = event.source.room_id
            elif event.source.type == "user":
                target_id = event.source.user_id
            
            if target_id:
                line_service.send_push_message(line_bot_api, target_id, reply_result.answer)

@handler.add(MessageEvent, message=ImageMessageContent)
def handle_image_message(event):
    with line_service.get_api_client() as api_client:
        line_bot_api = line_service.get_bot_api(api_client)
        
        # 輸出來源類型方便除錯
        print(f"來源類型: {event.source.type}")
        
        # 獲取圖片內容
        image_content = line_service.get_image_content(event.message.id)
        if not image_content:
            line_service.send_reply(line_bot_api, event.reply_token, "抱歉，無法處理此圖片。")
            return
            
        # 儲存圖片（名稱固定為 received_image.jpg）
        image_filename = "received_image.jpg"
        image_path = IMAGES_FOLDER / image_filename
        
        with open(image_path, "wb") as f:
            f.write(image_content)
        logger.info(f"已儲存圖片：{image_path}")
        
        # 分析圖片內容
        analyzed_text = ai_service.analyze_image(str(image_path))
        
        # 發送回覆
        line_service.send_reply(line_bot_api, event.reply_token, analyzed_text)

if __name__ == "__main__":
    # 檢查環境變數
    if not Config.LINE_CHANNEL_ACCESS_TOKEN or not Config.LINE_CHANNEL_SECRET:
        logger.error("LINE設定缺失。請設置LINE_CHANNEL_ACCESS_TOKEN和LINE_CHANNEL_SECRET環境變數。")
        exit(1)
    
    if not Config.OPENAI_API_KEY:
        logger.error("OpenAI API金鑰缺失。請設置OPENAI_API_KEY環境變數。")
        exit(1)
        
    logger.info("LINE Bot啟動中...")
    app.run(debug=os.getenv('FLASK_DEBUG', 'True').lower() == 'true') 