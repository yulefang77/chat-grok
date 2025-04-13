# LINE Bot 沙迪鼠 AI 助手

一個基於 LINE Messaging API 和 X.AI Grok 模型的智慧聊天機器人，具有專業且風趣的對話風格。

## 功能特點

- 🤖 智慧對話：使用 X.AI Grok-3 Mini Fast Beta 模型，提供精準且富有趣味的回應
- 🔄 彈性觸發機制：
  - 直接標記：使用 `@沙迪鼠` 前綴確保回應
  - 隨機回應：5% 機率自動回覆一般對話
- 📜 對話管理：
  - 保留最近 10 則對話記錄
  - 30 分鐘無互動自動清除歷史
  - 可查看歷史對話紀錄
- 🔐 安全性：
  - 支援白名單機制
  - 可限制特定用戶或群組使用

## 系統需求

- Python 3.8+
- Flask 3.1.0
- LINE Bot SDK 3.16.2
- OpenAI API 1.66.3
- 其他依賴參見 requirements.txt

## 安裝步驟

1. **下載專案**
```bash
git clone [儲存庫URL]
cd chat-grok
```

2. **安裝相依套件**
```bash
pip install -r requirements.txt
```

3. **環境設定**
建立 `.env` 檔案並設定以下變數：
```plain
LINE_CHANNEL_ACCESS_TOKEN=您的LINE通道存取權杖
LINE_CHANNEL_SECRET=您的LINE通道密鑰
OPENAI_API_KEY=您的X.AI API金鑰
OPENAI_BASE_URL=https://api.x.ai/v1
ALLOWED_CHAT_IDS=允許的ID列表（以逗號分隔）
```

4. **啟動服務**
```bash
python app.py
```

## 使用方式

### 基本指令
- **一般對話**：直接傳送訊息（5% 機率獲得回應）
- **主動呼叫**：訊息前加 `@沙迪鼠`
- **查看說明**：`@沙迪鼠 help`
- **歷史記錄**：`@沙迪鼠 history`

### 注意事項
- 需將聊天 ID 加入允許清單才能使用
- 群組使用需先邀請機器人加入
- 回答預設限制在 200 字以內
- 歷史記錄保留 30 分鐘

## 開發資訊

- 機器人名稱：沙迪鼠
- AI 模型：X.AI Grok-3 Mini Fast Beta
- 推理模式：Medium
- 回應限制：每則 200 字以內

## 授權條款

此專案採用 MIT 授權條款