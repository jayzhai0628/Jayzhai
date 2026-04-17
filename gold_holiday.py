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

# ==========================================
# 2. 核心专家数据库 (V2.0 确认版)
# ==========================================
VISA_DB = {
    "意大利": {
        "旅游签": {
            "通用": ["护照原件", "2寸白底彩照", "机票酒店单", "申根保险"],
            "在职": ["营业执照盖章", "在职证明", "半年流水"],
            "退休": ["退休证复印件", "养老金流水"]
        },
        "商务签": { "通用": ["邀请函", "派遣信", "业务往来证明"] }
    },
    "澳大利亚": {
        "旅游签": {
            "通用": ["护照彩色扫描", "户口本扫描", "1419表"],
            "在职": ["半年流水", "5-10万存款"],
            "退休": ["退休金流水", "房产证明"]
        }
    }
}
# 自动填充其他国家
for c in ["丹麦", "法国", "英国", "德国", "新加坡", "日本", "美国", "泰国", "悉尼(澳洲)"]:
    if c not in VISA_DB:
        VISA_DB[c] = {"旅游签": {"通用": ["护照", "照片", "资产证明"]}, "商务签": {"通用": ["邀请函"]}}

CURRENCIES = {"CNY":"人民币", "USD":"美元", "EUR":"欧元", "GBP":"英镑", "JPY":"日元", "HKD":"港币"}
CITIES = {"北京":"Asia/Shanghai", "罗马":"Europe/Rome", "悉尼":"Australia/Sydney"}

# ==========================================
# 3. 核心显示区域 (注意看 V2.0 字样)
# ==========================================
st.title("✈️ 广州市黄金假日国际旅行社有限公司")
st.subheader("【官方正式版】综合助手 V2.0")

# 侧边栏
st.sidebar.markdown("### 🏢 官方后台")
st.sidebar.write("广州市黄金假日国际旅行社有限公司")
menu = st.sidebar.radio("功能切换", ["💱 汇率换算", "🌍 时差查询", "🛂 签证指南"])

# --- 模块实现 ---
if menu == "💱 汇率换算":
    st.header("💱 实时汇率换算")
    c1, c2 = st.columns(2)
    with c1:
        base = st.selectbox("持有", list(CURRENCIES.keys()))
        amt = st.number_input("金额", value=100.0)
    with c2:
        target = st.selectbox("兑换", list(CURRENCIES.keys()), index=1)
    if st.button("计算"):
        res = requests.get(f"https://api.exchangerate-api.com/v4/latest/{base}").json()
        st.success(f"### {amt} {base} = {amt*res['rates'][target]:.2f} {target}")

elif menu == "🌍 时差查询":
    st.header("🌍 全球时差")
    city = st.selectbox("城市", list(CITIES.keys()))
    st.metric(f"📍 {city} 当前时间", datetime.now(pytz.timezone(CITIES[city])).strftime('%H:%M'))

elif menu == "🛂 签证指南":
    st.header("🛂 50国签证指南")
    c1, c2, c3 = st.columns(3)
    with c1: country = st.selectbox("目的地", list(VISA_DB.keys()))
    with c2: vtype = st.selectbox("签证类型", list(VISA_DB[country].keys()))
    with c3: ident = st.selectbox("您的身份", ["通用", "在职", "退休", "学生"])
    
    st.divider()
    v_data = VISA_DB[country][vtype]
    st.markdown(f"#### 🔍 {country} - {vtype} 材料清单")
    for item in v_data.get("通用", []): st.write(f"● {item}")
    if ident in v_data:
        st.warning(f"**{ident}额外补充材料：**")
        for item in v_data[ident]: st.write(f"- {item}")

# 页脚
st.sidebar.markdown("---")
st.sidebar.caption("© 2026 广州市黄金假日国际旅行社")