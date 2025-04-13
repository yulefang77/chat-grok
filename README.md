# LINE Bot X.AI 沙迪鼠

一個基於 LINE Messaging API 和 X.AI 的 Grok 模型整合的聊天機器人，融合專業與幽默的對話風格。

## 功能特色

- **智慧回應控制**：
  - 主動呼叫：使用 "@沙迪鼠" 前綴確保回應
  - 隨機回應：5% 機率自動回應一般對話
- **對話歷史管理**：
  - 保存最近 10 則對話內容
  - 30 分鐘無互動後自動清除
- **多場景支援**：支援個人聊天、群組和聊天室
- **權限控制**：可限制特定用戶或群組的使用權限

## 技術規格

- **AI 模型**：X.AI Grok-3 Mini Fast Beta
- **推理模式**：Medium
- **回應限制**：每則 200 字以內

## 安裝與設定

1. **複製專案**
   ```bash
   git clone [您的儲存庫網址]
   cd chat-grok
   ```

2. **安裝相依套件**
   ```bash
   pip install -r requirements.txt
   ```

3. **環境變數設定**
   建立 `.env` 檔案：
   ```bash
   LINE_CHANNEL_ACCESS_TOKEN=您的LINE頻道存取令牌
   LINE_CHANNEL_SECRET=您的LINE頻道密鑰
   OPENAI_API_KEY=您的X.AI API金鑰
   OPENAI_BASE_URL=https://api.x.ai/v1
   ALLOWED_CHAT_IDS=允許的ID列表（用逗號分隔）
   ```

4. **啟動服務**
   ```bash
   python app.py
   ```

## 使用方式

### 基本指令
- `@沙迪鼠 help`：顯示使用說明
- `@沙迪鼠 <您的問題>`：直接詢問任何問題

### 注意事項
- 需要將聊天 ID 加入允許清單才能使用
- 群組使用時需要邀請機器人加入群組

## 系統需求
- Python 3.8+
- Flask 3.1.0
- LINE Bot SDK 3.16.2
- OpenAI API 1.66.3

## 授權資訊
本專案採用 MIT 授權條款
