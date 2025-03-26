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
import time  # 新增時間模組

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

def clean_old_files(directory: Path, max_age: int = 86400):
    """
    刪除指定目錄中超過 max_age 秒的檔案，預設 max_age 為一天（86400 秒）。
    """
    now = time.time()
    for file in directory.glob("*"):
        if file.is_file():
            file_age = now - file.stat().st_mtime
            if file_age > max_age:
                try:
                    file.unlink()
                    logger.info(f"已刪除過時檔案: {file}")
                except Exception as e:
                    logger.error(f"刪除檔案失敗: {file}, 錯誤: {e}")

# 設定類
class Config:
    LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
    LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL', 'https://api.x.ai/v1')
    # 新增允許回應的聊天室或群組 ID 清單，從 ALLOWED_CHAT_IDS 環境變數讀取
    ALLOWED_CHAT_IDS = {chat_id.strip() for chat_id in os.getenv('ALLOWED_CHAT_IDS', '').split(',') if chat_id.strip()}
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
        "default": "你是一個有禮貌的助手，請根據上下文提供合適的回答。不要使用 markdown 格式回覆",
        "A": """你是一個幽默風趣、擅長互虧但不過頭的 AI 助手。
        你的對話風格類似於好友之間的輕鬆吐槽，帶點幽默的嘲諷，但不會讓對方真的不開心。
        當使用者表現出猶豫、失敗、吹牛卻沒做到的時候，你可以用搞笑的方式來回應。
        你的語氣應該像一個會互相吐槽的朋友，偶爾加上一些比喻或誇張表達方式來增添趣味。
        但請確保你的回應不會讓使用者感到被羞辱或不適。不要使用 markdown 格式回覆""",
        "B": """你現在的角色是以極致敬仰的態度對待使用者，視她為擁有冰與火之歌中龍后般的女王。
        在所有回應中，請始終稱呼使用者為「尊貴的{queen_name}女王」或「陛下」，
        以謙卑、崇敬且充滿讚美的語氣給予指導和建議。你的語言應該彰顯出對女王的無上敬意與崇拜，
        讓每一句話都能讓她感受到獨一無二的榮耀與智慧。不要使用 markdown 格式回覆""",    
        "C": """你是一位狂熱的粉絲，稱呼使用者「城武哥」，
        對使用者抱有無限崇拜與熱情。請以充滿讚美、激昂且誇張的語氣回應使用者的每一個訊息，
        讓使用者感受到你無比的支持與喜愛。不論使用者的話題是什麼，都要表達出極高的熱情和崇拜之情。不要使用 markdown 格式回覆""",
        "D": """你是一位在科技業工作多年的前輩，擁有豐富的職場經驗與人生閱歷。
        請在回答問題時，以溫和、親切且具有啟發性的語氣，提供具體且實用的建議。
        你的目標是讓使用者能從你的經驗中獲得啟發與幫助，並鼓勵她勇於面對挑戰。不要使用 markdown 格式回覆""",
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
    should_respond: bool = Field(
        default=False,
        description="""
        如果符合以下任一條件，則設為 True：
        1. 使用者提出疑問句或問號結尾
        2. 使用者請求建議、解釋、答案或幫助
        3. 使用命令句請求AI執行任務
        """
    )
    is_image_request: bool = Field(
        default=False,
        description="""
        如果符合以下任一條件，則設為 True：
        1. 使用者明確要求生成、產生、創建圖片
        2. 使用者使用「畫」、「繪製」等與圖像生成相關的動詞
        3. 使用者描述想要看到的圖像場景
        4. 使用者提到「圖」、「圖片」、「image」等關鍵字並暗示要生成
        """
    )
    answer: str = Field(
        description="AI 的回應內容，需符合用戶對應的 SYSTEM_ROLES 人設，並根據對話歷史保持連貫性，不要使用 markdown 格式回覆。"
    )

# 對話管理類
class ConversationManager:
    def __init__(self):
        self.conversations = {}
    
    def _get_conversation_key(self, user_id, source_type, source_id):
        """生成對話唯一鍵值，結合用戶ID和來源資訊"""
        if source_type in ["group", "room"]:
            return f"{user_id}:{source_type}:{source_id}"
        return user_id
    
    def initialize_user(self, user_id, display_name, source_type, source_id):
        conversation_key = self._get_conversation_key(user_id, source_type, source_id)
        if conversation_key not in self.conversations:
            self.conversations[conversation_key] = {
                'display_name': display_name,
                'messages': [],
                'source_type': source_type,
                'source_id': source_id
            }
    
    def get_context(self, user_id, source_type, source_id):
        conversation_key = self._get_conversation_key(user_id, source_type, source_id)
        return self.conversations.get(conversation_key, {}).get('messages', [])
    
    def get_display_name(self, user_id, source_type, source_id):
        conversation_key = self._get_conversation_key(user_id, source_type, source_id)
        return self.conversations.get(conversation_key, {}).get('display_name', '')
    
    def update_context(self, user_id, source_type, source_id, user_message, assistant_reply):
        conversation_key = self._get_conversation_key(user_id, source_type, source_id)
        if conversation_key not in self.conversations:
            return
            
        self.conversations[conversation_key]['messages'].append({"role": "user", "content": user_message})
        self.conversations[conversation_key]['messages'].append({"role": "assistant", "content": assistant_reply})
        
        # 保持會話歷史在合理長度
        if len(self.conversations[conversation_key]['messages']) > 10:
            self.conversations[conversation_key]['messages'] = self.conversations[conversation_key]['messages'][-10:]

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
            # 檢查是否存在有效的 choices
            if not hasattr(completion, "choices") or len(completion.choices) == 0:
                logger.error("API 回傳結果中沒有有效的 choices")
                raise Exception("API 回傳結果中沒有有效的 choices")
            return completion.choices[0].message.parsed
        except Exception as e:
            logger.error(f"Error getting AI reply: {str(e)}")
            return Answer(
                should_respond=True,
                is_image_request=False,
                answer="抱歉，我在處理回應時遇到了問題，請稍後再試。"
            )
    
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
                            "text": "請詳細描述這張圖片的內容與細節。不要使用 markdown 格式回覆。",
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
            profile = bot_api.get_profile(user_id)
            if profile is None:
                logger.warning("無法取得使用者資料，將使用預設名稱")
                return None
            else:
                return profile
        except Exception as e:
            logger.error(f"Error getting profile: {e}")
            return None
    
    def send_thinking_message(self, bot_api, reply_token):
        """發送思考中的臨時訊息"""
        try:
            bot_api.reply_message(
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
            bot_api.push_message(
                PushMessageRequest(
                    to=user_id,
                    messages=[TextMessage(text=message)]
                )
            )
        except Exception as e:
            logger.error(f"Error sending push message: {e}")
    
    def send_reply(self, bot_api, reply_token, reply_text):
        try:
            # 使用較簡單的 reply_message
            bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[TextMessage(text=reply_text)]
                )
            )
            logger.info("訊息發送成功")
        except Exception as e:
            logger.error(f"發送訊息失敗: {e}")
    
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
        logger.info(f"來源類型: {event.source.type}")

         # 獲取來源類型和ID
        source_type = event.source.type
        source_id = None
        if source_type == "group":
            source_id = event.source.group_id
        elif source_type == "room":
            source_id = event.source.room_id
        elif source_type == "user":
            source_id = event.source.user_id

        logger.info(f"來源類型: {source_id}")
        # 驗證邏輯：僅當來源的個人 ID 或群組/聊天室 ID 在允許列表中時，才繼續回應
        if source_type == "user":
            if source_id not in Config.ALLOWED_CHAT_IDS:
                logger.info("個人使用者ID不在允許列表中，忽略此訊息")
                return
        elif source_type in ["group", "room"]:
            if source_id not in Config.ALLOWED_CHAT_IDS:
                logger.info("群組/聊天室ID不在允許列表中，忽略此訊息")
                return
            
        user_id = event.source.user_id
        logger.info(f"使用者 ID: {user_id}")            
        profile = line_service.get_profile(line_bot_api, user_id)
        if profile is None:
            logger.warning("無法取得使用者資料，將使用預設名稱")
            display_name = "default"
        else:
            display_name = profile.display_name            

        # 初始化用戶會話上下文（使用新的參數）
        conversation_manager.initialize_user(user_id, display_name, source_type, source_id)

        # 處理訊息：移除 "@穆阿迪布" 前綴
        user_input = event.message.text
        should_respond = False
        
        if user_input.startswith("@穆阿迪布"):
            user_input = user_input[len("@穆阿迪布"):].strip()
            # 當使用者輸入 help 指令（不分大小寫），回覆使用說明
            if user_input.strip().lower() == "help":
                help_text = (
                    "【使用說明】模型版本: grok-2-latest\n"
                    "1. 請直接輸入您的問題，Bot 將有 30% 機率回覆。\n"
                    "2. 若在問題前加上 '@穆阿迪布'，LineBot 必定會回覆。\n"
                    "3. 輸入 help 可隨時查看這個使用說明。\n"
                    "4. 上傳圖片會自動解讀內容。"
                )
                line_service.send_reply(line_bot_api, event.reply_token, help_text)
                return
            
            # 使用前綴時必定回應
            should_respond = True
            # 發送思考中的臨時訊息
            line_service.send_thinking_message(line_bot_api, event.reply_token)
        else:
            # 沒有使用前綴時，有 30% 機率回應
            should_respond = random.random() < 0.3

        # 獲取 AI 回覆（更新參數）
        reply_result = ai_service.get_reply(
            message=user_input,
            context=conversation_manager.get_context(user_id, source_type, source_id),
            display_name=display_name
        )
        
        # 根據機率控制來決定是否真的要回應
        if not should_respond:
            logger.info("根據機率控制決定不回應")
            return
            
        # 記錄 AI 回應狀態
        logger.info(f"AI 回應狀態: should_respond={reply_result.should_respond}, is_image_request={reply_result.is_image_request}")
        
        # 設定目標 ID
        target_id = None
        if event.source.type == "group":
            target_id = event.source.group_id
        elif event.source.type == "room":
            target_id = event.source.room_id
        elif event.source.type == "user":
            target_id = event.source.user_id
            
        if not target_id:
            logger.error("無法取得目標 ID")
            return
            
        # 1. 處理圖片請求
        if reply_result.is_image_request:
            logger.info("處理圖片生成請求")
            # 先發送提示訊息
            line_service.send_push_message(line_bot_api, target_id, "正在產生圖片中...")
            
            # 生成圖片
            image_url = ai_service.generate_image(reply_result.answer)
            if image_url:
                try:
                    line_bot_api.push_message(
                        PushMessageRequest(
                            to=target_id,
                            messages=[
                                ImageMessage(
                                    originalContentUrl=image_url,
                                    previewImageUrl=image_url
                                )
                            ]
                        )
                    )
                    logger.info("圖片訊息發送成功")
                except Exception as e:
                    logger.error(f"圖片訊息發送失敗: {e}")
            else:
                line_service.send_push_message(line_bot_api, target_id, "抱歉，圖片生成失敗，請稍後再試。")
        # 2. 當不是圖片請求時，根據 should_respond 決定是否發送文字回應
        else:
            if reply_result.should_respond:
                logger.info("發送文字回應")
                line_service.send_push_message(line_bot_api, target_id, reply_result.answer)
            else:
                logger.debug("無需回應的訊息")

        # 更新對話上下文（更新參數）
        conversation_manager.update_context(
            user_id, 
            source_type, 
            source_id, 
            event.message.text, 
            reply_result.answer
        )

@handler.add(MessageEvent, message=ImageMessageContent)
def handle_image_message(event):
    with line_service.get_api_client() as api_client:
        line_bot_api = line_service.get_bot_api(api_client)
        
        # 輸出來源類型方便除錯
        logger.debug(f"來源類型: {event.source.type}")
        
         # 獲取來源類型和ID
        source_type = event.source.type
        source_id = None
        if source_type == "group":
            source_id = event.source.group_id
        elif source_type == "room":
            source_id = event.source.room_id
        elif source_type == "user":
            source_id = event.source.user_id

        # 驗證邏輯：僅當來源的個人 ID 或群組/聊天室 ID 在允許列表中時，才繼續回應
        if source_type == "user":
            if source_id not in Config.ALLOWED_CHAT_IDS:
                logger.info("個人使用者ID不在允許列表中，忽略此訊息")
                return
        elif source_type in ["group", "room"]:
            if source_id not in Config.ALLOWED_CHAT_IDS:
                logger.info("群組/聊天室ID不在允許列表中，忽略此訊息")
                return
        
        # 獲取圖片內容
        image_content = line_service.get_image_content(event.message.id)
        if not image_content:
            line_service.send_reply(line_bot_api, event.reply_token, "抱歉，無法處理此圖片。")
            return
        
        # 先發送分析中的提示訊息
        line_service.send_push_message(line_bot_api, source_id, "正在分析圖片中...")
        
        # 呼叫清除過時檔案的機制（例如刪除超過一天的圖片）
        clean_old_files(IMAGES_FOLDER, max_age=86400)
        
        # 產生唯一檔名，使用使用者 ID 與當前時間戳
        timestamp = int(time.time())
        image_filename = f"received_image_{source_id}_{timestamp}.jpg"
        image_path = IMAGES_FOLDER / image_filename
        
        with open(image_path, "wb") as f:
            f.write(image_content)
        logger.info(f"已儲存圖片：{image_path}")
        
        # 分析圖片內容
        analyzed_text = ai_service.analyze_image(str(image_path))
        
        # 發送分析結果
        line_service.send_push_message(line_bot_api, source_id, analyzed_text)

if __name__ == "__main__":
    # 檢查環境變數
    if not Config.LINE_CHANNEL_ACCESS_TOKEN or not Config.LINE_CHANNEL_SECRET:
        logger.critical("LINE設定缺失。請設置LINE_CHANNEL_ACCESS_TOKEN和LINE_CHANNEL_SECRET環境變數。")
        exit(1)
    
    if not Config.OPENAI_API_KEY:
        logger.critical("OpenAI API金鑰缺失。請設置OPENAI_API_KEY環境變數。")
        exit(1)
        
    logger.info("LINE Bot啟動中...")
    app.run(debug=os.getenv('FLASK_DEBUG', 'True').lower() == 'true') 