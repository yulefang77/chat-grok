# LINE Bot X.AI

一個基於 LINE Messaging API 和 X.AI 的 Grok 模型整合的聊天機器人，具備多角色人設、圖片分析與生成功能。

## 功能特色

- **多角色人設對話**：根據用戶設定或隨機分配不同聊天風格
- **智能回應控制**：只在被呼喚或問題符合條件時回應
- **沙丘文學主題**：以厄拉科星(沙丘星)穆阿迪布為形象的獨特回應風格
- **圖片分析功能**：上傳圖片自動解析內容並回覆描述
- **圖片生成功能**：根據文字描述自動生成圖片
- **多場景支援**：支援個人聊天、群組和聊天室等不同場景使用
- **訪問權限控制**：可限制特定用戶或群組使用機器人功能

## 安裝與設定

1. **複製項目**
   ```bash
   git clone https://github.com/yourusername/line-bot-xai.git
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
   ALLOWED_CHAT_IDS=個人ID1,群組ID1,聊天室ID1
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
   或使用Gunicorn多工作進程部署（建議生產環境）：
   ```bash
   gunicorn app:app --workers=3
   ```

5. **設定 Webhook**
   若須本地測試，可使用 [ngrok](https://ngrok.com/) 將本地端口公開，將生成的 URL 配置到 LINE 開發者控制台的 Webhook URL。

## 專案結構
```