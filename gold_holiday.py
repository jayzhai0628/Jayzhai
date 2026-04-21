import streamlit as st
import requests
from datetime import datetime
import pytz
from fpdf import FPDF
import io
import os
import json  # 💡 新增：导入处理 JSON 的库

# --- 1. 页面配置 ---
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
    h1 { color: #B8860B !important; text-align: center; font-weight: bold; font-size: calc(1.5rem + 1vw) !important; }
    .stDownloadButton>button {
        width: 100% !important; max-width: 300px; padding: 10px 20px !important;
        border-radius: 8px; border: 1px solid #D4AF37; background-color: #D4AF37; 
        color: white !important; font-weight: bold; display: block; margin: 20px 0;
    }
    .material-card {
        background-color: white; padding: 25px; border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08); border-left: 6px solid #D4AF37; 
        margin-top: 15px; color: #333333 !important; position: relative; overflow: hidden;
    }
    .policy-tag {
        padding: 8px 15px; border-radius: 10px; font-size: 14px; font-weight: bold; 
        margin-bottom: 15px; display: inline-block; line-height: 1.4;
    }
    .stMarkdown p, .stMarkdown li { color: #333333 !important; }
    
    /* 汇率换算按钮对齐微调 */
    .swap-btn-container {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        height: 100%;
        padding-top: 28px;
    }
    div[data-testid="column"]:nth-child(3) button {
        display: block !important;
        margin: 0 auto !important;
    }
    [data-testid="stHorizontalBlock"] {
        gap: 0.5rem !important;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. 💡 新增：数据库读取逻辑 💡
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "local_database.json")

def load_local_db():
    """从 local_database.json 加载全量数据"""
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            st.error(f"数据库解析失败: {e}")
            return {}
    return {}

# 预加载数据
DATABASE = load_local_db()

# 获取所有可查询的国家列表
if DATABASE:
    # 从 JSON 的 Key 中提取国家名称 (例如 "日本_旅游签_在职人员" 提取出 "日本")
    COUNTRIES_LIST = sorted(list(set([k.split('_')[0] for k in DATABASE.keys()])))
else:
    # 备用列表
    COUNTRIES_LIST = ["意大利", "日本", "美国", "英国", "法国", "德国", "澳大利亚", "新加坡", "泰国", "马来西亚"]

# ==========================================
# 4. 常量定义 (汇率与时差保持不变)
# ==========================================
CURRENCIES = {"CNY":"人民币", "USD":"美元", "EUR":"欧元", "GBP":"英镑", "JPY":"日元", "HKD":"港币", "AUD":"澳元", "THB":"泰铢", "SGD":"新币", "MYR":"林吉特", "KRW":"韩元", "CAD":"加元", "RUB":"卢布", "NZD":"纽币", "CHF":"瑞郎", "AED":"迪拉姆", "SAR":"沙特里亚尔", "INR":"印度卢比", "IDR":"印尼盾", "PHP":"菲律宾比索", "VND":"越南盾", "EGP":"埃及镑", "ZAR":"南非兰特", "SEK":"瑞典克朗", "TRY":"土耳其里拉", "BRL":"巴西雷亚尔", "MXN":"墨西哥比索", "TWD":"新台币", "MOP":"澳门币"}
CITIES = {"北京/上海":"Asia/Shanghai", "香港/澳门":"Asia/Hong_Kong", "台北":"Asia/Taipei", "东京":"Asia/Tokyo", "首尔":"Asia/Seoul", "新加坡":"Asia/Singapore", "曼谷":"Asia/Bangkok", "吉隆坡":"Asia/Kuala_Lumpur", "迪拜":"Asia/Dubai", "伦敦":"Europe/London", "巴黎":"Europe/Paris", "柏林":"Europe/Berlin", "罗马":"Europe/Rome", "马德里":"Europe/Madrid", "莫斯科":"Europe/Moscow", "苏黎世":"Europe/Zurich", "纽约":"America/New_York", "洛杉矶":"America/Los_Angeles", "多伦多":"America/Toronto", "温哥华":"America/Vancouver", "悉尼":"Australia/Sydney", "墨尔本":"Australia/Melbourne", "奥克兰":"Pacific/Auckland", "新德里":"Asia/Kolkata", "伊斯坦布尔":"Europe/Istanbul", "开罗":"Africa/Cairo", "约翰内斯堡":"Africa/Johannesburg", "雅典":"Europe/Athens", "阿姆斯特丹":"Europe/Amsterdam", "芝加哥":"America/Chicago"}

# ==========================================
# 5. PDF 生成逻辑 (适配新 JSON 结构)
# ==========================================
def generate_pdf(title_text, items):
    pdf = FPDF()
    pdf.add_page()
    base_dir = os.path.dirname(os.path.abspath(__file__))
    font_path = os.path.join(base_dir, "simsun.ttf")
    
    logo_path = None
    for name in ["image_743d5f.jpg", "image_743d5f.JPG", "logo.jpg"]:
        if os.path.exists(os.path.join(base_dir, name)):
            logo_path = os.path.join(base_dir, name)
            break
    
    if logo_path:
        try: pdf.image(logo_path, x=0, y=0, w=210); pdf.set_y(38)
        except: pdf.set_y(15)
    else: pdf.set_y(15)

    if os.path.exists(font_path):
        pdf.add_font("SimSun", style="", fname=font_path)
        pdf.set_font("SimSun", size=18)
    else: pdf.set_font("Helvetica", size=18)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("SimSun", size=14)
    pdf.cell(w=0, h=10, text=title_text, align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    pdf.set_font("SimSun", size=11)
    pdf.set_left_margin(25)
    for idx, item in enumerate(items, 1):
        pdf.multi_cell(w=160, h=8, text=f"{idx}. {item}")
        pdf.ln(1)
    return bytes(pdf.output())

# ==========================================
# 6. 交互界面
# ==========================================
st.sidebar.markdown("# 🏆 功能中心")
menu = st.sidebar.radio("请选择操作项目：", ["🛂 签证/入境材料查询", "💱 实时汇率换算", "⏰ 全球时差查询"])
st.sidebar.divider()
st.sidebar.caption("© 2026 广州市黄金假日")

st.title("✈️ 广州市黄金假日国际旅行社有限公司")
st.markdown('<hr style="border: none; height: 3px; background-image: linear-gradient(to right, transparent, #D4AF37, transparent); margin-top: -10px; margin-bottom: 30px;">', unsafe_allow_html=True)

if menu == "🛂 签证/入境材料查询":
    c1, c2, c3 = st.columns(3)
    with c1: country = st.selectbox("📌 选择目的地", COUNTRIES_LIST)
    with c2: v_type = st.selectbox("🎫 签证类型", ["旅游签", "商务签", "探亲签"])
    with c3: identity = st.selectbox("👤 申请人身份", ["在职人员", "退休人员", "在校学生", "自由职业者", "学龄前儿童"])

    # 💡 逻辑修改：从加载的 DATABASE 中获取数据
    search_key = f"{country}_{v_type}_{identity}"
    record = DATABASE.get(search_key)

    if record:
        content = record['content']
        data = content['material_list']
        desc = content['status_title']
        policy = content['cat']
        
        # 标签颜色匹配
        color_map = {"FREE":"#D4EDDA", "EVISA":"#FFF3CD", "STICKER":"#F8D7DA"}
        txt_map = {"FREE":"#155724", "EVISA":"#856404", "STICKER":"#721C24"}
        st.markdown(f'<div class="policy-tag" style="background-color:{color_map.get(policy, "#E2F0FB")}; color:{txt_map.get(policy, "#004085")};">{desc}</div>', unsafe_allow_html=True)

        st.markdown(f"### {country} ({v_type}) 材料清单")
        
        items_html = ""
        for i, item in enumerate(data, 1):
            items_html += f"""<div style="display: flex; margin-bottom: 12px; align-items: flex-start;">
    <div style="background-color: #D4AF37; color: white; border-radius: 50%; width: 22px; height: 22px; display: flex; justify-content: center; align-items: center; font-size: 11px; font-weight: bold; margin-right: 12px; flex-shrink: 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">{i}</div>
    <div style="color: #333; line-height: 1.5; font-size: 14px;">{item}</div>
    </div>"""
            
        card_html = f"""<div class="material-card">
    <div style="position: absolute; top: -15px; right: -15px; font-size: 80px; opacity: 0.05; transform: rotate(15deg); pointer-events: none;">✈️</div>
    {items_html}
    </div>"""
        st.markdown(card_html, unsafe_allow_html=True)
        
        # 专家建议展示
        if content.get('expert_tips'):
            st.info("\n".join([f"💡 {tip}" for tip in content['expert_tips']]))

        pdf_data = generate_pdf(f"{country}{v_type}材料清单", data)
        st.download_button(label="📥 一键下载材料清单", data=pdf_data, file_name=f"{country}_{identity}_材料清单.pdf", mime="application/pdf")

    else:
        st.warning(f"⚠️ 暂无 {country} ({v_type}) 针对 {identity} 的本地记录。")

    # 底部固定内容
    st.info("详情请联系客服获取专属材料包\n\n客服联系方式：18924232668（微信同号）")

elif menu == "💱 实时汇率换算":
    st.header("💱 全球主流货币换算")
    if 'base_curr' not in st.session_state: st.session_state.base_curr = 'CNY'
    if 'target_curr' not in st.session_state: st.session_state.target_curr = 'USD'
    def swap_c(): st.session_state.base_curr, st.session_state.target_curr = st.session_state.target_curr, st.session_state.base_curr
    
    c1, c2, c3, c4 = st.columns([2.5, 4.2, 0.6, 4.2], gap="small")
    with c1: amt = st.number_input("金额", value=100.0, min_value=0.0)
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
    except: st.warning("数据接口连接中...")

elif menu == "⏰ 全球时差查询":
    st.header("⏰ 全球主要城市时间")
    city = st.selectbox("搜索城市", sorted(list(CITIES.keys())))
    bj = datetime.now(pytz.timezone("Asia/Shanghai"))
    ct = datetime.now(pytz.timezone(CITIES[city]))
    tc1, tc2 = st.columns(2)
    with tc1: st.metric("🏠 北京时间", bj.strftime('%H:%M'))
    with tc2: st.metric(f"📍 {city} 时间", ct.strftime('%H:%M'), ct.strftime('%m-%d'))

st.markdown("<br><br><center>© 2026 广州市黄金假日国际旅行社有限公司</center>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; font-size:0.8rem; color:#888;'>免责声明： ⚠️ 签证政策实时变动，本清单仅供参考。最终办理材料请以领馆当日要求为准。</p>", unsafe_allow_html=True)