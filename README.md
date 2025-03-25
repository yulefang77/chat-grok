# LINE 聊天機器人與 X.AI 整合

## 專案簡介
這是一個智能 LINE 聊天機器人，整合了 X.AI (Grok) 模型的能力，可根據使用者身份自動切換人設，並提供個人化的對話體驗與圖片內容分析功能。系統使用 Flask 作為 Web 框架，藉由 LINE Messaging API 與 OpenAI API 為使用者提供即時互動服務。

## 功能特點
- **自動人設切換**：根據使用者名稱自動選擇不同的對話風格與回覆內容。
- **智能問答**：利用 X.AI (Grok) 模型即時回覆使用者提問。
- **圖片分析**：支援圖片上傳，將圖片下載並存放於 `static/images` 資料夾中（固定檔名為 `received_image.jpg`），並進行內容與細節的分析。
- **群組支援**：除了允許指定群組外，目前也支援個別聊天室與一對一聊天模式。
- **指令使用**：推送文字給聊天機器人，在文字訊息中輸入 `help` 可取得使用說明，支援多種互動指令。
- **環境變數管理**：使用 `python-dotenv` 載入環境變數，方便進行憑證與 API 金鑰的管理。

## 技術架構
- **Flask**：輕量級 Python Web 框架。
- **LINE Bot SDK (v3)**：與 LINE 平台進行訊息互動。
- **OpenAI API**：提供 AI 模型回覆及圖片分析功能。
- **Pydantic**：用於建立與驗證數據模型。
- **python-dotenv**：管理環境變數。
- **Requests**：處理 HTTP 請求。
- **Pathlib** 與 **datetime**：處理檔案路徑與檔案命名。

## 安裝步驟

### 前置需求
- Python 3.8 或更高版本
- LINE 開發者帳號與頻道設定
- X.AI API 金鑰

### 操作步驟
1. **複製專案**
   ```bash
   git clone https://github.com/你的用戶名/line-bot-xai.git
   cd line-bot-xai
   ```
2. **安裝相依套件**
   ```bash
   pip install -r requirements.txt
   ```
3. **建立環境變數檔案**
   在專案根目錄下建立一個 `.env` 檔案，並填入以下內容（根據您的設定調整）：
   ```bash
   LINE_CHANNEL_ACCESS_TOKEN=你的LINE頻道存取令牌
   LINE_CHANNEL_SECRET=你的LINE頻道密鑰
   OPENAI_API_KEY=你的X.AI API金鑰
   OPENAI_BASE_URL=https://api.x.ai/v1
   ALLOWED_GROUPS=群組ID1,群組ID2
   QUEEN_NAME=你想替換的女王名稱
   ROLE_CODE_A=預設用戶A
   ROLE_CODE_B=預設用戶B
   ROLE_CODE_C=預設用戶C
   ROLE_CODE_D=預設用戶D
   ```
4. **啟動應用程式**
   ```bash
   python app.py
   ```
5. **設定 Webhook**
   若須本地測試，可使用 [ngrok](https://ngrok.com/) 將本地端口公開，將生成的 URL 配置到 LINE 開發者控制台的 Webhook URL。

## 專案結構
line-bot-xai/
├── app.py               # 主程式，包含 LINE Bot 與 AI 服務邏輯
├── join.py              # 測試或輔助腳本
├── requirements.txt     # 相依套件列表
├── .env                 # 環境變數設定檔（不納入版本控制）
├── static/
│   └── images/          # 存放下載的圖片 (固定檔名: received_image.jpg)
├── .gitignore           # Git 忽略檔案設定
└── README.md            # 使用說明文件

## 版本說明
- **v1.1.0 (2023-12-15)**：新增圖片分析功能，將下載的圖片存至 `static/images` 資料夾中，檔名固定為 `received_image.jpg`，並透過 `ALLOWED_GROUPS` 控制群組的存取權限。
- **v1.0.0 (2023-12-01)**：初始版本，上線基本的問答與多角色人設切換功能。

## 授權資訊
本專案使用 **MIT 授權條款**，請參閱 LICENSE 檔案以獲得更詳細資訊。

## 鳴謝
- [LINE Messaging API](https://developers.line.biz/)
- [X.AI Grok 模型](https://www.x.ai/)
- [Flask Framework](https://flask.palletsprojects.com/)
- [OpenAI](https://openai.com/)
