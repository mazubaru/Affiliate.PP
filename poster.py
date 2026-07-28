import os
import requests
from supabase import create_client, Client
from datetime import datetime, timezone

# ดึงค่าจาก Environment Variables (ที่ตั้งไว้ใน GitHub Secrets)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def post_to_telegram(content, image_url):
    """ตัวอย่างฟังก์ชันยิง API ไปยัง Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "photo": image_url,
        "caption": content,
        "parse_mode": "Markdown"
    }
    response = requests.post(url, data=payload)
    return response.status_code == 200

def process_queue():
    now = datetime.now(timezone.utc).isoformat()
    
    # ดึงคิวที่ status = pending และถึงเวลาโพสต์แล้ว
    response = supabase.table("scheduled_posts") \
        .select("*") \
        .eq("status", "pending") \
        .lte("schedule_time", now) \
        .execute()
        
    posts = response.data
    
    for post in posts:
        print(f"กำลังโพสต์สินค้า: {post['product_name']}")
        
        # 1. ยิง API โพสต์ลง Social (ในที่นี้ทำตัวอย่าง Telegram)
        success = True
        try:
            post_to_telegram(post['content'], post['image_url'])
            # TODO: เพิ่มฟังก์ชัน post_to_facebook(), post_to_twitter() ตรงนี้ในอนาคต
        except Exception as e:
            print(f"Error posting: {e}")
            success = False
            
        # 2. อัปเดตสถานะใน Database
        if success:
            supabase.table("scheduled_posts") \
                .update({"status": "posted"}) \
                .eq("id", post['id']) \
                .execute()
            print(f"โพสต์สำเร็จและอัปเดตสถานะแล้ว: {post['id']}")

if __name__ == "__main__":
    process_queue()