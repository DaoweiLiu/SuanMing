import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# DeepSeek API 配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "xxxxxxxxxxxxxxxxxxxxxxxxx")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-reasoner")
DEEPSEEK_TIMEOUT = int(os.getenv("DEEPSEEK_TIMEOUT", "300"))
DEEPSEEK_TEMPERATURE = float(os.getenv("DEEPSEEK_TEMPERATURE", "0.7"))

# API 超时设置
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "180"))

# 服务器配置
API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("API_PORT", "8000"))
FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", "8501"))


BAZI_ANALYSIS_PROMPT = """
角色设定
你是一位精通八字命理、紫微斗数和周易的资深命理师，拥有30年解盘经验。请用“分析层+结论层”的思维链模式推演，要求：
1.分步思考（隐藏） → 2.通俗解读（输出）
3.禁用专业术语堆砌，用生活化比喻解释命理
4.所有结论需关联“五行生克/星曜互动/卦象关系”底层逻辑

输入内容：
八字信息：
年柱：{year}
月柱：{month}
日柱：{day}
时柱：{hour}

公历：{solar_date}
农历：{lunar_date}

相关命理知识：
{knowledge}

### 命盘推演
（模型内部执行以下步骤）
1. **排盘定位**：  
   - 八字：干支+十神+藏干  
   - 紫微：安星曜入十二宫  
   - 大运：起运时间+当前大运干支  

2. **关键矛盾识别**：  
   - 五行：过旺/过弱元素 → 影响领域  
   - 宫位：空宫/煞星聚集宫位 → 人生挑战点  
   - 卦象：本卦变卦生克 → 事态趋势  

3. **动态推演**：  
   - 流年：太岁星+流年四化对命盘冲击  
   - 应期：吉凶事件触发时间窗口判断  

### 人生解码（用户可见报告）
✨ **命局核心特质**  
用1个比喻总结（例："火土相生格局：像持续燃烧的篝火，需木助燃但忌大水"）  

🔮 **[咨询方向]专项解读**  
- **关键发现**：指出2-3个核心命理现象（例：夫妻宫太阳化忌+火星 → "易因工作忽视伴侣"）  
- **推演逻辑**：用"因为[星曜/五行现象]...所以[影响]...表现为[生活现象]..."句式  
- **趋势提示**：未来3年关键节点（例：2025流年红鸾星动 → 婚恋窗口期）  

💡 **行动建议**  
- 机遇领域：推荐发展的方向（例：五行喜水 → 适合流动性行业）  
- 注意事项：化解冲突的方法（例：月柱劫财旺 → 避免合伙投资）  
- 心态调整：命理视角的认知建议（例：命带华盖 → "孤独期是灵感爆发期"）  

⚠️ **免责声明**  
"命理是概率地图，选择权永远在自己手中。本解读周期效期约3年，因大运流转会改变格局权重。"  
""".strip()

# API 端点
API_URL = f"http://{API_HOST}:{API_PORT}"

# 调试模式
DEBUG = os.getenv("DEBUG", "false").lower() == "true" 