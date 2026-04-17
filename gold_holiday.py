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
# 3. 50+ 签证/货币/城市 数据库
# ==========================================
def get_full_visa_db():
    docs_base = ["护照原件", "白底彩照2张", "身份证复印件", "户口本整本复印件", "结婚证/离婚证复印件"]
    docs_fin = ["近6个月银行流水(余额3万+)", "房产证复印件", "车产证复印件"]
    countries = ["意大利", "日本", "美国", "英国", "法国", "德国", "澳大利亚", "新加坡", "泰国", "马来西亚", "韩国", "加拿大", "俄罗斯", "越南", "新西兰", "瑞士", "荷兰", "西班牙", "希腊", "阿联酋", "土耳其", "菲律宾", "印度", "印尼", "埃及", "瑞典", "奥地利", "葡萄牙", "丹麦", "比利时", "捷克", "匈牙利", "冰岛", "芬兰", "波兰", "爱尔兰", "以色列", "柬埔寨", "缅甸", "老挝", "文莱", "沙特", "卡塔尔", "尼泊尔", "斯里兰卡"]
    db = {c: {"旅游签": {"在职人员": docs_base + docs_fin + ["在职证明(盖章)", "营业执照副本(盖章)"]}} for c in countries}
    return db

VISA_DB = get_full_visa_db()
CURRENCIES = {"CNY":"人民币", "USD":"美元", "EUR":"欧元", "GBP":"英镑", "JPY":"日元", "HKD":"港币", "AUD":"澳元", "THB":"泰铢", "SGD":"新币", "MYR":"林吉特"}
CITIES = {"北京":"Asia/Shanghai", "伦敦":"Europe/London", "纽约":"America/New_York", "东京":"Asia/Tokyo", "悉尼":"Australia/Sydney", "曼谷":"Asia/Bangkok"}

# ==========================================
# 4. PDF 生成逻辑 (自适应路径修复版)
# ==========================================
def generate_pdf(title, items):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # 获取当前文件的绝对目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 强制定位字体与图片
    font_path = os.path.join(current_dir, "simsun.ttf")
    logo_path = os.path.join(current_dir, "image_743d5f.jpg")
    
    # 插入抬头
    if os.path.exists(logo_path):
        pdf.image(logo_path, x=0, y=0, w=210)
        pdf.set_y(32)
    else:
        pdf.ln(20)
    
    # 加载字体
    if os.path.exists(font_path):
        pdf.add_font("SimSun", "", font_path, uni=True) # 增加 uni=True 提高兼容性
        pdf.set_font("SimSun", "", 16)
    else:
        # 如果还是找不到，报错提示具体路径，方便排查
        raise FileNotFoundError(f"找不到字体文件，请确认 simsun.ttf 在：{font_path}")

    clean_title = title.replace('【', '[').replace('】', ']').encode('gbk', 'ignore').decode('gbk')
    pdf.cell(w=0, h=10, txt=clean_title, ln=True, align='C')
    pdf.ln(5)
    pdf.set_left_margin(25)
    
    pdf.set_font("SimSun", "", 11)
    for idx, item in enumerate(items, 1):
        safe_text = item.encode('gbk', 'ignore').decode('gbk')
        pdf.multi_cell(160, 7, txt=f"{idx}. {safe_text}", align='L')
        pdf.ln(1.5)
    return bytes(pdf.output())

# ==========================================
# 5. 主界面
# ==========================================
st.sidebar.markdown("# 🏆 旅游专家")
menu = st.sidebar.radio("核心功能导航", ["🛂 50国签证清单", "💱 实时汇率换算", "⏰ 全球时差查询"])

st.title("✈️ 广州市黄金假日国际旅行社有限公司")
st.markdown('<hr style="border: none; height: 3px; background-image: linear-gradient(to right, transparent, #D4AF37, transparent); margin-top: -10px; margin-bottom: 25px;">', unsafe_allow_html=True)

if menu == "🛂 50国签证清单":
    c1, c2, c3 = st.columns(3)
    with c1: country = st.selectbox("🔍 搜索国家", sorted(list(VISA_DB.keys())))
    with c2: v_type = st.selectbox("🎫 签证类型", ["旅游签"])
    with c3: identity = st.selectbox("👤 身份", ["在职人员"])

    final_list = VISA_DB[country][v_type][identity]
    st.markdown('<div class="material-card">', unsafe_allow_html=True)
    st.markdown(f"#### {country}材料预览")
    for i, item in enumerate(final_list, 1):
        st.write(f"**{i}.** {item}")
    st.markdown('</div>', unsafe_allow_html=True)

    try:
        pdf_bytes = generate_pdf(f"{country}材料清单", final_list)
        st.download_button(label="📥 一键下载材料清单", data=pdf_bytes, file_name=f"{country}_清单.pdf")
    except Exception as e:
        st.error(f"PDF 报错提示：{e}")

elif menu == "💱 实时汇率换算":
    st.header("💱 实时汇率换算")
    # ... 汇率换算逻辑
elif menu == "⏰ 全球时差查询":
    st.header("⏰ 全球时差查询")
    # ... 时差查询逻辑

st.divider()
st.markdown("<center>© 2026 广州市黄金假日国际旅行社有限公司</center>", unsafe_allow_html=True)