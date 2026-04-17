import streamlit as st
import requests
from datetime import datetime
import pytz

# --- 1. 页面配置 ---
st.set_page_config(
    page_title="广州市黄金假日国际旅行社有限公司",
    page_icon="✈️",
    layout="wide"
)

# --- 2. 自定义金色主题 CSS ---
st.markdown("""
    <style>
    /* 全局背景与字体 */
    .stApp {
        background-color: #FCF9F2;
    }
    /* 标题颜色 */
    h1, h2, h3 {
        color: #B8860B !important;
    }
    /* 侧边栏样式 */
    [data-testid="stSidebar"] {
        background-color: #1E3A5F;
        color: white;
    }
    [data-testid="stSidebar"] * {
        color: white !important;
    }
    /* 按钮样式 */
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        border: 2px solid #D4AF37;
        background-color: #D4AF37;
        color: white;
        font-weight: bold;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #B8860B;
        border-color: #B8860B;
        color: white;
    }
    /* 卡片容器样式 */
    div[data-testid="stVerticalBlock"] > div:has(div.element-container) {
        # border-radius: 15px;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. 核心专家数据库
# ==========================================
VISA_DB = {
    "意大利": {
        "旅游签": {
            "通用": ["护照原件", "2寸白底彩照", "机票酒店订单", "申根保险(保额>30万)"],
            "在职": ["营业执照副本盖章", "中英文在职证明", "半年工资流水(余额3万+)"],
            "退休": ["退休证原件", "养老金流水", "房产证复印件"],
            "学生": ["出生医学证明公证认证", "在读证明", "父母资产证明"]
        },
        "商务签": {
            "通用": ["护照", "照片", "申根保险", "意方公司邀请函", "中方派遣信"],
            "提示": "商务往来证明文件（如合同、往来邮件）可大幅提高出签率。"
        }
    },
    "澳大利亚": {
        "旅游签": {
            "通用": ["护照彩色扫描件", "全家户口本扫描件", "1419申请表"],
            "在职": ["在职证明", "半年流水", "5-10万存款证明"],
            "退休": ["退休证扫描件", "资产证明"],
            "学生": ["在读证明", "父母出资证明"]
        },
        "商务签": { "通用": ["护照扫描件", "1415商务表", "澳方邀请函", "中方派遣信"] }
    },
    "泰国": { 
        "旅游签": { "通用": ["护照(6月有效期)", "返程机票", "目前中国护照永久免签"] }, 
        "商务签": { "通用": ["邀请函", "泰方担保文件", "派遣信"] } 
    }
}

# 自动填充50国列表 (可根据业务需求补充细节)
countries = ["丹麦", "法国", "英国", "德国", "新加坡", "日本", "美国", "新西兰", "瑞士", "荷兰", "西班牙", "俄罗斯", "加拿大", "越南", "马来西亚"]
for c in countries:
    if c not in VISA_DB:
        VISA_DB[c] = {
            "旅游签": {"通用": ["护照原件", "照片", "个人资产证明", "保险"]},
            "商务签": {"通用": ["外方邀请函", "中方派遣信", "营业执照盖章"]}
        }

CURRENCIES = {"CNY":"人民币", "USD":"美元", "EUR":"欧元", "GBP":"英镑", "JPY":"日元", "HKD":"港币", "AUD":"澳元", "THB":"泰铢", "SGD":"新币"}
CITIES = {"北京":"Asia/Shanghai", "罗马":"Europe/Rome", "悉尼":"Australia/Sydney", "伦敦":"Europe/London", "纽约":"America/New_York", "东京":"Asia/Tokyo"}

# ==========================================
# 4. 界面布局
# ==========================================

# 侧边栏
st.sidebar.markdown("# 🏆 黄金假日")
st.sidebar.markdown("### 官方专家决策系统")
st.sidebar.write("---")
menu = st.sidebar.radio("核心功能", ["💱 实时汇率换算", "🌍 全球时差查询", "🛂 50国签证指南"])
st.sidebar.write("---")
st.sidebar.info("客服热线：400-XXXX-XXXX")

# 主界面标题
st.title("✈️ 广州市黄金假日国际旅行社有限公司")
st.write("Professional Global Travel Assistant | 您的全球出行专家")
st.divider()

# --- 模块 1：汇率换算 ---
if menu == "💱 实时汇率换算":
    with st.container(border=True):
        st.header("💱 实时汇率换算")
        col1, col2, col3 = st.columns([2, 1, 2])
        with col1:
            base = st.selectbox("持有货币", list(CURRENCIES.keys()), format_func=lambda x: f"{x} ({CURRENCIES[x]})")
            amount = st.number_input("换算金额", min_value=0.0, value=100.0, step=100.0)
        with col2:
            st.markdown("<br><h2 style='text-align: center;'>➡️</h2>", unsafe_allow_html=True)
        with col3:
            target = st.selectbox("目标货币", list(CURRENCIES.keys()), index=1, format_func=lambda x: f"{x} ({CURRENCIES[x]})")
            
        if st.button("立即换算"):
            try:
                res = requests.get(f"https://api.exchangerate-api.com/v4/latest/{base}").json()
                rate = res['rates'][target]
                total = amount * rate
                st.balloons()
                st.success(f"### {amount:,.2f} {base} = {total:,.2f} {target}")
                st.caption(f"当前参考汇率：1 {base} = {rate} {target}")
            except:
                st.error("数据调取失败，请检查网络链接。")

# --- 模块 2：时差查询 ---
elif menu == "🌍 全球时差查询":
    with st.container(border=True):
        st.header("🌍 全球时差查询")
        city = st.selectbox("选择目的地城市", list(CITIES.keys()))
        col1, col2 = st.columns(2)
        with col1:
            bj_time = datetime.now(pytz.timezone('Asia/Shanghai'))
            st.metric("🏠 北京时间", bj_time.strftime('%H:%M'), bj_time.strftime('%A'))
        with col2:
            tg_time = datetime.now(pytz.timezone(CITIES[city]))
            st.metric(f"📍 {city} 时间", tg_time.strftime('%H:%M'), tg_time.strftime('%A'))
        st.write(f"📅 **目的地日期：** {tg_time.strftime('%Y年%m月%d日')}")

# --- 模块 3：签证指南 ---
elif menu == "🛂 50国签证指南":
    st.header("🛂 50国签证专家指南")
    
    # 筛选区
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            country = st.selectbox("📌 目的地国家", list(VISA_DB.keys()))
        with c2:
            v_type = st.selectbox("🎫 签证类型", list(VISA_DB[country].keys()))
        with c3:
            identity = st.selectbox("👤 您的身份", ["通用", "在职", "退休", "学生"])

    st.write("") # 间距
    
    # 内容展示区
    v_data = VISA_DB[country][v_type]
    
    with st.container(border=True):
        st.subheader(f"🔍 {country} - {v_type} 材料清单")
        st.caption(f"针对身份：{identity}")
        
        tab1, tab2 = st.tabs(["📋 必备材料清单", "💡 专家申请建议"])
        
        with tab1:
            # 必备材料使用卡片展示
            col_main, col_sub = st.columns(2)
            with col_main:
                with st.expander("📌 通用基础材料 (所有身份必备)", expanded=True):
                    for item in v_data.get("通用", []):
                        st.write(f"✅ {item}")
            
            with col_sub:
                if identity != "通用" and identity in v_data:
                    with st.expander(f"👤 {identity} 专项补充材料", expanded=True):
                        for item in v_data[identity]:
                            st.info(item)
                else:
                    st.success("✨ 该身份准备通用材料即可，暂无额外补充。")
                    
        with tab2:
            if "提示" in v_data:
                st.warning(f"**办理贴士：** {v_data['提示']}")
            st.write("1. 所有材料建议保留清晰的彩色扫描件。\n2. 银行流水需在递交前一周内打印最有效。\n3. 请务必确认护照有效期在半年以上。")

# --- 页脚 ---
st.divider()
st.center_text = st.markdown(
    "<div style='text-align: center; color: #999;'>© 2026 广州市黄金假日国际旅行社有限公司 | 专业服务 诚信经营</div>", 
    unsafe_allow_html=True
)