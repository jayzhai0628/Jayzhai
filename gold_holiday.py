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
        padding: 25px; 
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08); 
        border-left: 6px solid #D4AF37; 
        margin-top: 15px;
        color: #333333 !important;
        position: relative;
        overflow: hidden;
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

# ==========================================
# 4. PDF 生成逻辑 (带终极全自动文件夹扫描机制)
# ==========================================
def generate_pdf(title_text, items):
    pdf = FPDF()
    pdf.add_page()
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    font_path = os.path.join(base_dir, "simsun.ttf")
    
    warning_msg = None
    logo_path = None
    
    # 终极扫描策略：1. 明确的可能名称（兼顾大小写）
    possible_names = [
        "image_743d5f.jpg", "image_743d5f.JPG", 
        "image_fed5fe.jpg", "image_fed5fe.JPG",
        "logo.jpg", "logo.png"
    ]
    
    for name in possible_names:
        abs_p = os.path.join(base_dir, name)
        if os.path.exists(abs_p):
            logo_path = abs_p
            break
        elif os.path.exists(name): # 回退使用相对路径
            logo_path = name
            break
            
    # 终极扫描策略：2. 如果没找到指定名字，自动扫描目录下的第一张图片作为抬头
    if not logo_path:
        try:
            for file in os.listdir(base_dir):
                if file.lower().endswith(('.png', '.jpg', '.jpeg')) and ('image_' in file.lower() or 'logo' in file.lower()):
                    logo_path = os.path.join(base_dir, file)
                    break
        except Exception:
            pass

    # 图片云端加载诊断逻辑
    if logo_path:
        try:
            pdf.image(logo_path, x=0, y=0, w=210)
            pdf.set_y(38) # 图片加载成功，游标下移避开图片区域
        except Exception as e: 
            warning_msg = f"⚠️ 找到了图片文件 {os.path.basename(logo_path)}，但服务器解析失败！错误代码：{e}。解决办法：请在 requirements.txt 中加上 Pillow。"
            pdf.set_y(15)
    else: 
        warning_msg = "⚠️ 云端服务器文件夹中没有找到任何图片！请务必确认抬头图片（如 image_743d5f.jpg）已成功 Push/上传 到了云端代码库中！"
        pdf.set_y(15)

    # 设置字体
    if os.path.exists(font_path):
        pdf.add_font("SimSun", style="", fname=font_path)
        pdf.set_font("SimSun", size=18)
    else: 
        pdf.set_font("Helvetica", size=18)

    # 文本颜色为黑色，不渲染公司名称文字
    pdf.set_text_color(0, 0, 0)
    
    # 黑色渲染清单小标题
    pdf.set_font("SimSun", size=14)
    pdf.cell(w=0, h=10, text=title_text, align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    # 渲染带序号的具体材料列表
    pdf.set_font("SimSun", size=11)
    pdf.set_left_margin(25)
    for idx, item in enumerate(items, 1):
        pdf.multi_cell(w=160, h=8, text=f"{idx}. {item}")
        pdf.ln(1)
        
    return bytes(pdf.output()), warning_msg

# ==========================================
# 5. 主界面逻辑
# ==========================================
st.sidebar.markdown("# 🏆 功能中心")
menu = st.sidebar.radio(
    "请选择操作项目：", 
    ["🛂 签证/入境材料查询", "💱 实时汇率换算", "⏰ 全球时差查询"]
)
st.sidebar.divider()
st.sidebar.caption("© 2026 广州市黄金假日")

st.title("✈️ 广州市黄金假日国际旅行社有限公司")
st.markdown('<hr style="border: none; height: 3px; background-image: linear-gradient(to right, transparent, #D4AF37, transparent); margin-top: -10px; margin-bottom: 30px;">', unsafe_allow_html=True)

# ==========================================
# 模块一：签证/入境材料查询
# ==========================================
if menu == "🛂 签证/入境材料查询":
    c1, c2, c3 = st.columns(3)
    with c1: country = st.selectbox("📌 选择目的地", sorted(COUNTRIES_LIST))
    with c2: v_type = st.selectbox("🎫 签证类型", ["旅游签", "商务签", "探亲签"])
    with c3: identity = st.selectbox("👤 申请人身份", ["在职人员", "退休人员", "在校学生", "自由职业者", "学龄前儿童"])

    policy_desc, data, p_type = get_verified_db(country, v_type, identity)
    
    bg_color = "#D4EDDA" if p_type == "FREE" else "#FFF3CD" if p_type == "ARRIVAL" else "#CCE5FF"
    text_color = "#155724" if p_type == "FREE" else "#856404" if p_type == "ARRIVAL" else "#004085"
    st.markdown(f'<div class="policy-tag" style="background-color:{bg_color}; color:{text_color};">{policy_desc}</div>', unsafe_allow_html=True)

    st.markdown(f"### {country} ({v_type}) 材料清单")
    
    # 修复代码块解析 Bug，去除了缩进，确保正确渲染 HTML 而不是显示源代码
    items_html = ""
    for i, item in enumerate(data, 1):
        items_html += f"""<div style="display: flex; margin-bottom: 15px; align-items: flex-start;">
<div style="background-color: #D4AF37; color: white; border-radius: 50%; width: 26px; height: 26px; display: flex; justify-content: center; align-items: center; font-size: 13px; font-weight: bold; margin-right: 12px; flex-shrink: 0; box-shadow: 0 2px 5px rgba(212, 175, 55, 0.4);">{i}</div>
<div style="color: #333; line-height: 1.6; font-size: 15px; padding-top: 2px;">{item}</div>
</div>"""
        
    card_html = f"""<div class="material-card" style="background-image: linear-gradient(to bottom right, #ffffff, #fdfaf2);">
<div style="position: absolute; top: -15px; right: -15px; font-size: 100px; opacity: 0.04; transform: rotate(15deg); pointer-events: none;">✈️</div>
{items_html}
</div>"""
    st.markdown(card_html, unsafe_allow_html=True)
    st.write("") # 增加一点底部间距

    try:
        pdf_title = f"{country}{v_type}材料清单" if p_type != "FREE" else f"{country}入境查验材料"
        
        # 接收并处理生成的 PDF 与警告信息
        pdf_data, warning_msg = generate_pdf(pdf_title, data)
        
        # 如果存在云端错误，在下载按钮上方显示醒目提示
        if warning_msg:
            st.warning(warning_msg, icon="⚠️")
            
        st.download_button(
            label="📥 一键下载材料清单", 
            data=pdf_data, 
            file_name=f"{country}_{v_type}_材料清单.pdf", 
            mime="application/pdf"
        )
    except Exception as e:
        st.error(f"PDF 系统配置中: {e}")

# ==========================================
# 模块二：全球主流货币换算 (支持任意互换)
# ==========================================
elif menu == "💱 实时汇率换算":
    st.header("💱 全球主流货币换算")
    
    # 建立会话状态，用于绑定货币互换
    if 'base_curr' not in st.session_state:
        st.session_state.base_curr = 'CNY'
    if 'target_curr' not in st.session_state:
        st.session_state.target_curr = 'USD'
        
    def swap_currencies():
        # 执行两个选择框的值互换
        st.session_state.base_curr, st.session_state.target_curr = st.session_state.target_curr, st.session_state.base_curr

    # 使用列进行布局
    c1, c2, c3, c4 = st.columns([2.5, 3.5, 1, 3.5])
    with c1: 
        amt = st.number_input("输入金额", value=100.0, min_value=0.0)
    with c2: 
        base = st.selectbox("持有货币", sorted(list(CURRENCIES.keys())), key="base_curr", format_func=lambda x: f"{x} - {CURRENCIES[x]}")
    with c3: 
        st.markdown("<div style='margin-top: 29px;'></div>", unsafe_allow_html=True)
        st.button("🔄", on_click=swap_currencies, help="点击互换货币", use_container_width=True)
    with c4: 
        target = st.selectbox("目标货币", sorted(list(CURRENCIES.keys())), key="target_curr", format_func=lambda x: f"{x} - {CURRENCIES[x]}")
        
    try:
        # 获取基础货币的最新汇率
        rates = requests.get(f"https://api.exchangerate-api.com/v4/latest/{base}").json()['rates']
        target_rate = rates.get(target, 0)
        converted_amt = amt * target_rate
        
        # 黄金质感的美化结果卡片
        result_html = f"""<div style="padding: 20px; background-color: white; border-radius: 12px; border-left: 6px solid #D4AF37; box-shadow: 0 4px 15px rgba(0,0,0,0.08); margin-top: 15px;">
<p style="font-size: 15px; color: #666; margin-bottom: 5px;">换算结果</p>
<h2 style="color: #D4AF37; margin: 0; font-size: 32px;">{converted_amt:,.2f} <span style="font-size: 20px; color: #333;">{target}</span></h2>
<p style="font-size: 13px; color: #999; margin-top: 10px; margin-bottom: 0;">参考汇率: 1 {base} = {target_rate} {target}</p>
</div>"""
        st.markdown(result_html, unsafe_allow_html=True)
    except: 
        st.warning("正在获取最新汇率数据...")

# ==========================================
# 模块三：全球主要城市时间
# ==========================================
elif menu == "⏰ 全球时差查询":
    st.header("⏰ 全球主要城市时间")
    city = st.selectbox("搜索城市", sorted(list(CITIES.keys())))
    bj = datetime.now(pytz.timezone("Asia/Shanghai"))
    ct = datetime.now(pytz.timezone(CITIES[city]))
    c1, c2 = st.columns(2)
    c1.metric("🏠 北京时间", bj.strftime('%H:%M'))
    c2.metric(f"📍 {city}时间", ct.strftime('%H:%M'), ct.strftime('%m-%d'))

st.markdown("<br><br><center>© 2026 广州市黄金假日国际旅行社有限公司</center>", unsafe_allow_html=True)