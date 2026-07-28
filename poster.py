import os
import requests
from supabase import create_client, Client
from datetime import datetime, timezone

# --- 1. ดึงค่าความลับจาก Environment Variables ---
# (ตอนรันบน GitHub Actions ระบบจะดึงค่าจาก Secrets ให้อัตโนมัติ)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ตรวจสอบว่ามี Key ครบไหม (ถ้าทดสอบในคอมแล้วลืมใส่ มันจะแจ้งเตือน)
if not all([SUPABASE_URL, SUPABASE_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
    print("⚠️  ข้อผิดพลาด: หา API Key ไม่ครบ โปรดตรวจสอบ Environment Variables")
    exit()

# เชื่อมต่อฐานข้อมูล
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. ฟังก์ชันยิง API เข้า Telegram ---
def post_to_telegram(caption, image_url):
    """ส่งข้อความและรูปภาพเข้า Telegram"""
    
    # Telegram มีข้อจำกัด: แคปชันรูปภาพต้องยาวไม่เกิน 1024 ตัวอักษร
    caption_to_send = caption[:1000] if len(caption) > 1000 else caption
    
    # กรณีมีรููปภาพ
    if image_url and image_url.strip() != "":
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "photo": image_url,
            "caption": caption_to_send,
            "parse_mode": "Markdown" # รองรับตัวหนา, ตัวเอียง
        }
    # กรณีไม่มีรูปภาพ (ส่งแต่ข้อความ)
    else:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": caption_to_send,
            "parse_mode": "Markdown"
        }
        
    response = requests.post(url, data=payload)
    return response

# --- 3. ฟังก์ชันหลักสำหรับเช็กคิวและโพสต์ ---
def process_queue():
    now = datetime.now(timezone.utc).isoformat()
    print(f"🔍 เริ่มตรวจสอบคิวโพสต์ ณ เวลา: {now}")
    
    try:
        # ดึงข้อมูลจาก Supabase ที่สถานะเป็น pending และถึงเวลาโพสต์แล้ว
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
            
            # ดึงข้อมูลมาเตรียมโพสต์
            content = post['content']
            image_url = post.get('image_url', '')
            
            # ยิงไปที่ Telegram
            res = post_to_telegram(content, image_url)
            
            # ตรวจสอบผลลัพธ์
            if res.status_code == 200:
                print("✅ โพสต์ลง Telegram สำเร็จ!")
                # อัปเดตสถานะในฐานข้อมูลเป็น posted
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
