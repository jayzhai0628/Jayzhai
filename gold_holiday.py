import streamlit as st
import requests
from datetime import datetime
import pytz
from fpdf import FPDF
import io
import os

# --- 1. 页面配置 ---
st.set_page_config(page_title="广州市黄金假日国际旅行社有限公司", page_icon="✈️", layout="wide")

# --- 2. 品牌视觉 CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #FCF9F2; }
    [data-testid="stSidebar"] { background-color: #1E3A5F !important; }
    [data-testid="stSidebar"] * { color: white !important; }
    h1 { color: #B8860B !important; text-align: center; font-weight: bold; }
    
    /* 下载按钮样式：左对齐以对齐上方卡片序号 */
    .stDownloadButton>button {
        width: auto !important; padding-left: 25px !important; padding-right: 25px !important;
        border-radius: 8px; border: 1px solid #D4AF37; background-color: #D4AF37; 
        color: white !important; font-weight: bold; margin-left: 5px;
    }
    
    .material-card {
        background-color: white; padding: 25px; border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1); border-left: 5px solid #D4AF37; margin-top: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. 核心全量数据库
# ==========================================
def get_massive_db():
    base = ["护照原件", "白底彩照2张", "身份证复印件", "户口本整本复印件"]
    id_docs = {
        "在职人员": ["在职证明(加盖公章)", "营业执照副本复印件(盖章)", "近6个月银行流水"],
        "退休人员": ["退休证复印件", "养老金流水单/近6个月银行流水"],
        "在校学生": ["在校证明(学校盖章)", "学生证复印件", "出生证复印件", "父母资产证明"],
        "学龄前儿童": ["出生证复印件", "父母结婚证复印件", "出资证明书"],
        "自由职业者": ["近6个月大额银行流水", "存款证明(5万以上)", "收入来源说明书"]
    }
    type_extra = {
        "旅游签": ["全程酒店预订单", "往返机票行程单", "旅游行程计划表"],
        "商务签": ["外方邀请函(扫描/正本)", "中方派遣函(公司盖章)", "外方公司执照"],
        "探亲签": ["亲属关系公证书", "邀请人护照及签证页", "邀请信(签名)"]
    }
    # 50个目的地国家
    countries = [
        "意大利", "日本", "美国", "英国", "法国", "德国", "澳大利亚", "新加坡", "泰国", "马来西亚", 
        "韩国", "加拿大", "越南", "新西兰", "瑞士", "荷兰", "西班牙", "希腊", "阿联酋", "土耳其",
        "俄罗斯", "菲律宾", "印度", "印尼", "埃及", "南非", "瑞典", "奥地利", "葡萄牙", "丹麦",
        "比利时", "捷克", "匈牙利", "冰岛", "芬兰", "波兰", "爱尔兰", "以色列", "柬埔寨", "缅甸",
        "老挝", "文莱", "沙特", "卡塔尔", "尼泊尔", "斯里兰卡", "巴西", "阿根廷", "墨西哥", "智利"
    ]
    db = {}
    for c in countries:
        db[c] = {}
        for t in type_extra.keys():
            db[c][t] = {}
            for ident, docs in id_docs.items():
                db[c][t][ident] = base + docs + type_extra[t]
    return db

VISA_DB = get_massive_db()

# 50种货币
CURRENCIES = {
    "CNY":"人民币", "USD":"美元", "EUR":"欧元", "GBP":"英镑", "JPY":"日元", "HKD":"港币", "AUD":"澳元", "THB":"泰铢", "SGD":"新币", "MYR":"林吉特",
    "KRW":"韩元", "CAD":"加元", "RUB":"卢布", "NZD":"纽币", "CHF":"瑞郎", "AED":"迪拉姆", "SAR":"里亚尔", "INR":"卢比", "IDR":"印尼盾", "PHP":"比索",
    "VND":"越南盾", "EGP":"埃及镑", "ZAR":"兰特", "SEK":"克朗", "NOK":"挪威克朗", "DKK":"丹麦克朗", "PLN":"兹罗提", "ILS":"谢克尔", "BRL":"雷亚尔", "MXN":"墨西哥比索",
    "TRY":"土耳其里拉", "KWD":"科威特第纳尔", "QAR":"卡塔尔里亚尔", "CLP":"智利比索", "COP":"哥伦比亚比索", "HUF":"福林", "CZK":"捷克克朗", "PKR":"巴基斯坦卢比", "TWD":"新台币", "MOP":"澳门币",
    "LKR":"斯里兰卡卢比", "NPR":"尼泊尔卢比", "MNT":"图格里克", "KZT":"坚戈", "UAH":"格里夫纳", "PEN":"索尔", "AR_S":"阿根廷比索", "HNL":"伦皮拉", "CRC":"科隆", "UYU":"乌拉圭比索"
}

# 30+ 全球核心城市时差
CITIES = {
    "北京/上海":"Asia/Shanghai", "香港/澳门":"Asia/Hong_Kong", "台北":"Asia/Taipei",
    "东京":"Asia/Tokyo", "首尔":"Asia/Seoul", "新加坡":"Asia/Singapore", 
    "曼谷":"Asia/Bangkok", "吉隆坡":"Asia/Kuala_Lumpur", "迪拜":"Asia/Dubai",
    "伦敦":"Europe/London", "巴黎":"Europe/Paris", "柏林":"Europe/Berlin", 
    "罗马":"Europe/Rome", "马德里":"Europe/Madrid", "莫斯科":"Europe/Moscow",
    "苏黎世":"Europe/Zurich", "阿姆斯特丹":"Europe/Amsterdam", "雅典":"Europe/Athens",
    "纽约":"America/New_York", "洛杉矶":"America/Los_Angeles", "芝加哥":"America/Chicago",
    "多伦多":"America/Toronto", "温哥华":"America/Vancouver", "巴西利亚":"America/Sao_Paulo",
    "悉尼":"Australia/Sydney", "墨尔本":"Australia/Melbourne", "奥克兰":"Pacific/Auckland",
    "开罗":"Africa/Cairo", "约翰内斯堡":"Africa/Johannesburg", "内罗毕":"Africa/Nairobi",
    "新德里":"Asia/Kolkata", "伊斯坦布尔":"Europe/Istanbul", "多哈":"Asia/Qatar"
}

# ==========================================
# 4. PDF 生成逻辑
# ==========================================
def generate_pdf(title_text, items):
    pdf = FPDF()
    pdf.add_page()
    base_dir = os.path.dirname(os.path.abspath(__file__))
    font_path = os.path.join(base_dir, "simsun.ttf")
    logo_path = os.path.join(base_dir, "image_743d5f.jpg")
    
    if os.path.exists(logo_path):
        try:
            pdf.image(logo_path, x=0, y=0, w=210)
            pdf.set_y(35)
        except: pdf.ln(20)
    else: pdf.ln(20)

    if os.path.exists(font_path):
        pdf.add_font("SimSun", style="", fname=font_path)
        pdf.set_font("SimSun", size=16)
    else: pdf.set_font("Helvetica", size=16)

    # 渲染标题
    pdf.set_text_color(0, 0, 0)
    pdf.cell(w=0, h=10, text=title_text, align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # 渲染清单
    pdf.set_font("SimSun", size=11)
    pdf.set_left_margin(25)
    for idx, item in enumerate(items, 1):
        pdf.multi_cell(w=160, h=8, text=f"{idx}. {item}")
        pdf.ln(1)
        
    return bytes(pdf.output())

# ==========================================
# 5. 主界面
# ==========================================
st.sidebar.markdown("# 🏆 功能中心")
menu = st.sidebar.radio("请选择操作项目：", ["🛂 签证材料查询", "💱 实时汇率换算", "⏰ 全球时差查询"])
st.sidebar.divider()
st.sidebar.caption("© 2026 广州市黄金假日")

st.title("✈️ 广州市黄金假日国际旅行社有限公司")
st.markdown('<hr style="border: none; height: 3px; background-image: linear-gradient(to right, transparent, #D4AF37, transparent); margin-top: -10px; margin-bottom: 30px;">', unsafe_allow_html=True)

if menu == "🛂 签证材料查询":
    c1, c2, c3 = st.columns(3)
    with c1: country = st.selectbox("📌 选择目的地国家", sorted(list(VISA_DB.keys())))
    with c2: v_type = st.selectbox("🎫 签证类型", ["旅游签", "商务签", "探亲签"])
    with c3: identity = st.selectbox("👤 申请人身份", ["在职人员", "退休人员", "在校学生", "自由职业者", "学龄前儿童"])

    data = VISA_DB[country][v_type][identity]
    st.markdown(f"### {country} - {v_type} ({identity}) 所需材料")
    st.markdown('<div class="material-card">', unsafe_allow_html=True)
    for i, item in enumerate(data, 1):
        st.write(f"**{i}.** {item}")
    st.markdown('</div>', unsafe_allow_html=True)

    st.write("")
    try:
        pdf_title = f"{country}{v_type}材料清单({identity})"
        pdf_data = generate_pdf(pdf_title, data)
        st.download_button(label="📥 一键下载材料清单", data=pdf_data, file_name=f"{country}_{v_type}_材料清单.pdf", mime="application/pdf")
    except Exception as e:
        st.error(f"PDF生成异常: {e}")

elif menu == "💱 实时汇率换算":
    st.header(f"💱 全球 {len(CURRENCIES)} 种货币实时换算")
    try:
        rates = requests.get("https://api.exchangerate-api.com/v4/latest/CNY").json()['rates']
        c1, c2 = st.columns(2)
        with c1: amt = st.number_input("输入人民币金额", value=100.0)
        with c2: target = st.selectbox("选择目标货币", sorted(list(CURRENCIES.keys())), format_func=lambda x: f"{x} - {CURRENCIES[x]}")
        st.metric("换算结果", f"{amt * rates.get(target, 0):,.2f} {target}")
    except: st.warning("数据连接中...")

elif menu == "⏰ 全球时差查询":
    st.header(f"⏰ 全球 {len(CITIES)} 个重点城市时间")
    city = st.selectbox("搜索城市 (支持中英文关键字)", sorted(list(CITIES.keys())))
    bj = datetime.now(pytz.timezone("Asia/Shanghai"))
    ct = datetime.now(pytz.timezone(CITIES[city]))
    c1, c2 = st.columns(2)
    c1.metric("🏠 北京时间", bj.strftime('%H:%M'))
    c2.metric(f"📍 {city}时间", ct.strftime('%H:%M'), ct.strftime('%m-%d'))

st.markdown("<br><br><center>© 2026 广州市黄金假日国际旅行社有限公司</center>", unsafe_allow_html=True)