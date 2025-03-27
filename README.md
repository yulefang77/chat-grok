
# LINE Bot X.AI

一個基於 LINE Messaging API 和 X.AI 的 Grok 模型整合的聊天機器人，具備多角色人設、圖片分析與生成功能。以沙丘小說中的穆阿迪布為形象，提供風趣、專業且多樣化的對話體驗。

## 功能特色

- **多角色人設對話**：根據用戶設定或隨機分配五種不同聊天風格
- **智能回應控制**：只在被呼喚或問題符合條件時回應
- **沙丘文學主題**：以厄拉科星(沙丘星)穆阿迪布為形象的獨特回應風格
- **圖片分析功能**：上傳圖片自動解析內容並回覆描述
- **圖片生成功能**：根據文字描述自動生成圖片
- **多場景支援**：支援個人聊天、群組和聊天室等不同場景使用
- **訪問權限控制**：可限制特定用戶或群組使用機器人功能
- **檔案自動清理**：定期清理過時的圖片檔案，保持伺服器空間整潔

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
line-bot-xai/
├── app.py               # 主程式，包含 LINE Bot 與 AI 服務邏輯
├── requirements.txt     # 相依套件列表
├── .env                 # 環境變數設定檔（不納入版本控制）
├── static/
│   └── images/          # 存放下載的圖片 (檔名格式: received_image_{user_id}_{timestamp}.jpg)
├── .gitignore           # Git 忽略檔案設定
└── README.md            # 使用說明文件
```

## 使用方式

1. **基本互動**
   - 直接發送訊息有 30% 機率獲得回應
   - 使用「@穆阿迪布」前綴確保必定回應
   - 輸入「@穆阿迪布 help」獲取使用說明

2. **圖片功能**
   - 上傳圖片獲取 AI 分析結果
   - 請求生成圖片，例如「@穆阿迪布 畫一隻在沙漠中的跳鼠」

3. **用戶體驗**
   - 添加機器人為好友可獲得特定角色人設回應
   - 未添加為好友的用戶將隨機獲得五種不同風格的回應
   - 在群組或聊天室中，機器人需被特別邀請且群組 ID 需在允許清單中

## 技術實現

- **多工處理**：使用 Gunicorn 實現多工作進程，提高並發處理能力
- **角色隨機分配**：對於無法獲取 display_name 的用戶，隨機從五種人設中選擇
- **圖片唯一命名**：使用用戶 ID 和時間戳生成唯一檔名，避免圖片覆蓋
- **文件自動清理**：定期刪除過時圖片，防止伺服器空間浪費
- **訊息驗證**：整合 pydantic 進行 API 回應的資料結構驗證

## 自訂人設

本專案預設五種隨機人設：
1. **嚴謹學者幽默型**：精準且風趣，使用專業數據佐證
2. **親切導師幽默型**：溫柔又帶點吐槽精神，講解淺顯易懂
3. **直率專家幽默型**：一針見血、重點明確，融入搞笑吐槽
4. **輕鬆友善幽默型**：平易近人，讓人感覺像在跟老友閒聊
5. **創意思考幽默型**：充滿創意、思維活躍，使用奇思妙想和誇張比喻

您可以修改 `Config._ROLE_SETTINGS` 中的設定，自訂更多人設。

## 版本說明
- **v1.3.0 (2025-03-28)**：改進用戶體驗，新增五種隨機人設，當無法獲取用戶名稱時系統會隨機選擇一種風格回應。修正圖片處理邏輯，現在支援個人、群組和聊天室三種場景的圖片處理。增強防錯機制與代碼穩定性。
- **v1.2.0 (2025-03-27)**：更新圖片儲存機制，改用動態檔名格式 `received_image_{user_id}_{timestamp}.jpg`，並新增檔案自動清理機制。同時新增 `ALLOWED_CHAT_IDS` 環境變數，用於控制允許使用的個人、群組或聊天室。
- **v1.1.0 (2025-03-26)**：新增圖片分析功能，支援圖片上傳與內容分析，並透過環境變數控制存取權限。
- **v1.0.0 (2025-03-25)**：初始版本，上線基本的問答與多角色人設切換功能。

## 常見問題

1. **無法獲取用戶資料**：當用戶未添加機器人為好友時，無法獲取完整的用戶資料。系統會使用隨機人設進行回應。

2. **圖片分析失敗**：確保上傳的圖片格式受支援（JPG、PNG等），且大小不超過 10MB。

3. **API 配額用盡**：若遇到 "You have reached your monthly limit" 錯誤，表示 X.AI API 的使用配額已用完，需要等待下個計費周期或升級計劃。

## 授權資訊
本專案使用 **MIT 授權條款**，請參閱 LICENSE 檔案以獲得更詳細資訊。

## 鳴謝
- [LINE Messaging API](https://developers.line.biz/)
- [X.AI Grok 模型](https://www.x.ai/)
- [Flask Framework](https://flask.palletsprojects.com/)
- [OpenAI](https://openai.com/)
- [沙丘小說系列](https://en.wikipedia.org/wiki/Dune_(novel)) - Frank Herbert
