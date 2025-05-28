import streamlit as st
import requests
from datetime import datetime
import json

# 配置API地址和超时时间
API_URL = "http://127.0.0.1:8000"
API_TIMEOUT = 180  # 设置前端超时时间比后端长一些

st.set_page_config(
    page_title="生辰八字算命系统",
    page_icon="🔮",
    layout="wide"
)

def check_api_health():
    """检查API服务是否可用"""
    try:
        response = requests.get(f"{API_URL}/health")
        if response.status_code == 200:
            data = response.json()
            if data.get("knowledge_base") != "initialized":
                st.error("知识库未正确初始化，请联系管理员")
                return False
            return True
    except requests.exceptions.RequestException:
        st.error("无法连接到后端服务，请确保服务已启动")
        return False
    return False

def call_api(endpoint: str, data: dict):
    """调用后端API的通用函数"""
    url = f"{API_URL}{endpoint}"
    try:
        # 显示调试信息
        if st.session_state.get('debug', False):
            st.write("Debug Info:")
            st.write(f"URL: {url}")
            st.write(f"Request Data: {json.dumps(data, ensure_ascii=False, indent=2)}")
        
        response = requests.post(
            url,
            json=data,
            headers={"Content-Type": "application/json"},
            timeout=API_TIMEOUT
        )
        
        # 显示调试信息
        if st.session_state.get('debug', False):
            st.write(f"Response Status: {response.status_code}")
            st.write(f"Response Headers: {dict(response.headers)}")
            try:
                st.write(f"Response Body: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
            except:
                st.write(f"Response Text: {response.text}")
        
        if response.status_code == 400:
            error_msg = response.json().get("detail", "输入数据验证失败")
            st.error(f"请求错误: {error_msg}")
            return None
        elif response.status_code == 504:
            st.error("分析请求超时，这可能是因为服务器正在处理大量请求。请稍后重试。")
            return None
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        st.error(f"请求超时（{API_TIMEOUT}秒），这可能是因为：\n1. 服务器响应时间较长\n2. 网络连接不稳定\n\n请稍后重试。")
    except requests.exceptions.ConnectionError:
        st.error("无法连接到服务器，请确保服务已启动")
    except requests.exceptions.RequestException as e:
        st.error(f"API请求失败: {str(e)}")
    except Exception as e:
        st.error(f"发生错误: {str(e)}")
    return None

def main():
    st.title("生辰八字算命系统 🔮")
    st.write("请输入您的出生信息，我们将为您进行详细的命理分析。")

    # Debug模式开关
    if st.sidebar.checkbox("调试模式"):
        st.session_state.debug = True
    
    # 检查API健康状态
    if not check_api_health():
        return
    
    # 创建两列布局
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("基本信息")
        
        # 历法选择
        is_lunar = st.radio(
            "选择历法",
            options=[False, True],
            format_func=lambda x: "农历" if x else "公历",
            horizontal=True,
            help="请选择您的出生日期使用的历法"
        )
        
        # 日期选择
        birth_date = st.date_input(
            f"选择{('农历' if is_lunar else '公历')}出生日期",
            min_value=datetime(1900, 1, 1),
            max_value=datetime.now()
        )
        
        # 时辰选择
        hour_options = [
            (0, "子时 (23:00-01:00)"),
            (2, "丑时 (01:00-03:00)"),
            (4, "寅时 (03:00-05:00)"),
            (6, "卯时 (05:00-07:00)"),
            (8, "辰时 (07:00-09:00)"),
            (10, "巳时 (09:00-11:00)"),
            (12, "午时 (11:00-13:00)"),
            (14, "未时 (13:00-15:00)"),
            (16, "申时 (15:00-17:00)"),
            (18, "酉时 (17:00-19:00)"),
            (20, "戌时 (19:00-21:00)"),
            (22, "亥时 (21:00-23:00)")
        ]
        selected_hour = st.selectbox(
            "选择出生时辰",
            options=[h[0] for h in hour_options],
            format_func=lambda x: next(h[1] for h in hour_options if h[0] == x)
        )
        
        # 提交按钮
        if st.button("开始分析", type="primary"):
            with st.spinner("正在分析中..."):
                # 准备请求数据
                data = {
                    "year": birth_date.year,
                    "month": birth_date.month,
                    "day": birth_date.day,
                    "hour": selected_hour,
                    "is_lunar": is_lunar
                }
                
                # 调用API
                result = call_api("/analyze", data)
                
                if result:
                    with col2:
                        st.subheader("分析结果")
                        
                        # 显示日期信息
                        st.write("### 日期信息")
                        date_info = {
                            "": ["日期"],
                            "公历": [result["bazi"]["solar_date"]],
                            "农历": [result["bazi"]["lunar_date"]]
                        }
                        st.table(date_info)
                        
                        # 显示八字
                        st.write("### 您的八字")
                        bazi = result["bazi"]
                        bazi_df = {
                            "": ["天干", "地支"],
                            "年柱": [bazi["year"][:1], bazi["year"][1:]],
                            "月柱": [bazi["month"][:1], bazi["month"][1:]],
                            "日柱": [bazi["day"][:1], bazi["day"][1:]],
                            "时柱": [bazi["hour"][:1], bazi["hour"][1:]]
                        }
                        st.table(bazi_df)
                        
                        # 显示分析结果
                        st.write("### 命理分析")
                        st.write(result["analysis"])
                        
                        # 显示参考知识
                        with st.expander("查看参考知识"):
                            st.write(result["knowledge_base"])

    # 添加页脚
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center'>
            <p>本系统仅供娱乐参考，请理性对待分析结果</p>
            <p>© 2024 生辰八字算命系统</p>
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main() 