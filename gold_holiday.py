import streamlit as st
import requests
from datetime import datetime
import pytz
from fpdf import FPDF
import io
import os
import json

# --- 1. 页面基本配置 ---
st.set_page_config(
    page_title="广州市黄金假日国际旅行社有限公司", 
    page_icon="✈️", 
    layout="wide"
)

# --- 2. 响应式美化 CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #FCF9F2; color: #333333; }
    [data-testid="stSidebar"] { background-color: #1E3A5F !important; }
    [data-testid="stSidebar"] * { color: #FFFFFF !important; }
    
    /* 主标题压缩 */
    h1 { 
        color: #B8860B !important; 
        text-align: center; 
        font-weight: bold; 
        font-size: 2.2rem !important; 
        margin-top: -20px !important; 
        margin-bottom: 15px !important; 
    }
    
    /* 下拉选择框间距 */
    .stSelectbox { margin-bottom: 5px !important; }

    /* 材料清单卡片 */
    .material-card {
        background-color: white; 
        padding: 15px 25px !important; 
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.06); 
        border-left: 6px solid #D4AF37; 
        margin-top: 10px !important; 
        margin-bottom: 10px !important;
        line-height: 1.5 !important;
    }
    
    /* 下载按钮样式：确保独立占行，增加间距防止重叠 */
    .stDownloadButton { margin-top: 10px !important; margin-bottom: 15px !important; }
    .stDownloadButton>button {
        width: 100% !important; max-width: 280px; 
        padding: 8px 15px !important;
        height: 42px !important;
        border-radius: 8px; border: 1px solid #D4AF37; 
        background-color: #D4AF37; 
        color: white !important; font-weight: bold;
    }
    
    /* 专家建议文字：增加垂直间距 */
    .expert-tips-text {
        color: #555; 
        font-size: 0.95rem; 
        margin-top: 10px !important; 
        margin-bottom: 10px !important;
        line-height: 1.6;
    }

    /* 客服联系信息区：移除负边距，采用正常边距 */
    .custom-contact-container {
        margin-top: 15px !important;
        padding: 15px 0;
        border-top: 1px dashed #DDD;
        color: #1E3A5F;
        font-weight: bold;
        text-align: center;
        line-height: 1.6;
    }

    /* 汇率换算间距对齐 */
    .swap-btn-container { display: flex; align-items: center; justify-content: center; width: 100%; height: 100%; padding-top: 25px; }
    div[data-testid="column"]:nth-child(3) button { display: block !important; margin: 0 auto !important; }
    [data-testid="stHorizontalBlock"] { gap: 0.5rem !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 数据库读取逻辑 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "local_database.json")

def load_local_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return {}
    return {}

DATABASE = load_local_db()

# 动态提取国家
if DATABASE:
    COUNTRIES_LIST = sorted(list(set([k.split('_')[0] for k in DATABASE.keys()])))
else:
    COUNTRIES_LIST = ["日本", "意大利", "美国", "英国", "法国"]

CURRENCIES = {"CNY":"人民币", "USD":"美元", "EUR":"欧元", "GBP":"英镑", "JPY":"日元", "HKD":"港币", "AUD":"澳元", "THB":"泰铢", "SGD":"新币", "MYR":"林吉特", "KRW":"韩元", "CAD":"加元", "RUB":"卢布", "NZD":"纽币", "CHF":"瑞郎"}
CITIES = {"北京/上海":"Asia/Shanghai", "香港/澳门":"Asia/Hong_Kong", "台北":"Asia/Taipei", "伦敦":"Europe/London", "巴黎":"Europe/Paris", "纽约":"America/New_York", "东京":"Asia/Tokyo"}

# --- 4. 优化后的 PDF 生成函数 (不带文字抬头) ---
def generate_pdf(country, v_type, identity, material_list, expert_tips):
    pdf = FPDF()
    pdf.add_page()
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    font_path = os.path.join(base_dir, "simsun.ttf")
    if os.path.exists(font_path):
        pdf.add_font("SimSun", style="", fname=font_path)
        pdf.set_font("SimSun", size=12)
    else:
        pdf.set_font("Helvetica", size=12)

    # 1. 抬头 Logo
    logo_file = None
    for f in ["image_743d5f.jpg", "image_743d5f.JPG", "logo.jpg"]:
        if os.path.exists(os.path.join(base_dir, f)):
            logo_file = os.path.join(base_dir, f)
            break
    
    if logo_file:
        pdf.image(logo_file, x=10, y=8, w=190)
        pdf.set_y(45) 
    else:
        pdf.set_y(20)

    # 2. 金色分割线
    pdf.set_draw_color(212, 175, 55) 
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(10)

    # 3. 签证信息
    pdf.set_font("SimSun", size=12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(w=0, h=8, text=f"目的地：{country}    签证类型：{v_type}    身份：{identity}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # 4. 材料清单 (带序号)
    pdf.set_fill_color(240, 242, 246)
    pdf.set_font("SimSun", size=13)
    pdf.cell(w=0, h=10, text=" 📋 必备材料清单", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_font("SimSun", size=11)
    for idx, item in enumerate(material_list, 1):
        pdf.multi_cell(w=170, h=8, text=f" {idx}. {item}")
        pdf.ln(1)

    # 5. 专家建议 (带序号)
    if expert_tips:
        pdf.ln(5)
        pdf.set_fill_color(253, 249, 240)
        pdf.cell(w=0, h=10, text=" 💡 专家建议", fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)
        for idx, tip in enumerate(expert_tips, 1):
            pdf.multi_cell(w=170, h=7, text=f" {idx}. {tip}")
            pdf.ln(1)

    # 6. 页脚
    pdf.set_y(-30)
    pdf.set_font("SimSun", size=9)
    pdf.set_text_color(128, 128, 128)
    pdf.cell(w=0, h=5, text="客服联系方式：18924232668（微信同号）", align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.multi_cell(w=0, h=5, text="免责声明：签证政策实时变动，本清单仅供参考。最终办理材料请以领馆当日要求为准。", align='C')

    return bytes(pdf.output())

# --- 5. 交互界面 ---
st.sidebar.markdown("# 🏆 功能中心")
menu = st.sidebar.radio("请选择操作项目：", ["🛂 签证/入境材料查询", "💱 实时汇率换算", "⏰ 全球时差查询"])
st.sidebar.divider()
st.sidebar.caption("© 2026 广州市黄金假日")

st.title("✈️ 广州市黄金假日国际旅行社有限公司")
st.markdown('<hr style="border: none; height: 3px; background-image: linear-gradient(to right, transparent, #D4AF37, transparent); margin-top: -10px; margin-bottom: 20px;">', unsafe_allow_html=True)

if menu == "🛂 签证/入境材料查询":
    c1, c2, c3 = st.columns(3)
    with c1: 
        country = st.selectbox("📌 选择目的地", COUNTRIES_LIST)
        # 💡 在目的地国家下面显示政策提示
        sample_key = next((k for k in DATABASE.keys() if k.startswith(f"{country}_")), None)
        if sample_key:
            policy_txt = DATABASE[sample_key]['content']['status_title']
            st.markdown(f"<p style='color: #D4AF37; font-size: 0.85rem; font-weight: bold; margin-top: -10px;'>{policy_txt}</p>", unsafe_allow_html=True)
            
    with c2: v_type = st.selectbox("🎫 签证类型", ["旅游签", "商务签", "探亲签"])
    with c3: identity = st.selectbox("👤 申请人身份", ["在职人员", "退休人员", "在校学生", "自由职业者", "学龄前儿童"])

    search_key = f"{country}_{v_type}_{identity}"
    record = DATABASE.get(search_key)

    if record:
        content = record['content']
        st.markdown(f"### {country} ({v_type}) 材料清单")
        
        # 1. 网页版材料展示 (带序号)
        items_html = "".join([f'<div style="margin-bottom:8px;">{i}. {m}</div>' for i, m in enumerate(content['material_list'], 1)])
        st.markdown(f'<div class="material-card">{items_html}</div>', unsafe_allow_html=True)
        
        # 2. 网页版专家建议 (带序号) - 独立占行
        if content.get('expert_tips'):
            tips_text = "<br>".join([f"{i}. {tip}" for i, tip in enumerate(content['expert_tips'], 1)])
            st.markdown(f"<div class='expert-tips-text'><b>💡 专家建议：</b><br>{tips_text}</div>", unsafe_allow_html=True)

        # 3. 下载按钮 - 独立占行
        pdf_data = generate_pdf(country, v_type, identity, content['material_list'], content.get('expert_tips', []))
        st.download_button(label="📥 下载 PDF 材料清单", data=pdf_data, file_name=f"{country}_{identity}_材料清单.pdf", mime="application/pdf")

        # 4. 客服联系信息
        st.markdown("""
            <div class="custom-contact-container">
                详情请联系客服获取专属材料包<br>
                客服联系方式：18924232668（微信同号）
            </div>
        """, unsafe_allow_html=True)
    else:
        st.warning(f"⚠️ 暂无 {country} ({v_type}) 的本地记录。")

elif menu == "💱 实时汇率换算":
    st.header("💱 实时汇率换算")
    if 'base_curr' not in st.session_state: st.session_state.base_curr = 'CNY'
    if 'target_curr' not in st.session_state: st.session_state.target_curr = 'USD'
    def swap_c(): st.session_state.base_curr, st.session_state.target_curr = st.session_state.target_curr, st.session_state.base_curr
    
    c1, c2, c3, c4 = st.columns([2.5, 4.2, 0.6, 4.2], gap="small")
    with c1: amt = st.number_input("金额", value=100.0)
    with c2: base = st.selectbox("持有", sorted(list(CURRENCIES.keys())), key="base_curr", format_func=lambda x: f"{x}-{CURRENCIES[x]}")
    with c3:
        st.markdown('<div class="swap-btn-container">', unsafe_allow_html=True)
        st.button("🔄", on_click=swap_c, key="swap_exchange")
        st.markdown('</div>', unsafe_allow_html=True)
    with c4: target = st.selectbox("目标", sorted(list(CURRENCIES.keys())), key="target_curr", format_func=lambda x: f"{x}-{CURRENCIES[x]}")
    
    try:
        r_data = requests.get(f"https://api.exchangerate-api.com/v4/latest/{base}").json()
        rate = r_data['rates'][target]
        st.markdown(f"""<div style="padding:20px; background:white; border-left:6px solid #D4AF37; border-radius:10px; box-shadow:0 4px 10px rgba(0,0,0,0.05); margin-top:15px;">
        <p style="color:#666; margin:0;">换算结果</p>
        <h2 style="color:#D4AF37; margin:0;">{amt*rate:,.2f} {target}</h2></div>""", unsafe_allow_html=True)
    except: st.error("汇率接口获取失败")

elif menu == "⏰ 全球时差查询":
    st.header("⏰ 全球主要城市时间")
    city = st.selectbox("选择城市", sorted(list(CITIES.keys())))
    bj_tz = pytz.timezone("Asia/Shanghai")
    target_tz = pytz.timezone(CITIES[city])
    bj_time = datetime.now(bj_tz)
    target_time = datetime.now(target_tz)
    
    tc1, tc2 = st.columns(2)
    with tc1: st.metric("🏠 北京时间", bj_time.strftime('%H:%M'), bj_time.strftime('%m-%d'))
    with tc2: st.metric(f"📍 {city} 时间", target_time.strftime('%H:%M'), target_time.strftime('%m-%d'))

st.markdown("<br><br><center>© 2026 广州市黄金假日国际旅行社有限公司</center>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; font-size:0.8rem; color:#888;'>免责声明： ⚠️ 签证政策实时变动，本清单仅供参考。最终办理材料请以领馆当日要求为准。</p>", unsafe_allow_html=True)