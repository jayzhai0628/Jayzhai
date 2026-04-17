import streamlit as st
import requests
from datetime import datetime
import pytz

# --- 1. 页面配置 ---
st.set_page_config(
    page_title="广州市黄金假日国际旅行社有限公司 - 签证专家系统",
    page_icon="✈️",
    layout="wide"
)

# --- 2. 品牌主题 CSS (专业金色) ---
st.markdown("""
    <style>
    .stApp { background-color: #FCF9F2; }
    h1, h2, h3 { color: #B8860B !important; font-family: 'Microsoft YaHei'; }
    [data-testid="stSidebar"] { background-color: #1E3A5F; }
    /* 模拟携程风格的清单卡片 */
    .material-card {
        background-color: white; 
        padding: 25px; 
        border-radius: 12px;
        border-top: 5px solid #D4AF37;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        margin-top: 20px;
    }
    .check-item { 
        font-size: 16px; 
        padding: 10px 0;
        border-bottom: 1px solid #eee;
        color: #333;
    }
    .stButton>button {
        width: 100%; border-radius: 8px; border: 2px solid #D4AF37;
        background-color: #D4AF37; color: white; font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. 全量数据模板 (用于动态组合)
# ==========================================

# A. 必要身份证明 (基础)
DOCS_IDENTITY = [
    "【护照】原件：有效期需在6个月以上，至少有两页完整的空白签证页",
    "【照片】近期照片：近6个月内拍摄的2寸(3.5cmx4.5cm)白底彩照2张",
    "【身份证】复印件：二代身份证正反面清晰复印在同一张A4纸上",
    "【户口本】复印件：全家户口本整本复印(从第一页至最后一名成员，无论是否同行)",
    "【结婚证】复印件：已婚提供结婚证；离婚提供离婚证；单身无需提供"
]

# B. 资产证明 (旅游/探亲必需)
DOCS_FINANCE = [
    "【银行流水】对账单：近6个月借记卡流水明细，加盖银行公章，余额建议3-5万以上",
    "【房产证明】复印件：本人或配偶名下的房产证或购房合同复印件(极佳辅助材料)",
    "【车产证明】复印件：名下机动车行驶证复印件(可选辅助材料)"
]

# C. 商务专项 (基础)
DOCS_BIZ_CORE = [
    "【外方邀请函】原件/扫描：外方公司签发的正式邀请函，含邀请人签名及公司盖章",
    "【中方派遣信】原件：单位红头纸打印，包含申请人职位、薪资、访问目的及费用承担，领导签字并加盖公章",
    "【营业执照】复印件：中方单位营业执照副本复印件，加盖单位公章"
]

# ==========================================
# 4. 构建全量数据库
# ==========================================

def get_visa_database():
    return {
        "意大利": {
            "旅游签": {
                "在职人员": DOCS_IDENTITY + DOCS_FINANCE + [
                    "【在职证明】原件：中英文对照，红头纸打印，注明职位、薪水、准假时间",
                    "【营业执照】复印件：所在单位营业执照副本复印件，加盖公章",
                    "【旅行计划】机票预订单、全程酒店确认单、申根境外医疗保险(保额>30万)"
                ],
                "退休人员": DOCS_IDENTITY + DOCS_FINANCE + [
                    "【退休证】复印件：退休证原件及复印件",
                    "【养老金流水】对账单：最近6个月的养老金发放明细",
                    "【旅行计划】机票、酒店订单、境外医疗保险"
                ],
                "学生/未成年": DOCS_IDENTITY + [
                    "【在读证明】原件：学校抬头纸打印并盖章",
                    "【出生医学证明】原件及公证认证：需经外事办认证(未成年人核心材料)",
                    "【父母资产】父母双方的在职证明、近半年流水及出资声明信",
                    "【旅行计划】机票、酒店预订及申根保险"
                ]
            },
            "商务签": {
                "在职人员": DOCS_IDENTITY + DOCS_BIZ_CORE + [
                    "【意方Visura】复印件：意方公司的营业执照(Visura Camerale)，近6个月内开具",
                    "【业务往来证明】复印件：双方贸易往来凭证(如合同、发票、提单、往来邮件等)",
                    "【境外保险】申根医疗保险(保额>30万)"
                ]
            }
        },
        "澳大利亚": {
            "旅游签": {
                # 澳洲特殊要求：所有复印件需为彩色扫描
                "在职人员": [d.replace("复印件", "彩色扫描件") for d in DOCS_IDENTITY + DOCS_FINANCE] + [
                    "【1419申请表】签字原件", "【54家庭成员表】签字原件", "【在职证明】彩色扫描件"
                ],
                "退休人员": [d.replace("复印件", "彩色扫描件") for d in DOCS_IDENTITY + DOCS_FINANCE] + ["【退休证】彩色扫描件"]
            },
            "商务签": {
                "在职人员": [d.replace("复印件", "彩色扫描件") for d in DOCS_IDENTITY] + ["【澳方邀请函】", "【派遣信】", "【1415商务表】"]
            }
        },
        "泰国": {
            "旅游签": {
                "在职人员": ["【护照】原件：有效期6个月以上", "【机票】回程机票确认单", "【现金】建议随身携带4000元等值现金备查(免签入境)"],
                "退休人员": ["【护照】原件", "【回程机票单】", "【退休证】复印件(备查)"]
            }
        }
    }

VISA_DB = get_visa_database()

# 自动补全模版 (50国逻辑)
all_countries = ["法国", "英国", "德国", "新加坡", "日本", "美国", "新西兰", "瑞士", "荷兰", "西班牙", "俄罗斯", "加拿大", "越南", "韩国", "希腊", "瑞典"]
for c in all_countries:
    if c not in VISA_DB:
        VISA_DB[c] = {
            "旅游签": {
                "在职人员": DOCS_IDENTITY + DOCS_FINANCE + ["【在职证明】红头纸盖章件", "【营业执照】副本盖章件"],
                "退休人员": DOCS_IDENTITY + DOCS_FINANCE + ["【退休证】复印件", "【养老金流水】单据"],
                "学生": DOCS_IDENTITY + ["【在读证明】", "【出生证公证认证】", "【父母资产证明】"]
            },
            "商务签": {
                "在职人员": DOCS_IDENTITY + DOCS_BIZ_CORE + ["【业务往来证明】(建议)"]
            }
        }

# ==========================================
# 5. 网页界面
# ==========================================

# 侧边栏
st.sidebar.markdown("# 🏆 黄金假日")
st.sidebar.markdown("### 签证专家决策系统")
st.sidebar.write("---")
menu = st.sidebar.radio("核心功能", ["🛂 50国签证全量清单", "💱 实时汇率换算", "🌍 全球时差查询"])
st.sidebar.write("---")
st.sidebar.caption("© 2026 广州市黄金假日国际旅行社")

st.title("✈️ 广州市黄金假日国际旅行社有限公司")
st.write("Professional Global Travel Assistant | 全人群精准材料清单")
st.divider()

if menu == "🛂 50国签证全量清单":
    st.header("🛂 签证申请材料清单")
    
    # 筛选器
    with st.container():
        c1, c2, c3 = st.columns(3)
        with c1: country = st.selectbox("📍 目的地国家", sorted(list(VISA_DB.keys())))
        with c2: v_type = st.selectbox("🎫 签证类型", list(VISA_DB[country].keys()))
        with c3:
            identities = list(VISA_DB[country][v_type].keys())
            identity = st.selectbox("👤 您的身份", identities)

    st.write("")
    
    # 获取全量合并后的数据
    final_list = VISA_DB[country][v_type][identity]
    
    # 展示区域
    st.markdown(f"### 📋 {country} - {v_type} 【{identity}】 完整清单")
    
    st.markdown('<div class="material-card">', unsafe_allow_html=True)
    for i, item in enumerate(final_list):
        st.markdown(f'<div class="check-item">□ {item}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # 下载功能
    dl_txt = f"【广州市黄金假日国际旅行社有限公司】签证申请清单\n"
    dl_txt += f"目的地：{country} | 类型：{v_type} | 身份：{identity}\n"
    dl_txt += "="*45 + "\n\n"
    for item in final_list:
        dl_txt += f"[ ] {item}\n"
    dl_txt += "\n\n💡 注意事项：\n1. 请确保所有扫描/复印件内容清晰完整。\n2. 银行流水需在递交前一周内打印方为有效。"

    st.write("")
    st.download_button(
        label=f"📥 下载【{identity}】专属完整材料清单 (TXT)",
        data=dl_txt,
        file_name=f"{country}_{identity}_清单.txt",
        mime="text/plain"
    )

elif menu == "💱 实时汇率换算":
    # (保持原有汇率模块代码...)
    st.header("💱 实时汇率换算")
    res = requests.get(f"https://api.exchangerate-api.com/v4/latest/CNY").json()
    st.write(f"今日人民币汇率参考: USD:{res['rates']['USD']} | EUR:{res['rates']['EUR']}")

elif menu == "🌍 全球时差查询":
    # (保持原有时差模块代码...)
    st.header("🌍 全球时差查询")
    t = datetime.now(pytz.timezone('Europe/Rome'))
    st.write(f"罗马当前时间: {t.strftime('%H:%M')}")

st.divider()
st.markdown("<center>© 2026 广州市黄金假日国际旅行社有限公司 | 签证部技术支持</center>", unsafe_allow_html=True)