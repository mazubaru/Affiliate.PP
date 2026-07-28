import streamlit as st
import google.generativeai as genai
from supabase import create_client, Client
import datetime

# --- 1. ตั้งค่าความปลอดภัย & เชื่อมต่อ Services ---
# ระบบ Login อย่างง่าย
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        st.text_input("รหัสผ่าน (Password)", type="password", key="pwd")
        if st.session_state["pwd"] == st.secrets["APP_PASSWORD"]:
            st.session_state["password_correct"] = True
            st.rerun()
        elif st.session_state["pwd"]:
            st.error("รหัสผ่านไม่ถูกต้อง")
        return False
    return True

if not check_password():
    st.stop()

# เชื่อมต่อ Supabase และ Gemini จาก st.secrets
supabase: Client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
if st.button("🔍 ตรวจสอบการเชื่อมต่อ Gemini API"):
    try:
        st.write("โมเดลที่คุณสามารถใช้งานได้มีดังนี้:")
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        st.write(models)
        st.success("✅ เชื่อมต่อ API สำเร็จ!")
    except Exception as e:
        st.error(f"❌ เชื่อมต่อไม่ได้ Error: {e}")
model = genai.GenerativeModel('gemini-1.5-flash') # ใช้ 1.5 flash จะเร็วและถูกมาก

# --- 2. ฟังก์ชัน AI สร้างแคปชัน ---
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
        response = model.generate_content(prompt)
        return response.text
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
