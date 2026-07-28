import os
import requests
from supabase import create_client, Client
from datetime import datetime, timezone, timedelta

# --- ดึงค่าความลับจาก Environment Variables ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not all([SUPABASE_URL, SUPABASE_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
    print("⚠️ ข้อผิดพลาด: หา API Key ไม่ครบ โปรดตรวจสอบ Environment Variables")
    exit()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def post_to_telegram(caption):
    """ส่งข้อความเข้า Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": caption,
        "parse_mode": "Markdown"
    }
    response = requests.post(url, data=payload)
    return response

def process_queue():
    # --- กำหนดโซนเวลาประเทศไทย (GMT+7) เพื่อดึงเวลาปัจจุบันของไทยมาเทียบ ---
    TH_TZ = timezone(timedelta(hours=7))
    now = datetime.now(TH_TZ).isoformat()
    
    print(f"🔍 เริ่มตรวจสอบคิวโพสต์ ณ เวลาไทย: {now}")
    
    try:
        # ดึงข้อมูลที่สถานะเป็น pending และถึงเวลา (หรือเลยเวลา) แล้ว
        response = supabase.table("scheduled_posts") \
            .select("*") \
            .eq("status", "pending") \
            .lte("schedule_time", now) \
            .execute()
            
        posts = response.data
        
        if not posts:
            print("💤 ยังไม่มีคิวโพสต์ที่ถึงเวลาในตอนนี้")
            return
            
        for post in posts:
            print(f"🚀 กำลังโพสต์สินค้า: {post.get('product_name', 'ไม่ทราบชื่อ')}")
            content = post['content']
            
            # ยิงเข้า Telegram
            res = post_to_telegram(content)
            
            if res.status_code == 200:
                print("✅ โพสต์ลง Telegram สำเร็จ!")
                # เปลี่ยนสถานะในฐานข้อมูลเป็น posted
                supabase.table("scheduled_posts") \
                    .update({"status": "posted"}) \
                    .eq("id", post['id']) \
                    .execute()
            else:
                print(f"❌ โพสต์ไม่สำเร็จ API ตอบกลับมาว่า: {res.text}")
                
    except Exception as e:
        print(f"🚨 ระบบเกิดข้อผิดพลาด: {e}")

if __name__ == "__main__":
    process_queue()
