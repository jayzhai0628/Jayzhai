import streamlit as st
import requests
from datetime import datetime
import pytz
from fpdf import FPDF
import io
import os

# --- 新增：尝试导入地图渲染库 ---
try:
    import plotly.express as px
    import pandas as pd
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# --- 1. 页面配置 ---
st.set_page_config(
    page_title="广州市黄金假日国际旅行社有限公司", 
    page_icon="✈️", 
    layout="wide"
)

# --- 2. 响应式移动端美化 CSS ---
st.markdown("""
    <style>
    /* 全局背景与基础文字颜色，防止手机模式下文字隐身 */
    .stApp { 
        background-color: #FCF9F2;
        color: #333333;
    }
    
    /* 侧边栏样式优化 */
    [data-testid="stSidebar"] { 
        background-color: #1E3A5F !important; 
    }
    [data-testid="stSidebar"] * { 
        color: #FFFFFF !important; 
    }
    
    /* 标题响应式 */
    h1 { 
        color: #B8860B !important; 
        text-align: center; 
        font-weight: bold;
        font-size: calc(1.5rem + 1vw) !important;
    }
    
    /* 下载按钮：手机端自适应宽度 */
    .stDownloadButton>button {
        width: 100% !important; 
        max-width: 300px;
        padding: 10px 20px !important;
        border-radius: 8px; 
        border: 1px solid #D4AF37; 
        background-color: #D4AF37; 
        color: white !important; 
        font-weight: bold;
        display: block;
        margin: 20px 0;
    }
    
    /* 材料卡片：移动端增加自适应间距 */
    .material-card {
        background-color: white; 
        padding: 20px; 
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1); 
        border-left: 5px solid #D4AF37; 
        margin-top: 15px;
        color: #333333 !important;
    }
    
    /* 政策标签样式 */
    .policy-tag {
        padding: 8px 15px; 
        border-radius: 10px; 
        font-size: 14px; 
        font-weight: bold; 
        margin-bottom: 15px; 
        display: inline-block;
        line-height: 1.4;
    }

    /* 情报卡片样式 */
    .info-box {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        border-top: 4px solid #D4AF37;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        height: 100%;
    }
    
    /* 适配 Streamlit 默认文字 */
    .stMarkdown p, .stMarkdown li {
        color: #333333 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. 核心全量数据库 (2026 验证版)
# ==========================================
def get_verified_db(target_country, v_type, identity):
    # 免签/落地签名单 (针对中国普通护照)
    visa_free = ["新加坡", "马来西亚", "泰国", "阿联酋", "卡塔尔", "哈萨克斯坦", "马尔代夫", "斐济", "塞舌尔", "毛里求斯", "阿尔巴尼亚"]
    visa_arrival = ["埃及", "老挝", "柬埔寨", "尼泊尔", "越南", "沙特", "斯里兰卡", "马达加斯加"]
    
    if target_country in visa_free:
        policy = "FREE"
        policy_desc = "🌟 互免签证 (仅需准备入境查验材料)"
    elif target_country in visa_arrival:
        policy = "ARRIVAL"
        policy_desc = "📝 落地签/电子签 (建议提前准备基础材料)"
    else:
        policy = "REQUIRED"
        policy_desc = "🛂 需办理正式签证"

    # 照片尺寸精准判断
    photo_size = "51mm × 51mm (2英寸)" if target_country == "美国" else "35mm × 45mm"
    
    # 基础材料
    base = [
        f"护照原件 (有效期6个月以上，至少2页空白)",
        f"白底彩照2张 (尺寸{photo_size}，近6个月拍摄)"
    ]
    
    if policy == "FREE":
        base = [f"护照原件 (有效期6个月以上)", "电子入境卡 (请根据目的地官网提前3天在线填报)"]
        id_docs = ["往返机票行程单 (打印备用)", "全程酒店预订单 (打印备用)", "足够支付旅费的资金证明 (现金或信用卡)"]
        final_list = base + id_docs
    else:
        base += ["身份证正反面复印件", "户口本整本复印件"]
        if target_country == "美国":
            base += ["DS-160申请表确认页", "签证面谈预约单"]
            
        id_map = {
            "在职人员": ["红头在职证明 (含职位、薪资、公章、负责人签字)", "营业执照副本/代码证复印件 (加盖公章)", "个人近6个月银行流水 (余额5万+建议)"],
            "退休人员": ["退休证复印件", "退休金近6个月银行流水账单"],
            "在校学生": ["在校证明 (学校抬头纸盖章)", "学生证复印件", "出生医学证明复印件", "父母出资证明及流水"],
            "自由职业者": ["个人收入来源说明信 (亲笔签名)", "个人近6个月活跃银行流水", "5万以上定期存款证明"],
            "学龄前儿童": ["出生医学证明复印件", "父母结婚证复印件", "父母资产证明材料"]
        }
        type_map = {
            "旅游签": ["往返机票预订单", "酒店确认单", "详细个人旅游行程"],
            "商务签": ["外方正式邀请函 (注明出访目的与费用承担)", "中方派遣函 (红头盖章)", "双方商业往来凭证"],
            "探亲签": ["亲属关系公证书 (需外交部认证)", "邀请人护照及有效签证/居留复印件", "邀请函 (含居住地址)"]
        }
        final_list = base + id_map.get(identity, []) + type_map.get(v_type, [])

    return policy_desc, final_list, policy

# 全量配置项
CURRENCIES = {"CNY":"人民币", "USD":"美元", "EUR":"欧元", "GBP":"英镑", "JPY":"日元", "HKD":"港币", "AUD":"澳元", "THB":"泰铢", "SGD":"新币", "MYR":"林吉特", "KRW":"韩元", "CAD":"加元", "RUB":"卢布", "NZD":"纽币", "CHF":"瑞郎", "AED":"迪拉姆", "SAR":"里亚尔", "INR":"卢比", "IDR":"印尼盾", "PHP":"比索", "VND":"越南盾", "EGP":"埃及镑", "ZAR":"兰特", "SEK":"克朗", "NOK":"挪威克朗", "DKK":"丹麦克朗", "PLN":"兹罗提", "ILS":"谢克尔", "BRL":"雷亚尔", "MXN":"墨西哥比索", "TRY":"土耳其里拉", "KWD":"科威特第纳尔", "QAR":"卡塔尔里亚尔", "CLP":"智利比索", "COP":"哥伦比亚比索", "HUF":"福林", "CZK":"捷克克朗", "PKR":"巴基斯坦卢比", "TWD":"新台币", "MOP":"澳门币", "LKR":"斯里兰卡卢比", "NPR":"尼泊尔卢比", "MNT":"图格里克", "KZT":"坚戈", "UAH":"格里夫纳", "PEN":"索尔", "AR_S":"阿根廷比索", "HNL":"伦皮拉", "CRC":"科隆", "UYU":"乌拉圭比索"}

CITIES = {
    "北京/上海":"Asia/Shanghai", "香港/澳门":"Asia/Hong_Kong", "台北":"Asia/Taipei", "东京":"Asia/Tokyo", "首尔":"Asia/Seoul", 
    "新加坡":"Asia/Singapore", "曼谷":"Asia/Bangkok", "吉隆坡":"Asia/Kuala_Lumpur", "迪拜":"Asia/Dubai", "伦敦":"Europe/London", 
    "巴黎":"Europe/Paris", "柏林":"Europe/Berlin", "罗马":"Europe/Rome", "马德里":"Europe/Madrid", "莫斯科":"Europe/Moscow", 
    "苏黎世":"Europe/Zurich", "纽约":"America/New_York", "洛杉矶":"America/Los_Angeles", "多伦多":"America/Toronto", "温哥华":"America/Vancouver", 
    "悉尼":"Australia/Sydney", "墨尔本":"Australia/Melbourne", "奥克兰":"Pacific/Auckland", "新德里":"Asia/Kolkata", "伊斯坦布尔":"Europe/Istanbul",
    "开罗":"Africa/Cairo", "约翰内斯堡":"Africa/Johannesburg", "雅典":"Europe/Athens", "阿姆斯特丹":"Europe/Amsterdam", "芝加哥":"America/Chicago"
}

COUNTRIES_LIST = ["意大利", "日本", "美国", "英国", "法国", "德国", "澳大利亚", "新加坡", "泰国", "马来西亚", "韩国", "加拿大", "越南", "新西兰", "瑞士", "荷兰", "西班牙", "希腊", "阿联酋", "土耳其", "俄罗斯", "菲律宾", "印度", "印尼", "埃及", "南非", "瑞典", "奥地利", "葡萄牙", "丹麦", "比利时", "捷克", "匈牙利", "冰岛", "芬兰", "波兰", "爱尔兰", "以色列", "柬埔寨", "缅甸", "老挝", "文莱", "沙特", "卡塔尔", "尼泊尔", "斯里兰卡", "巴西", "阿根廷", "墨西哥", "智利"]

# 新增：国家信息元数据（用于地图联动及多模块一站式查询）
def get_country_meta(country):
    # 格式: 国家 -> (默认货币代码, 默认时区城市, ISO-3缩写)
    meta = {
        "美国": ("USD", "纽约", "USA"), "英国": ("GBP", "伦敦", "GBR"), "日本": ("JPY", "东京", "JPN"),
        "澳大利亚": ("AUD", "悉尼", "AUS"), "法国": ("EUR", "巴黎", "FRA"), "德国": ("EUR", "柏林", "DEU"),
        "意大利": ("EUR", "罗马", "ITA"), "新加坡": ("SGD", "新加坡", "SGP"), "泰国": ("THB", "曼谷", "THA"),
        "马来西亚": ("MYR", "吉隆坡", "MYS"), "韩国": ("KRW", "首尔", "KOR"), "加拿大": ("CAD", "多伦多", "CAN"),
        "阿联酋": ("AED", "迪拜", "ARE"), "俄罗斯": ("RUB", "莫斯科", "RUS"), "新西兰": ("NZD", "奥克兰", "NZL"),
        "瑞士": ("CHF", "苏黎世", "CHE"), "埃及": ("EGP", "开罗", "EGY"), "南非": ("ZAR", "约翰内斯堡", "ZAF"),
        "西班牙": ("EUR", "马德里", "ESP"), "希腊": ("EUR", "雅典", "GRC"), "荷兰": ("EUR", "阿姆斯特丹", "NLD"),
        "印度": ("INR", "新德里", "IND"), "印尼": ("IDR", "吉隆坡", "IDN"), "菲律宾": ("PHP", "北京/上海", "PHL"),
        "越南": ("VND", "曼谷", "VNM"), "土耳其": ("TRY", "伊斯坦布尔", "TUR"), "沙特": ("SAR", "迪拜", "SAU"),
        "卡塔尔": ("QAR", "多哈", "QAT"), "阿根廷": ("AR_S", "巴西利亚", "ARG"), "巴西": ("BRL", "巴西利亚", "BRA"),
        "墨西哥": ("MXN", "芝加哥", "MEX"), "丹麦": ("DKK", "柏林", "DNK"), "瑞典": ("SEK", "柏林", "SWE"),
        "葡萄牙": ("EUR", "伦敦", "PRT"), "爱尔兰": ("EUR", "伦敦", "IRL"), "以色列": ("ILS", "雅典", "ISR"),
        "芬兰": ("EUR", "雅典", "FIN"), "波兰": ("PLN", "柏林", "POL"), "捷克": ("CZK", "柏林", "CZE"),
        "比利时": ("EUR", "巴黎", "BEL"), "奥地利": ("EUR", "柏林", "AUT"), "柬埔寨": ("USD", "曼谷", "KHM"),
        "尼泊尔": ("NPR", "新德里", "NPL"), "斯里兰卡": ("LKR", "新德里", "LKA")
    }
    return meta.get(country, ("USD", "北京/上海", None))

# ==========================================
# 4. PDF 生成逻辑 (无黄色抬头，确保黑色正式文字)
# ==========================================
def generate_pdf(title_text, items):
    pdf = FPDF()
    pdf.add_page()
    base_dir = os.path.dirname(os.path.abspath(__file__))
    font_path = os.path.join(base_dir, "simsun.ttf")
    logo_path = os.path.join(base_dir, "image_743d5f.jpg")
    
    # 1. 尝试插入图片抬头
    if os.path.exists(logo_path):
        try:
            pdf.image(logo_path, x=0, y=0, w=210)
            pdf.set_y(35)
        except: pdf.ln(15)
    else: pdf.ln(15)

    # 2. 设置字体
    if os.path.exists(font_path):
        pdf.add_font("SimSun", style="", fname=font_path)
        pdf.set_font("SimSun", size=18)
    else: pdf.set_font("Helvetica", size=18)

    # 3. 确保文本颜色为黑色
    pdf.set_text_color(0, 0, 0)
    
    # 4. 黑色渲染清单小标题
    pdf.set_font("SimSun", size=14)
    pdf.cell(w=0, h=10, text=title_text, align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    # 5. 渲染带序号列表
    pdf.set_font("SimSun", size=11)
    pdf.set_left_margin(25)
    for idx, item in enumerate(items, 1):
        pdf.multi_cell(w=160, h=8, text=f"{idx}. {item}")
        pdf.ln(1)
        
    return bytes(pdf.output())

# ==========================================
# 5. 主界面逻辑
# ==========================================
st.sidebar.markdown("# 🏆 功能中心")
# ★★★ 完全保留原来的 3 个菜单，新增了第 4 个“全球地图”选项 ★★★
menu = st.sidebar.radio(
    "请选择操作项目：", 
    ["🌍 全球地图与情报", "🛂 签证/入境材料查询", "💱 实时汇率换算", "⏰ 全球时差查询"]
)
st.sidebar.divider()
st.sidebar.caption("© 2026 广州市黄金假日")

st.title("✈️ 广州市黄金假日国际旅行社有限公司")
st.markdown('<hr style="border: none; height: 3px; background-image: linear-gradient(to right, transparent, #D4AF37, transparent); margin-top: -10px; margin-bottom: 30px;">', unsafe_allow_html=True)


# ==========================================
# 模块一：新增的全球地图与情报 (完全独立的模块)
# ==========================================
if menu == "🌍 全球地图与情报":
    st.header("🌍 全球签证地图与国家全景情报")
    
    # 渲染交互式地图
    if PLOTLY_AVAILABLE:
        map_data = []
        for c in COUNTRIES_LIST:
            _, _, iso = get_country_meta(c)
            if iso:
                _, _, p_type = get_verified_db(c, "旅游签", "在职人员")
                policy_label = "互免签证" if p_type == "FREE" else "落地签/电子签" if p_type == "ARRIVAL" else "需办签证"
                map_data.append({"Country": c, "ISO": iso, "Policy": policy_label})
                
        df = pd.DataFrame(map_data)
        
        fig = px.choropleth(
            df, 
            locations="ISO", 
            color="Policy", 
            hover_name="Country",
            color_discrete_map={
                "互免签证": "#28a745", 
                "落地签/电子签": "#ffc107", 
                "需办签证": "#007bff"
            },
            projection="natural earth"
        )
        fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("💡 提示：系统检测到未安装 `plotly` 和 `pandas`，无法显示地图。请在终端执行 `pip install plotly pandas`。下方的全景情报仍可正常使用。")
        st.write("")

    # 一站式全景情报面板
    st.markdown("### 🔍 国家全景情报查询")
    st.markdown("👉 请在下方选择国家，即可**一站式获取**该国的签证、汇率与时差信息。")
    
    selected_country = st.selectbox("📌 请选择查询国家", sorted(COUNTRIES_LIST))
    
    # 获取三项数据
    cur_code, city_name, _ = get_country_meta(selected_country)
    policy_desc, _, p_type = get_verified_db(selected_country, "旅游签", "在职人员")
    
    rate_val = "正在请求接口..."
    try:
        rates = requests.get("https://api.exchangerate-api.com/v4/latest/CNY").json()['rates']
        rate_val = f"{rates.get(cur_code, 0):,.2f} {cur_code}"
    except:
        rate_val = "暂无数据"
        
    tz_str = CITIES.get(city_name, "Asia/Shanghai")
    ct = datetime.now(pytz.timezone(tz_str))
    time_str = ct.strftime('%H:%M  (%m月%d日)')

    st.write("")
    ic1, ic2, ic3 = st.columns(3)
    
    with ic1:
        st.markdown(f"""
        <div class="info-box">
            <h4 style="color:#1E3A5F; margin-top:0;">🛂 签证政策</h4>
            <p style="font-size: 14px;"><strong>{selected_country}</strong><br><br>{policy_desc}</p>
        </div>
        """, unsafe_allow_html=True)
        
    with ic2:
        st.markdown(f"""
        <div class="info-box">
            <h4 style="color:#1E3A5F; margin-top:0;">💱 实时汇率</h4>
            <p style="font-size: 14px;"><strong>基准：100 人民币 (CNY)</strong><br><br>可兑换：<b style="color:#D4AF37; font-size:16px;">{rate_val}</b></p>
        </div>
        """, unsafe_allow_html=True)
        
    with ic3:
        st.markdown(f"""
        <div class="info-box">
            <h4 style="color:#1E3A5F; margin-top:0;">⏰ 当地时间</h4>
            <p style="font-size: 14px;"><strong>参考城市：{city_name}</strong><br><br>当地时间：<b style="color:#D4AF37; font-size:16px;">{time_str}</b></p>
        </div>
        """, unsafe_allow_html=True)


# ==========================================
# 模块二：保留的原功能 - 签证/入境材料查询
# ==========================================
elif menu == "🛂 签证/入境材料查询":
    c1, c2, c3 = st.columns(3)
    with c1: country = st.selectbox("📌 选择目的地", sorted(COUNTRIES_LIST))
    with c2: v_type = st.selectbox("🎫 签证类型", ["旅游签", "商务签", "探亲签"])
    with c3: identity = st.selectbox("👤 申请人身份", ["在职人员", "退休人员", "在校学生", "自由职业者", "学龄前儿童"])

    policy_desc, data, p_type = get_verified_db(country, v_type, identity)
    
    bg_color = "#D4EDDA" if p_type == "FREE" else "#FFF3CD" if p_type == "ARRIVAL" else "#CCE5FF"
    text_color = "#155724" if p_type == "FREE" else "#856404" if p_type == "ARRIVAL" else "#004085"
    st.markdown(f'<div class="policy-tag" style="background-color:{bg_color}; color:{text_color};">{policy_desc}</div>', unsafe_allow_html=True)

    st.markdown(f"### {country} ({v_type}) 材料清单")
    st.markdown('<div class="material-card">', unsafe_allow_html=True)
    for i, item in enumerate(data, 1):
        st.write(f"**{i}.** {item}")
    st.markdown('</div>', unsafe_allow_html=True)

    try:
        pdf_title = f"{country}{v_type}材料清单" if p_type != "FREE" else f"{country}入境查验材料"
        pdf_data = generate_pdf(pdf_title, data)
        st.download_button(
            label="📥 一键下载材料清单", 
            data=pdf_data, 
            file_name=f"{country}_{v_type}_材料清单.pdf", 
            mime="application/pdf"
        )
    except Exception as e:
        st.error(f"PDF 系统配置中: {e}")


# ==========================================
# 模块三：保留的原功能 - 实时汇率换算
# ==========================================
elif menu == "💱 实时汇率换算":
    st.header(f"💱 全球 {len(CURRENCIES)} 种货币换算")
    try:
        rates = requests.get("https://api.exchangerate-api.com/v4/latest/CNY").json()['rates']
        c1, c2 = st.columns(2)
        with c1: amt = st.number_input("金额 (CNY)", value=100.0)
        with c2: target = st.selectbox("目标货币", sorted(list(CURRENCIES.keys())), format_func=lambda x: f"{x} - {CURRENCIES[x]}")
        st.metric("结果", f"{amt * rates.get(target, 0):,.2f} {target}")
    except: st.warning("数据接口连接中...")


# ==========================================
# 模块四：保留的原功能 - 全球时差查询
# ==========================================
elif menu == "⏰ 全球时差查询":
    st.header(f"⏰ 全球 {len(CITIES)} 个重点城市时间")
    city = st.selectbox("搜索城市", sorted(list(CITIES.keys())))
    bj = datetime.now(pytz.timezone("Asia/Shanghai"))
    ct = datetime.now(pytz.timezone(CITIES[city]))
    c1, c2 = st.columns(2)
    c1.metric("🏠 北京时间", bj.strftime('%H:%M'))
    c2.metric(f"📍 {city}时间", ct.strftime('%H:%M'), ct.strftime('%m-%d'))

st.markdown("<br><br><center>© 2026 广州市黄金假日国际旅行社有限公司</center>", unsafe_allow_html=True)