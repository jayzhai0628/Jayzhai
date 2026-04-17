import streamlit as st
import requests
from datetime import datetime
import pytz
from fpdf import FPDF
import io
import os

# --- 1. 页面基础配置 ---
st.set_page_config(
    page_title="广州市黄金假日国际旅行社有限公司",
    page_icon="✈️",
    layout="wide"
)

# --- 2. 品牌视觉 CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #FCF9F2; }
    [data-testid="stSidebar"] { background-color: #1E3A5F !important; }
    [data-testid="stSidebar"] * { color: white !important; }
    h1 { color: #B8860B !important; text-align: center; font-weight: bold; }
    .stButton>button {
        width: 100%; border-radius: 8px; border: 1px solid #D4AF37;
        background-color: #D4AF37; color: white !important; font-weight: bold;
    }
    .material-card {
        background-color: white; padding: 25px; border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1); border-left: 5px solid #D4AF37;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. 50+ 全量数据库
# ==========================================
def get_full_db():
    base = ["护照原件", "白底照片2张", "身份证复印件", "户口本整本复印件", "结婚证复印件"]
    fin = ["近6个月银行流水(余额3万+)", "房产证复印件", "车产证复印件"]
    countries = ["意大利", "日本", "美国", "英国", "法国", "德国", "澳大利亚", "新加坡", "泰国", "马来西亚", "韩国", "加拿大", "俄罗斯", "越南", "新西兰", "瑞士", "荷兰", "西班牙", "希腊", "阿联酋", "土耳其", "菲律宾", "印度", "印尼", "埃及", "瑞典", "奥地利", "葡萄牙", "丹麦", "比利时", "捷克", "匈牙利"]
    db = {c: {"旅游签": {"在职人员": base + fin + ["在职证明(盖章)", "营业执照副本(盖章)"]}} for c in countries}
    return db

VISA_DB = get_full_db()
CURRENCIES = {"CNY":"人民币", "USD":"美元", "EUR":"欧元", "GBP":"英镑", "JPY":"日元", "HKD":"港币", "THB":"泰铢", "AUD":"澳元"}
CITIES = {"北京":"Asia/Shanghai", "伦敦":"Europe/London", "纽约":"America/New_York", "巴黎":"Europe/Paris", "东京":"Asia/Tokyo"}

# ==========================================
# 4. PDF 生成逻辑 (加入图片容错机制)
# ==========================================
def generate_pdf(title, items):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    font_path = os.path.join(base_dir, "simsun.ttf")
    logo_path = os.path.join(base_dir, "image_743d5f.jpg")
    
    # 【核心修复】尝试插入图片，如果报错则跳过
    has_image = False
    if os.path.exists(logo_path):
        try:
            pdf.image(logo_path, x=0, y=0, w=210)
            pdf.set_y(32)
            has_image = True
        except Exception:
            # 如果图片文件识别失败，不抛出异常，只是不画图
            has_image = False

    if not has_image:
        pdf.ln(20) # 没图的话留点空白
    
    # 加载字体
    if os.path.exists(font_path):
        pdf.add_font("SimSun", style="", fname=font_path)
        pdf.set_font("SimSun", size=16)
    else:
        raise FileNotFoundError(f"缺少字体文件: {font_path}")

    # 写入标题
    pdf.cell(w=0, h=10, text=title, ln=True, align='C')
    pdf.ln(5)
    
    # 写入正文
    pdf.set_left_margin(25)
    pdf.set_font("SimSun", size=11)
    for idx, item in enumerate(items, 1):
        pdf.multi_cell(160, 7, text=f"{idx}. {item}", align='L')
        pdf.ln(1.5)
        
    return bytes(pdf.output())

# ==========================================
# 5. 主界面
# ==========================================
st.sidebar.markdown("# 🏆 旅游专家")
menu = st.sidebar.radio("核心导航", ["🛂 签证清单", "💱 汇率换算", "⏰ 时差查询"])

st.title("✈️ 广州市黄金假日国际旅行社有限公司")
st.markdown('<hr style="border: none; height: 3px; background-image: linear-gradient(to right, transparent, #D4AF37, transparent); margin-top: -10px; margin-bottom: 25px;">', unsafe_allow_html=True)

if menu == "签证清单":
    c1, c2, c3 = st.columns(3)
    with c1: country = st.selectbox("📌 选择国家", sorted(list(VISA_DB.keys())))
    with c2: v_type = st.selectbox("🎫 类型", ["旅游签"])
    with c3: identity = st.selectbox("👤 身份", ["在职人员"])

    data = VISA_DB[country][v_type][identity]
    st.markdown('<div class="material-card">', unsafe_allow_html=True)
    for i, item in enumerate(data, 1):
        st.write(f"**{i}.** {item}")
    st.markdown('</div>', unsafe_allow_html=True)

    try:
        pdf_bytes = generate_pdf(f"{country}材料清单", data)
        st.download_button(
            label="📥 一键下载材料清单", 
            data=pdf_bytes, 
            file_name=f"{country}_清单.pdf",
            mime="application/pdf"
        )
    except Exception as e:
        st.error(f"下载失败：{e}")

elif menu == "汇率换算":
    st.header("💱 实时汇率换算")
    try:
        rates = requests.get("https://api.exchangerate-api.com/v4/latest/CNY").json()['rates']
        col1, col2 = st.columns(2)
        with col1: amt = st.number_input("人民币", value=100.0)
        with col2: target = st.selectbox("货币", sorted(list(CURRENCIES.keys())), format_func=lambda x: f"{x}-{CURRENCIES[x]}")
        st.metric("结果", f"{amt * rates.get(target, 0):,.2f} {target}")
    except: st.warning("接口连接中...")

elif menu == "时差查询":
    st.header("⏰ 全球时差查询")
    city = st.selectbox("城市", sorted(list(CITIES.keys())))
    bj = datetime.now(pytz.timezone("Asia/Shanghai"))
    ct = datetime.now(pytz.timezone(CITIES[city]))
    st.metric("🏠 北京时间", bj.strftime('%H:%M'))
    st.metric(f"📍 {city}时间", ct.strftime('%H:%M'))

st.markdown("<br><center>© 2026 广州市黄金假日国际旅行社有限公司</center>", unsafe_allow_html=True)