import os
import json
import sqlite3
from dotenv import load_dotenv
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.agents import ChatAgent
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Text2SQL")
logger.setLevel(logging.INFO)


class Text2SQL:
    def __init__(self):
        """初始化PlanAgent"""
        self.load_env()
        self.load_config()
        self.init_agent()
        self.DB_PATH = "database/sensor_data.db"
    def load_env(self):
        """加载环境变量"""
        load_dotenv(dotenv_path=".env")
        os.environ["TOKENIZERS_PARALLELISM"] = "false" 
        self.api_key = os.getenv("GPT_API_KEY")
        if not self.api_key:
            raise ValueError("API_KEY 未在 .env 文件中设置")
        os.environ["OPENAI_API_KEY"] = self.api_key

    def load_config(self):
        """加载配置文件"""
        with open("utils/config.json", "r", encoding="utf-8") as f:
            self.config = json.load(f)     

    def init_agent(self):
        """初始化ChatAgent"""
        self.agent = ChatAgent(
            system_message="You are a data analyst. Your job is to assist users with their business questions by querying the data contained in a SQL database.",
            model=ModelFactory.create(
                model_platform=ModelPlatformType.OPENAI,
                model_type=ModelType.GPT_4O_MINI,
                api_key=self.api_key,
                model_config_dict={"temperature": 0.4, "max_tokens": 4096},
            )
        )        
        # self.conn = pymysql.connect()

    def text2sql(self, query):
        if not query or not query.strip():
            return None
        use_msg = f"""你是一个sql语句生成专家，目的是根据用户的问题生成sql语句。
已知数据库结构：
表名：sensor_data
字段里的内容格式为：
"timestamp":2025-06-13 18:39:33,
"oxygen_saturation":6.411097526550293,
"water_level":513,
"ph":7.59,
"ph_temp":24.1,
"turbidity":100,
"turbidity_temp":24.1

以下是示例：
<example>
问题: 请查询所有ph值大于8的数据
答案:
SELECT * FROM sensor_data WHERE ph > 8
问题: 请查询六月十三号的ph值
答案:
SELECT ph FROM sensor_data WHERE timestamp BETWEEN '2025-06-13 00:00:00' AND '2025-06-13 23:59:59'
</example>

    •请根据以下自然语言生成SQL语句，严格遵循SQL语法并且可以直接使用，不要添加任何其他内容，字符串开头不能有sql
    •强调：关于时间的查询名称为timestamp，格式为2025-06-13 18:39:33，在检索的时候需要注意对日期和时间的准确处理，比如查询六月十三号十八点四十到十八点四十一的ph值，需要写成WHERE timestamp BETWEEN '2025-06-13 18:40:00' AND '2025-06-13 18:41:00'
问题：{query}
答案：
"""       
        response = self.agent.step(use_msg)
        content = response.msg.content            
        SQL_query = content
        logger.info(f"生成的SQL语句是：{SQL_query}")
        return SQL_query
    
    def query_sensor_data(self, query) -> str:
        try:
            sql = self.text2sql(query)
            if not sql:
                logger.info("无法生成有效的SQL查询")
                return "无法生成有效的SQL查询"

            conn = sqlite3.connect(self.DB_PATH)
            cur = conn.cursor()
            cur.execute(sql)
            results = cur.fetchall()
            conn.close()

            if not results:
                logger.info("无相关数据")
                return "无相关数据"


            if "*" in sql or "oxygen_saturation" in sql:
                result_lines = []
                for r in results:

                    timestamp = f"{r[1]}" if r[1] is not None else "N/A"
                    oxygen = f"{r[2]}" if r[2] is not None else "N/A"
                    water_level = f"{r[3]}" if r[3] is not None else "N/A"
                    ph = f"{r[4]}" if r[4] is not None else "N/A"
                    ph_temp = f"{r[5]}" if r[5] is not None else "N/A"
                    turbidity = f"{r[6]}" if r[6] is not None else "N/A"
                    turbidity_temp = f"{r[7]}" if r[7] is not None else "N/A"
                    
                    line = f"{timestamp} | 溶解氧: {oxygen} | 液位: {water_level} mm | PH: {ph} | PH温度: {ph_temp}°C | 浊度: {turbidity} NTU | 浊度温度: {turbidity_temp}°C"
                    result_lines.append(line)
                return "\n".join(result_lines)
            else:

                simple_values = [str(r[0]) for r in results]
                return "查询结果：\n" + "\n".join(simple_values)

        except Exception as e:
            logger.error(f"查询出错: {str(e)}")
            return f"查询出错: {str(e)}"