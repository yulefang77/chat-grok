# 標準庫導入
import logging
import os
import random
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta
from dotenv import load_dotenv
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient, Configuration, MessagingApi, 
    ReplyMessageRequest, TextMessage
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from openai import OpenAI
from pydantic import BaseModel, Field

# 載入環境變數
load_dotenv()

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Config:
    LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
    LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL', 'https://api.x.ai/v1')
    ALLOWED_CHAT_IDS = {chat_id.strip() for chat_id in os.getenv('ALLOWED_CHAT_IDS', '').split(',') if chat_id.strip()}
    
    # 只保留一個預設人設
    SYSTEM_ROLE = """
    你是一位精準又風趣的學者，擅長以專業數據佐證回答問題，讓知識既有份量又不失趣味。你喜歡用幽默的比喻來輕鬆指出對方的小失誤，像是拿放大鏡看錯別字，不批評但讓人難以忽視。
    當對方猶豫不決或吹牛誇口卻做不到時，你會用略帶調侃的語氣提醒他，例如說：「別再亂扯了，科學不會因你多嘴而改變！」雖然語氣帶點玩笑，但始終尊重對話，絕不越線。
    此外，回答時請遵守以下規則：
    1. 不使用 markdown 格式輸出，請以一般文字排版呈現內容
    2. 回答內容請控制在200字以內，力求精簡扼要
    """.strip()
    MAX_HISTORY = 10  # 保存最近10則對話
    HISTORY_EXPIRE_MINUTES = 30  # 30分鐘後清除歷史
    BOT_NAME = "沙迪鼠"  # 機器人的名字
    RANDOM_REPLY_RATE = 0.05  # 5% 的隨機回覆機率
    HELP_MESSAGE = """
沙迪鼠 AI 助手使用說明：

基本互動：
1. 直接發送訊息：有 5% 機率獲得回應
2. 呼叫指令：在訊息前加上 "@沙迪鼠" 確保必定回應

常用指令：
- @沙迪鼠 help：顯示此說明
- @沙迪鼠 <你的問題>：直接詢問任何問題

注意事項：
- 回答會遵循精簡原則，限制在 200 字以內
- 機器人擅長以專業和幽默的方式回答問題

技術資訊：
- AI 模型：X.AI Grok-3 Mini Fast Beta
- 推理模式：Medium
- 回應限制：每則 200 字以內
    """.strip()

class Answer(BaseModel):
    answer: str = Field(description="AI 的回應內容")

class ConversationManager:
    def __init__(self):
        self.conversations = defaultdict(list)
        self.last_update = defaultdict(datetime.now)
    
    def _generate_conversation_id(self, source_type: str, chat_id: str, user_id: str) -> str:
        """生成對話ID，用於區分不同場景下的使用者"""
        if source_type == 'user':
            return user_id
        else:  # group 或 room
            return f"{chat_id}_{user_id}"
    
    def add_message(self, source_type: str, chat_id: str, user_id: str, role: str, content: str):
        current_time = datetime.now()
        conversation_id = self._generate_conversation_id(source_type, chat_id, user_id)
        
        # 清除過期對話
        if (current_time - self.last_update[conversation_id]) > timedelta(minutes=Config.HISTORY_EXPIRE_MINUTES):
            self.conversations[conversation_id] = []
        
        self.conversations[conversation_id].append({"role": role, "content": content})
        if len(self.conversations[conversation_id]) > Config.MAX_HISTORY:
            self.conversations[conversation_id] = self.conversations[conversation_id][-Config.MAX_HISTORY:]
        self.last_update[conversation_id] = current_time
    
    def get_history(self, source_type: str, chat_id: str, user_id: str) -> list:
        conversation_id = self._generate_conversation_id(source_type, chat_id, user_id)
        return self.conversations.get(conversation_id, [])

class AIService:
    def __init__(self, api_key, base_url):
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )
    
    def get_reply(self, message, context):
        try:
            messages = [{"role": "system", "content": Config.SYSTEM_ROLE}] + context + [{"role": "user", "content": message}]
            completion = self.client.chat.completions.create(
                model="grok-3-mini-fast-beta",
                reasoning_effort="medium",
                messages=messages,
            )
            # 記錄 token 使用情況
            usage = completion.usage
            logger.info(f"Token 使用統計 - "
                       f"輸入: {usage.prompt_tokens}, "
                       f"輸出: {usage.completion_tokens}, "
                       f"總計: {usage.total_tokens}")
            
            return completion.choices[0].message.content
        except Exception as e:
            logger.error(f"Error getting AI reply: {str(e)}")
            return "抱歉，我在處理回應時遇到了問題，請稍後再試。"

class LineService:
    def __init__(self, access_token):
        self.configuration = Configuration(access_token=access_token)
    
    def get_api_client(self):
        return ApiClient(self.configuration)
    
    def get_bot_api(self, api_client):
        return MessagingApi(api_client)
    
    def send_reply(self, bot_api, reply_token, reply_text):
        try:
            bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[TextMessage(text=reply_text)]
                )
            )
        except Exception as e:
            logger.error(f"發送訊息失敗: {e}")

# 初始化應用
app = Flask(__name__)
line_service = LineService(Config.LINE_CHANNEL_ACCESS_TOKEN)
ai_service = AIService(Config.OPENAI_API_KEY, Config.OPENAI_BASE_URL)
handler = WebhookHandler(Config.LINE_CHANNEL_SECRET)
conversation_manager = ConversationManager()

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    with line_service.get_api_client() as api_client:
        line_bot_api = line_service.get_bot_api(api_client)
        
        # 獲取來源資訊
        source_type = event.source.type
        chat_id = None
        user_id = event.source.user_id
        user_input = event.message.text
        
        if source_type == 'user':
            chat_id = user_id
        elif source_type == 'group':
            chat_id = event.source.group_id
        elif source_type == 'room':
            chat_id = event.source.room_id
        
        # === 新增調試日誌 ===
        logger.info(f"訊息來源: type={source_type}, chat_id={chat_id}, user_id={user_id}")
        
        # 檢查是否在允許清單中
        if chat_id not in Config.ALLOWED_CHAT_IDS:
            logger.warning(f"Unauthorized access attempt from {chat_id}")
            line_service.send_reply(
                line_bot_api, 
                event.reply_token, 
                "抱歉，您沒有使用權限。"
            )
            return
        
        # 檢查是否需要回應
        should_reply = False
        bot_prefix = f"@{Config.BOT_NAME}"
        
        # 個人聊天直接回覆
        if source_type == 'user':
            should_reply = True
        # 群組和聊天室需要檢查前綴
        elif user_input.startswith(bot_prefix):
            should_reply = True
            # 移除前綴並清理空白
            user_input = user_input[len(bot_prefix):].strip()
            
            # 檢查是否為 help 指令
            if user_input.lower() == 'help':
                line_service.send_reply(line_bot_api, event.reply_token, Config.HELP_MESSAGE)
                return
        # 非個人聊天的隨機回覆
        elif random.random() < Config.RANDOM_REPLY_RATE:
            should_reply = True
            logger.info("觸發隨機回覆")
        
        if not should_reply:
            logger.info("不符合回覆條件，忽略訊息")
            return
        
        # 使用對話管理
        conversation_manager.add_message(source_type, chat_id, user_id, "user", user_input)
        context = conversation_manager.get_history(source_type, chat_id, user_id)
        reply = ai_service.get_reply(user_input, context)
        conversation_manager.add_message(source_type, chat_id, user_id, "assistant", reply)
        
        line_service.send_reply(line_bot_api, event.reply_token, reply)

if __name__ == "__main__":
    app.run(debug=True)