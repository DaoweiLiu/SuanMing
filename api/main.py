from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import datetime, time
import os
import requests
from dotenv import load_dotenv
from typing import Optional
import logging
from api.knowledge_base import SimpleKnowledgeBase, initialize_knowledge_base
from lunar_python import Lunar, Solar
from datetime import datetime, timedelta
import math
from config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_MODEL,
    DEEPSEEK_TIMEOUT,
    DEEPSEEK_TEMPERATURE,
    FRONTEND_PORT,
    BAZI_ANALYSIS_PROMPT
)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

app = FastAPI()

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"http://localhost:{FRONTEND_PORT}", f"http://127.0.0.1:{FRONTEND_PORT}"],
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
    birth_time: time = Field(..., description="出生时间，格式为 HH:MM")
    latitude: float = Field(..., description="出生地纬度")
    longitude: float = Field(..., description="出生地经度")
    is_lunar: bool = False
    gender: str = Field(..., description="性别，'男'或'女'")

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

def beijing_time_to_local_time(dt: datetime, longitude: float) -> datetime:
    """将北京时间转换为当地时间
    
    Args:
        dt: 北京时间
        longitude: 当地经度（东经为正，西经为负）
    
    Returns:
        当地时间
    """
    # 北京经度
    BEIJING_LONGITUDE = 116.4074
    
    # 计算经度差（当地经度 - 北京经度）
    longitude_diff = longitude - BEIJING_LONGITUDE
    
    # 计算时差（分钟）：每经度4分钟
    time_diff_minutes = longitude_diff * 4
    
    # 调整时间
    local_time = dt + timedelta(minutes=time_diff_minutes)
    return local_time

def get_gz_hour(hour: int, minute: int) -> tuple:
    """根据当地时间获取时辰的干支"""
    # 将小时和分钟转换为小时的小数形式
    decimal_hour = hour + minute / 60.0
    
    # 12时辰对应的时间范围（使用小数形式的小时）
    hour_ranges = {
        0: (23, 1),    # 子时 (23:00-01:00)
        1: (1, 3),     # 丑时 (01:00-03:00)
        2: (3, 5),     # 寅时 (03:00-05:00)
        3: (5, 7),     # 卯时 (05:00-07:00)
        4: (7, 9),     # 辰时 (07:00-09:00)
        5: (9, 11),    # 巳时 (09:00-11:00)
        6: (11, 13),   # 午时 (11:00-13:00)
        7: (13, 15),   # 未时 (13:00-15:00)
        8: (15, 17),   # 申时 (15:00-17:00)
        9: (17, 19),   # 酉时 (17:00-19:00)
        10: (19, 21),  # 戌时 (19:00-21:00)
        11: (21, 23)   # 亥时 (21:00-23:00)
    }
    
    # 处理跨午夜的情况
    if decimal_hour >= 23 or decimal_hour < 1:
        return 0  # 子时
    
    # 确定时辰
    for branch_index, (start, end) in hour_ranges.items():
        if start <= decimal_hour < end:
            return branch_index
    
    return 0  # 默认返回子时

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
        if not (-90 <= birth_info.latitude <= 90):
            raise ValueError("纬度必须在-90到90度之间")
        if not (-180 <= birth_info.longitude <= 180):
            raise ValueError("经度必须在-180到180度之间")

        # 如果是农历，转换为公历
        year, month, day = (
            convert_lunar_to_solar(birth_info.year, birth_info.month, birth_info.day)
            if birth_info.is_lunar
            else (birth_info.year, birth_info.month, birth_info.day)
        )

        # 创建北京时间datetime对象
        beijing_datetime = datetime(
            year, month, day,
            birth_info.birth_time.hour,
            birth_info.birth_time.minute
        )
        
        # 转换为当地时间
        local_datetime = beijing_time_to_local_time(
            beijing_datetime,
            birth_info.longitude
        )
        
        # 获取当地时间的时辰
        hour_branch_index = get_gz_hour(
            local_datetime.hour,
            local_datetime.minute
        )

        # 使用lunar-python计算八字
        solar = Solar.fromYmd(year, month, day)
        lunar = solar.getLunar()
        
        # 获取年月日的干支
        year_gz = lunar.getYearInGanZhi()
        month_gz = lunar.getMonthInGanZhi()
        day_gz = lunar.getDayInGanZhi()
        
        # 计算时柱干支
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
            "lunar_date": f"{lunar.getYearInChinese()}年{lunar.getMonthInChinese()}月{lunar.getDayInChinese()}",
            "local_time": local_datetime.strftime("%H:%M")
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
        prompt = BAZI_ANALYSIS_PROMPT.format(
            year=bazi['year'],
            month=bazi['month'],
            day=bazi['day'],
            hour=bazi['hour'],
            solar_date=bazi['solar_date'],
            lunar_date=bazi['lunar_date'],
            gender=birth_info.gender,
            knowledge=knowledge
        )
        
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
                    "model": DEEPSEEK_MODEL,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": DEEPSEEK_TEMPERATURE
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