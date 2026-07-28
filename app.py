import streamlit as st
import google.generativeai as genai
from supabase import create_client, Client
import datetime

# --- 1. ตั้งค่าความปลอดภัย & ระบบ Login ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        st.text_input("รหัสผ่าน (Password) เพื่อเข้าใช้งาน", type="password", key="pwd")
        if st.session_state["pwd"] == st.secrets["APP_PASSWORD"]:
            st.session_state["password_correct"] = True
            st.rerun()
        elif st.session_state["pwd"]:
            st.error("รหัสผ่านไม่ถูกต้อง")
        return False
    return True

if not check_password():
    st.stop()

# --- 2. เชื่อมต่อ Services (Supabase & Gemini แบบดั้งเดิม) ---

# เชื่อมต่อ Database (Supabase)
supabase: Client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# เชื่อมต่อ Gemini API (ใช้ไลบรารี google-generativeai)
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# ตั้งค่าชื่อโมเดลที่คุณรันผ่าน (ถ้า 3.5-flash เวิร์ก สามารถเปลี่ยนเป็นชื่อนั้นได้เลยครับ)
model = genai.GenerativeModel('gemini-3.5-flash') 


# --- 3. ฟังก์ชัน AI สร้างแคปชัน ---
def generate_captions(product_name, product_link, provider="gemini"):
    prompt = f"""
    คุณคือนักการตลาด Affiliate มืออาชีพ ช่วยเขียนแคปชันขายสินค้าชื่อ: "{product_name}" 
    ลิงก์สินค้า: {product_link}
    
    โปรดเขียนแยก 4 แพลตฟอร์มตามกฎนี้:
    1. Facebook: สั้นกระชับ (4-5 บรรทัด) เน้นจุดเด่นเป็นข้อๆ + แฮชแท็ก 3-4 อัน
    2. Threads: โทนเป็นกันเองเหมือนเพื่อนเล่าให้ฟัง ไม่เน้นขายตรง
    3. Twitter/X: สั้นมาก (ไม่เกิน 200 ตัวอักษร) ภาษาวัยรุ่น + แฮชแท็ก 1-2 อัน
    4. Telegram: เน้นบอกดีลเด็ด ราคา ตัวหนา (ใช้ markdown **ข้อความ**) พร้อม Bullet Points
    
    ตอบกลับมาโดยแยกหัวข้อชัดเจน
    """
    
    if provider == "gemini":
        try:
            # ใช้คำสั่ง generate_content ของเวอร์ชันดั้งเดิม
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"❌ เกิดข้อผิดพลาดจาก API: {e}"
            
    return "API Provider not supported yet."

# --- 3. หน้าจอ UI (Streamlit) ---
st.title("🤖 Affiliate Auto-Poster")
st.write("วางลิงก์ เจนแคปชัน แล้วตั้งเวลาโพสต์!")

col1, col2 = st.columns(2)
with col1:
    product_name = st.text_input("ชื่อสินค้า (สั้นๆ)")
with col2:
    product_link = st.text_input("ลิงก์สินค้า (Shopee/Lazada)")
    
image_url = st.text_input("ลิงก์รูปภาพสินค้า (หรือจะต่อยอดให้อัปโหลดไฟล์ก็ได้)")

if st.button("✨ เจนแคปชันด้วย AI (Gemini)"):
    if product_name and product_link:
        with st.spinner("AI กำลังคิดแคปชัน..."):
            captions = generate_captions(product_name, product_link)
            st.session_state['captions'] = captions
            st.success("สร้างแคปชันสำเร็จ!")
    else:
        st.warning("กรุณาใส่ชื่อสินค้าและลิงก์")

if 'captions' in st.session_state:
    st.markdown("### 📝 ตรวจสอบและแก้ไขแคปชัน")
    edited_caption = st.text_area("แก้ไขข้อความก่อนโพสต์ได้ที่นี่", value=st.session_state['captions'], height=300)
    
    post_date = st.date_input("วันที่ต้องการโพสต์", min_value=datetime.date.today())
    post_time = st.time_input("เวลาที่ต้องการโพสต์")
    
    if st.button("🚀 อนุมัติและบันทึกลงคิวโพสต์"):
        schedule_datetime = datetime.datetime.combine(post_date, post_time).isoformat()
        
        # บันทึกลง Database (Supabase)
        try:
            data = {
                "product_name": product_name,
                "content": edited_caption,
                "image_url": image_url,
                "schedule_time": schedule_datetime,
                "status": "pending"
            }
            supabase.table("scheduled_posts").insert(data).execute()
            st.success(f"✅ บันทึกลงคิวเรียบร้อย! ระบบจะโพสต์อัตโนมัติในวันที่ {schedule_datetime}")
            del st.session_state['captions'] # ล้างค่าหลังบันทึกเสร็จ
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาด: {e}")
