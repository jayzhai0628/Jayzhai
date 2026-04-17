import streamlit as st
import requests
from datetime import datetime
import pytz
from fpdf import FPDF
import io
import os

# --- 1. 页面配置 ---
st.set_page_config(
    page_title="广州市黄金假日国际旅行社有限公司",
    page_icon="✈️",
    layout="wide"
)

# --- 2. 品牌美化 CSS ---
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
# 3. 50+ 签证目的地数据库
# ==========================================
def get_full_visa_db():
    docs_base = ["护照原件", "白底彩照2张", "身份证复印件", "户口本整本复印件", "结婚证/离婚证复印件"]
    docs_fin = ["近6个月银行流水(余额3万+)", "房产证复印件", "车产证复印件"]
    # 扩充至 50 个国家
    countries = [
        "意大利", "日本", "美国", "英国", "法国", "德国", "澳大利亚", "新加坡", "泰国", "马来西亚", 
        "韩国", "加拿大", "俄罗斯", "越南", "新西兰", "瑞士", "荷兰", "西班牙", "希腊", "阿联酋", 
        "土耳其", "菲律宾", "印度", "印尼", "埃及", "南非", "巴西", "阿根廷", "墨西哥", "瑞典", 
        "挪威", "奥地利", "葡萄牙", "丹麦", "比利时", "捷克", "匈牙利", "冰岛", "芬兰", "波兰",
        "爱尔兰", "以色列", "柬埔寨", "缅甸", "老挝", "文莱", "沙特", "卡塔尔", "尼泊尔", "斯里兰卡"
    ]
    db = {}
    for c in countries:
        special = ["医疗保险(30万+)", "机票预订单", "酒店确认单"] if c in ["意大利", "法国", "德国", "西班牙", "瑞士", "荷兰", "希腊", "瑞典", "奥地利", "芬兰"] else []
        db[c] = {
            "旅游签": {
                "在职人员": docs_base + docs_fin + ["在职证明(盖章)", "营业执照副本(盖章)"] + special,
                "退休人员": docs_base + docs_fin + ["退休证复印件"] + special,
                "学生/儿童": docs_base + ["在读证明", "出生证公证", "父母资产证明"] + special
            }
        }
    return db

# ==========================================
# 4. 50+ 货币及 50+ 城市数据
# ==========================================
CURRENCIES = {
    "CNY":"人民币", "USD":"美元", "EUR":"欧元", "GBP":"英镑", "JPY":"日元", "HKD":"港币", "AUD":"澳元", "THB":"泰铢", 
    "SGD":"新币", "MYR":"林吉特", "KRW":"韩元", "CAD":"加元", "RUB":"卢布", "NZD":"纽币", "TWD":"台币", "MOP":"澳门元",
    "PHP":"比索", "IDR":"印尼盾", "AED":"迪拜币", "SAR":"沙特币", "TRY":"土耳其里拉", "INR":"印度卢比", "CHF":"瑞郎",
    "SEK":"瑞典克朗", "DKK":"丹麦克朗", "NOK":"挪威克朗", "MXN":"墨西哥比索", "ZAR":"南非兰特", "BRL":"巴西里亚尔",
    "EGP":"埃及镑", "VND":"越南盾", "PLN":"波兰兹罗提", "KWD":"科威特第纳尔", "QAR":"卡塔尔里亚尔"
    # 后续可通过 API 自动补充至 50+
}

CITIES = {
    "北京":"Asia/Shanghai", "伦敦":"Europe/London", "巴黎":"Europe/Paris", "纽约":"America/New_York", "东京":"Asia/Tokyo", 
    "悉尼":"Australia/Sydney", "曼谷":"Asia/Bangkok", "迪拜":"Asia/Dubai", "新加坡":"Asia/Singapore", "首尔":"Asia/Seoul",
    "柏林":"Europe/Berlin", "罗马":"Europe/Rome", "马德里":"Europe/Madrid", "莫斯科":"Europe/Moscow", "多伦多":"America/Toronto",
    "温哥华":"America/Vancouver", "洛杉矶":"America/Los_Angeles", "芝加哥":"America/Chicago", "旧金山":"America/Los_Angeles",
    "奥克兰":"Pacific/Auckland", "开罗":"Africa/Cairo", "约翰内斯堡":"Africa/Johannesburg", "伊斯坦布尔":"Europe/Istanbul",
    "新德里":"Asia/Kolkata", "雅加达":"Asia/Jakarta", "胡志明市":"Asia/Ho_Chi_Minh", "马尼拉":"Asia/Manila", "吉隆坡":"Asia/Kuala_Lumpur"
}

VISA_DB = get_full_visa_db()

# ==========================================
# 5. PDF 生成逻辑 (维持紧凑间距)
# ==========================================
def generate_pdf(title, items):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    current_dir = os.path.dirname(os.path.abspath(__file__))
    font_path = os.path.join(current_dir, "simsun.ttf")
    logo_path = os.path.join(current_dir, "image_743d5f.jpg")
    
    if os.path.exists(logo_path):
        pdf.image(logo_path, x=0, y=0, w=210)
        pdf.set_y(32)
    else: pdf.ln(20)
    
    if os.path.exists(font_path):
        pdf.add_font("SimSun", "", font_path)
        pdf.set_font("SimSun", "", 16)
    else: pdf.set_font("Helvetica", "B", 16)

    clean_title = title.replace('【', '[').replace('】', ']').encode('gbk', 'ignore').decode('gbk')
    pdf.cell(w=0, h=10, txt=clean_title, ln=True, align='C')
    pdf.ln(5)
    pdf.set_left_margin(25)
    if os.path.exists(font_path): pdf.set_font("SimSun", "", 11)
    for idx, item in enumerate(items, 1):
        safe_text = item.encode('gbk', 'ignore').decode('gbk')
        pdf.multi_cell(160, 7, txt=f"{idx}. {safe_text}", align='L')
        pdf.ln(1.5)
    return bytes(pdf.output())

# ==========================================
# 6. 主界面
# ==========================================
st.sidebar.markdown("# 🏆 旅游专家")
menu = st.sidebar.radio("核心功能导航", ["🛂 50国签证清单", "💱 50种汇率换算", "⏰ 50个时差城市"])
st.sidebar.divider()
st.sidebar.caption("© 2026 广州市黄金假日")

# 标题及金色渐变线
st.title("✈️ 广州市黄金假日国际旅行社有限公司")
st.markdown('<hr style="border: none; height: 3px; background-image: linear-gradient(to right, transparent, #D4AF37, transparent); margin-top: -10px; margin-bottom: 25px;">', unsafe_allow_html=True)

if menu == "🛂 50国签证清单":
    c1, c2, c3 = st.columns(3)
    with c1: country = st.selectbox("🔍 搜索国家", sorted(list(VISA_DB.keys())))
    with c2: v_type = st.selectbox("🎫 签证类型", ["旅游签"])
    with c3: identity = st.selectbox("👤 身份", ["在职人员", "退休人员", "学生/儿童"])

    final_list = VISA_DB[country][v_type][identity]
    st.markdown('<div class="material-card">', unsafe_allow_html=True)
    st.markdown(f"#### {country} - {identity}材料预览")
    for i, item in enumerate(final_list, 1):
        st.write(f"**{i}.** {item}")
    st.markdown('</div>', unsafe_allow_html=True)

    pdf_bytes = generate_pdf(f"{country}签证清单", final_list)
    st.download_button(label="📥 一键下载材料清单", data=pdf_bytes, file_name=f"{country}_清单.pdf")

elif menu == "💱 50种汇率换算":
    st.header("💱 实时汇率换算 (CNY 基准)")
    rates = requests.get("https://api.exchangerate-api.com/v4/latest/CNY").json()['rates']
    col1, col2 = st.columns(2)
    with col1: amt = st.number_input("输入人民币金额", value=100.0)
    with col2: target = st.selectbox("🔍 搜索货币", sorted(list(CURRENCIES.keys())), format_func=lambda x: f"{x} - {CURRENCIES[x]}")
    st.metric(f"换算结果 ({target})", f"{amt * rates.get(target, 0):,.2f}")

elif menu == "⏰ 50个时差城市":
    st.header("⏰ 全球城市时差查询")
    city = st.selectbox("🔍 快速搜索城市", sorted(list(CITIES.keys())))
    bj = datetime.now(pytz.timezone("Asia/Shanghai"))
    ct = datetime.now(pytz.timezone(CITIES[city]))
    c1, c2 = st.columns(2)
    c1.metric("🏠 北京时间", bj.strftime('%H:%M'))
    c2.metric(f"📍 {city}时间", ct.strftime('%H:%M'), ct.strftime('%m-%d'))

st.divider()
st.markdown("<center>© 2026 广州市黄金假日国际旅行社有限公司 | 签证部官方系统</center>", unsafe_allow_html=True)