from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import os
import requests
from dotenv import load_dotenv
from typing import Optional
import logging
from api.knowledge_base import SimpleKnowledgeBase, initialize_knowledge_base
from lunar_python import Lunar, Solar

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

# 配置API密钥和超时时间
DEEPSEEK_API_KEY = "xxx"
DEEPSEEK_TIMEOUT = 120  # 设置120秒超时

app = FastAPI()

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],  # Streamlit 默认端口
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化知识库
try:
    kb = initialize_knowledge_base()
    logger.info("知识库初始化成功")
except Exception as e:
    logger.error(f"知识库初始化失败: {str(e)}")
    kb = None

class BirthInfo(BaseModel):
    year: int
    month: int
    day: int
    hour: int
    is_lunar: bool = False

# 天干
HEAVENLY_STEMS = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
# 地支
EARTHLY_BRANCHES = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

def convert_lunar_to_solar(year: int, month: int, day: int) -> tuple:
    """将农历日期转换为公历日期"""
    try:
        lunar = Lunar.fromYmd(year, month, day)
        solar = lunar.getSolar()
        return (solar.getYear(), solar.getMonth(), solar.getDay())
    except Exception as e:
        logger.error(f"农历转换失败: {str(e)}")
        raise ValueError(f"农历日期转换失败: {str(e)}")

def get_gz_hour(hour: int) -> tuple:
    """获取时辰的干支"""
    # 12时辰对应的地支
    hour_to_branch = {
        23: 0, 0: 0,     # 子时 (23:00-01:00)
        1: 1, 2: 1,      # 丑时 (01:00-03:00)
        3: 2, 4: 2,      # 寅时 (03:00-05:00)
        5: 3, 6: 3,      # 卯时 (05:00-07:00)
        7: 4, 8: 4,      # 辰时 (07:00-09:00)
        9: 5, 10: 5,     # 巳时 (09:00-11:00)
        11: 6, 12: 6,    # 午时 (11:00-13:00)
        13: 7, 14: 7,    # 未时 (13:00-15:00)
        15: 8, 16: 8,    # 申时 (15:00-17:00)
        17: 9, 18: 9,    # 酉时 (17:00-19:00)
        19: 10, 20: 10,  # 戌时 (19:00-21:00)
        21: 11, 22: 11   # 亥时 (21:00-23:00)
    }
    branch_index = hour_to_branch.get(hour, 0)  # 默认子时
    return branch_index

def calculate_bazi(birth_info: BirthInfo) -> dict:
    """计算八字"""
    try:
        # 验证输入
        if not (1900 <= birth_info.year <= datetime.now().year):
            raise ValueError("年份必须在1900年至今之间")
        if not (1 <= birth_info.month <= 12):
            raise ValueError("月份必须在1-12之间")
        if not (1 <= birth_info.day <= 31):
            raise ValueError("日期必须在1-31之间")
        if not (0 <= birth_info.hour <= 23):
            raise ValueError("小时必须在0-23之间")

        # 如果是农历，转换为公历
        year, month, day = (
            convert_lunar_to_solar(birth_info.year, birth_info.month, birth_info.day)
            if birth_info.is_lunar
            else (birth_info.year, birth_info.month, birth_info.day)
        )

        # 使用lunar-python计算八字
        solar = Solar.fromYmd(year, month, day)
        lunar = solar.getLunar()
        
        # 获取年月日时的干支
        year_gz = lunar.getYearInGanZhi()
        month_gz = lunar.getMonthInGanZhi()
        day_gz = lunar.getDayInGanZhi()
        
        # 获取时辰干支
        hour_branch_index = get_gz_hour(birth_info.hour)
        day_stem_index = HEAVENLY_STEMS.index(day_gz[0])  # 获取日干索引
        hour_stem_index = (day_stem_index * 2 + hour_branch_index) % 10
        hour_gz = f"{HEAVENLY_STEMS[hour_stem_index]}{EARTHLY_BRANCHES[hour_branch_index]}"

        logger.info(f"八字计算结果 - 年: {year_gz}, 月: {month_gz}, 日: {day_gz}, 时: {hour_gz}")
        
        return {
            "year": year_gz,
            "month": month_gz,
            "day": day_gz,
            "hour": hour_gz,
            "solar_date": f"{year}年{month}月{day}日",
            "lunar_date": f"{lunar.getYearInChinese()}年{lunar.getMonthInChinese()}月{lunar.getDayInChinese()}"
        }
    except Exception as e:
        logger.error(f"八字计算错误: {str(e)}")
        raise HTTPException(status_code=400, detail=f"八字计算错误: {str(e)}")

@app.post("/analyze")
async def analyze_bazi(birth_info: BirthInfo):
    try:
        logger.info(f"收到请求: {birth_info}")
        
        # 检查知识库状态
        if kb is None:
            raise HTTPException(status_code=500, detail="知识库未正确初始化")
        
        # 计算八字
        bazi = calculate_bazi(birth_info)
        logger.info(f"八字计算结果: {bazi}")
        
        # 获取相关命理知识
        try:
            knowledge = kb.get_relevant_knowledge(bazi)
            logger.info("成功获取命理知识")
        except Exception as e:
            logger.error(f"获取命理知识失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"获取命理知识失败: {str(e)}")
        
        # 使用配置的API密钥
        if not DEEPSEEK_API_KEY:
            logger.error("DeepSeek API key未配置")
            raise HTTPException(status_code=500, detail="DeepSeek API key not configured")
        
        # 构建提示词
        prompt = f"""
        请基于以下信息进行命理分析：
        
        八字信息：
        年柱：{bazi['year']}
        月柱：{bazi['month']}
        日柱：{bazi['day']}
        时柱：{bazi['hour']}
        
        公历：{bazi['solar_date']}
        农历：{bazi['lunar_date']}
        
        相关命理知识：
        {knowledge}
        
        请提供详细的命理分析，包括：
        1. 八字基本特征
        2. 五行属性分析
        3. 命局格局判断
        4. 运势发展预测
        5. 事业、财运、姻缘等方面的分析
        
        注意：分析要专业、客观，避免过于玄学或迷信的说法。
        """
        
        try:
            logger.info("开始调用DeepSeek API...")
            # 调用DeepSeek API
            response = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 2000
                },
                timeout=DEEPSEEK_TIMEOUT
            )
            
            if response.status_code != 200:
                logger.error(f"DeepSeek API请求失败: {response.text}")
                raise HTTPException(status_code=500, detail=f"DeepSeek API请求失败: {response.text}")
            
            analysis = response.json()["choices"][0]["message"]["content"]
            logger.info("成功获取分析结果")
            
        except requests.exceptions.Timeout:
            logger.error(f"DeepSeek API请求超时（{DEEPSEEK_TIMEOUT}秒）")
            raise HTTPException(
                status_code=504,
                detail=f"DeepSeek API请求超时（{DEEPSEEK_TIMEOUT}秒），请稍后重试"
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"调用DeepSeek API时发生错误: {str(e)}")
            raise HTTPException(status_code=500, detail=f"调用DeepSeek API时发生错误: {str(e)}")
        
        return {
            "bazi": bazi,
            "analysis": analysis,
            "knowledge_base": knowledge
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"处理请求时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理请求时发生错误: {str(e)}")

@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "ok", "knowledge_base": "initialized" if kb is not None else "not initialized"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        debug=bool(os.getenv("DEBUG", True))
    ) 