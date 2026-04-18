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
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. 核心全量数据库 (2026 全球 50 国深度核实版)
# ==========================================
def get_verified_db(country, v_type, identity):
    # --- 国家分类定义 ---
    # A类：互免签证 (无需任何材料)
    visa_free = ["新加坡", "马来西亚", "泰国", "阿联酋", "卡塔尔", "哈萨克斯坦", "马尔代夫", "斐济", "塞舌尔", "毛里求斯", "阿尔巴尼亚"]
    
    # B类：超轻量 ETA/电子签 (无需照片、无需在职、无需户口本、无需行程)
    # 澳洲现为全数字化申请，无需物理照片；斯里兰卡ETA/土耳其电子签仅需护照信息。
    visa_ultra_light = ["斯里兰卡", "土耳其", "澳大利亚", "新西兰"]
    
    # C类：标准电子签 (需护照+照片，无需在职证明和资产)
    # 越南、俄罗斯、印尼、埃及、柬埔寨等均已实现极简电子化。
    visa_evisa_standard = ["越南", "俄罗斯", "印尼", "埃及", "柬埔寨", "缅甸", "老挝", "文莱", "沙特", "尼泊尔"]
    
    # D类：申根区 (高门槛：强制保险+指纹+全套资产)
    schengen = ["意大利", "法国", "德国", "瑞士", "荷兰", "西班牙", "希腊", "瑞典", "奥地利", "葡萄牙", "丹麦", "比利时", "捷克", "匈牙利", "冰岛", "芬兰", "波兰"]

    base_p = "护照原件/高清扫描件 (有效期6个月以上)"

    # --- 逻辑精准分流 ---
    if country in visa_free:
        policy, desc = "FREE", "🌟 互免签证 (直飞入境)"
        docs = [base_p, "目的地国家电子入境卡 (请在出发前1-3天内完成申报)", "往返机票行程单 (英文版打印备用)", "全程酒店预订单 (英文版打印备查)"]

    elif country in visa_ultra_light:
        policy, desc = "ETA", f"📝 {country} 电子授权/签证 (材料极简，无需照片/在职/户口本)"
        if country == "斯里兰卡":
            docs = [base_p, "【免材料】仅需护照信息在线申请 ETA，无需照片、无需行程、无需酒店、无需在职证明"]
        elif country == "澳大利亚":
            docs = [base_p, "【无纸化】仅需护照高清扫描件，无需纸质照片，建议提供基础资产扫描件(无需原件)", "个人基本信息表 (电子版)"]
        else: # 土耳其/新西兰
            docs = [base_p, f"【极简办理】仅需护照信息，无需提供照片及任何工作证明材料"]

    elif country in visa_evisa_standard:
        policy, desc = "E-VISA", f"🌍 {country} 电子签 (仅需照片，无需在职/户口本证明)"
        docs = [base_p, "电子版白底照片 (35x45mm)", "往返机票行程单 (英文版)"]
        if country == "越南":
            docs.append("【注】越南电子签仅需护照首页+照片，无需资产证明、无需在职证明。")

    else:
        # 传统签证区 (美、加、英、日、韩、申根、南非、南美等)
        policy, desc = "STICKER", "🛂 传统签证 (需提交完整资产、在职及身份证明材料)"
        
        # 照片精度控制
        if country == "日本": photo = "纸质照片2张 (45x45mm 正方形，白底)"
        elif country == "美国": photo = "纸质照片2张 (51x51mm 正方形，不戴眼镜)"
        else: photo = "纸质照片2张 (35x45mm，白底彩照)"
        
        docs = [base_p, photo, "身份证及户口本整本复印件", "个人信息申请表"]
        
        # 申根保险强校验
        if country in schengen:
            docs.append("【强提示】境外医疗保险原件 (保额需达30万人民币/3万欧元以上)")
            docs.append("【指纹录入】需本人亲自前往签证中心录入生物识别信息")

        # 身份细节追加
        if identity == "在职人员":
            docs += ["在职证明原件 (公司红头信笺打印，加盖公章)", "营业执照副本复印件 (加盖公章)", "个人近6个月银行流水 (余额建议5万以上)"]
        elif identity == "退休人员":
            docs += ["退休证复印件", "养老金账户近6个月流水账单"]
        elif identity == "在校学生":
            docs += ["在校证明原件", "出生医学证明复印件", "父母资产及委托证明"]
        elif identity == "自由职业者":
            docs += ["个人收入来源说明信", "近6个月活跃银行流水明细"]
        elif identity == "学龄前儿童":
            docs += ["出生医学证明复印件", "父母结婚证", "【重要】公证书及领事认证 (如非父母双方陪同)"]

        docs += ["全程机票/酒店预订单", "详细旅游行程表"]

    return desc, docs, policy

# 国家及主流配置
COUNTRIES_LIST = ["意大利", "日本", "美国", "英国", "法国", "德国", "澳大利亚", "新加坡", "泰国", "马来西亚", "韩国", "加拿大", "越南", "新西兰", "瑞士", "荷兰", "西班牙", "希腊", "阿联酋", "土耳其", "俄罗斯", "菲律宾", "印度", "印尼", "埃及", "南非", "瑞典", "奥地利", "葡萄牙", "丹麦", "比利时", "捷克", "匈牙利", "冰岛", "芬兰", "波兰", "爱尔兰", "以色列", "柬埔寨", "缅甸", "老挝", "文莱", "沙特", "卡塔尔", "尼泊尔", "斯里兰卡", "巴西", "阿根廷", "墨西哥", "智利"]
CURRENCIES = {"CNY":"人民币", "USD":"美元", "EUR":"欧元", "GBP":"英镑", "JPY":"日元", "HKD":"港币", "AUD":"澳元", "THB":"泰铢", "SGD":"新币", "MYR":"林吉特", "KRW":"韩元", "CAD":"加元", "RUB":"卢布", "NZD":"纽币", "CHF":"瑞郎", "AED":"迪拉姆", "SAR":"沙特里亚尔", "INR":"印度卢比", "IDR":"印尼盾", "PHP":"菲律宾比索", "VND":"越南盾", "EGP":"埃及镑", "ZAR":"南非兰特", "SEK":"瑞典克朗", "TRY":"土耳其里拉", "BRL":"巴西雷亚尔", "MXN":"墨西哥比索", "TWD":"新台币", "MOP":"澳门币"}
CITIES = {"北京/上海":"Asia/Shanghai", "香港/澳门":"Asia/Hong_Kong", "台北":"Asia/Taipei", "东京":"Asia/Tokyo", "首尔":"Asia/Seoul", "新加坡":"Asia/Singapore", "曼谷":"Asia/Bangkok", "吉隆坡":"Asia/Kuala_Lumpur", "迪拜":"Asia/Dubai", "伦敦":"Europe/London", "巴黎":"Europe/Paris", "柏林":"Europe/Berlin", "罗马":"Europe/Rome", "马德里":"Europe/Madrid", "莫斯科":"Europe/Moscow", "苏黎世":"Europe/Zurich", "纽约":"America/New_York", "洛杉矶":"America/Los_Angeles", "多伦多":"America/Toronto", "温哥华":"America/Vancouver", "悉尼":"Australia/Sydney", "墨尔本":"Australia/Melbourne", "奥克兰":"Pacific/Auckland", "新德里":"Asia/Kolkata", "伊斯坦布尔":"Europe/Istanbul", "开罗":"Africa/Cairo", "约翰内斯堡":"Africa/Johannesburg", "雅典":"Europe/Athens", "阿姆斯特丹":"Europe/Amsterdam", "芝加哥":"America/Chicago"}

# ==========================================
# 4. PDF 生成
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
# 5. 交互界面
# ==========================================
st.sidebar.markdown("# 🏆 功能中心")
menu = st.sidebar.radio("请选择操作项目：", ["🛂 签证/入境材料查询", "💱 实时汇率换算", "⏰ 全球时差查询"])
st.sidebar.divider()
st.sidebar.caption("© 2026 广州市黄金假日")

st.title("✈️ 广州市黄金假日国际旅行社有限公司")
st.markdown('<hr style="border: none; height: 3px; background-image: linear-gradient(to right, transparent, #D4AF37, transparent); margin-top: -10px; margin-bottom: 30px;">', unsafe_allow_html=True)

if menu == "🛂 签证/入境材料查询":
    c1, c2, c3 = st.columns(3)
    with c1: country = st.selectbox("📌 选择目的地", sorted(COUNTRIES_LIST))
    with c2: v_type = st.selectbox("🎫 签证类型", ["旅游签", "商务签", "探亲签"])
    with c3: identity = st.selectbox("👤 申请人身份", ["在职人员", "退休人员", "在校学生", "自由职业者", "学龄前儿童"])

    desc, data, policy = get_verified_db(country, v_type, identity)
    
    color_map = {"FREE":"#D4EDDA", "ETA":"#E2F0FB", "E-VISA":"#FFF3CD", "STICKER":"#F8D7DA"}
    txt_map = {"FREE":"#155724", "ETA":"#004085", "E-VISA":"#856404", "STICKER":"#721C24"}
    st.markdown(f'<div class="policy-tag" style="background-color:{color_map[policy]}; color:{txt_map[policy]};">{desc}</div>', unsafe_allow_html=True)

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

    pdf_data = generate_pdf(f"{country}{v_type}材料清单", data)
    st.download_button(label="📥 一键下载材料清单", data=pdf_data, file_name=f"{country}_{identity}_材料清单.pdf", mime="application/pdf")

elif menu == "💱 实时汇率换算":
    st.header("💱 全球主流货币换算")
    if 'base_curr' not in st.session_state: st.session_state.base_curr = 'CNY'
    if 'target_curr' not in st.session_state: st.session_state.target_curr = 'USD'
    def swap_c(): st.session_state.base_curr, st.session_state.target_curr = st.session_state.target_curr, st.session_state.base_curr
    c1, c2, c3, c4 = st.columns([2.5, 3.5, 1, 3.5])
    with c1: amt = st.number_input("金额", value=100.0, min_value=0.0)
    with c2: base = st.selectbox("持有", sorted(list(CURRENCIES.keys())), key="base_curr", format_func=lambda x: f"{x}-{CURRENCIES[x]}")
    with c3: st.markdown("<br>", unsafe_allow_html=True); st.button("🔄", on_click=swap_c)
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