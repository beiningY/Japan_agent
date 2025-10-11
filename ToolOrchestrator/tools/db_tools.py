import asyncio
import aiomysql
import logging
from datetime import datetime, date
from decimal import Decimal
from utils.logger import get_logger

logger = get_logger(__name__)

DB_CONFIG = {
    "host": "rm-0iwx9y9q368yc877wbo.mysql.japan.rds.aliyuncs.com",
    "user": "root",
    "password": "Root155017",
    "db": "cognitive"
}

def convert_to_json_serializable(obj):
    """将数据库查询结果中的特殊类型转换为JSON可序列化的类型"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, bytes):
        return obj.decode('utf-8', errors='ignore')
    elif isinstance(obj, dict):
        return {k: convert_to_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_to_json_serializable(item) for item in obj]
    else:
        return obj

async def list_sql_tables() -> dict:
    """列出数据库中所有表名"""
    conn = None
    logger.info("调用工具: list_sql_tables()")
    try:
        conn = await aiomysql.connect(**DB_CONFIG)
        async with conn.cursor() as cursor:
            await cursor.execute("SHOW TABLES;")
            result = await cursor.fetchall()
            tables = [row[0] for row in result]
            logger.info(f"✅ 查询到的表: {tables}")
            return {"tables": tables}
    except Exception as e:
        logger.error(f"❌ list_sql_tables 出错: {e}", exc_info=True)
        return {"error": f"数据库连接失败: {str(e)}"}
    finally:
        if conn:
            conn.close()
            logger.debug("数据库连接已关闭。")

async def get_tables_schema(table_names: list) -> dict:
    """获取指定表的字段结构"""
    conn = None
    logger.info(f"调用工具: get_tables_schema(table_names={table_names})")
    try:
        conn = await aiomysql.connect(**DB_CONFIG)
        async with conn.cursor() as cursor:
            result = {}
            for table in table_names:
                logger.debug(f"正在获取表结构: {table}")
                await cursor.execute(f"DESCRIBE {table};")
                schema = await cursor.fetchall()
                result[table] = schema
            
            # 转换为JSON可序列化的格式
            serializable_result = convert_to_json_serializable(result)
            
            logger.info(f"✅ 查询到的表结构: {list(serializable_result.keys())}")
            return {"schemas": serializable_result}
    except Exception as e:
        logger.error(f"❌ get_tables_schema 出错: {e}", exc_info=True)
        return {"error": f"数据库连接失败: {str(e)}"}
    finally:
        if conn:
            conn.close()
            logger.debug("数据库连接已关闭。")

async def read_sql_query(table_queries: list) -> dict:
    """执行多条 SQL 查询语句并返回结果"""
    conn = None
    logger.info(f"调用工具: read_sql_query(table_queries={table_queries})")
    try:
        conn = await aiomysql.connect(**DB_CONFIG)
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            results = []
            for item in table_queries:
                query = item.get("query")
                logger.info(f"执行 SQL 查询: {query}")
                if not query:
                    msg = "缺少 query 字段"
                    logger.warning(f"⚠️ {msg}")
                    results.append({"error": msg})
                    continue
                try:
                    await cursor.execute(query)
                    rows = await cursor.fetchall()
                    logger.info(f"✅ 查询成功: 返回 {len(rows)} 条记录")
                    
                    # 转换为JSON可序列化的格式
                    serializable_rows = convert_to_json_serializable(rows)
                    
                    results.append({"query": query, "rows": serializable_rows})
                except Exception as e:
                    logger.error(f"❌ 执行 SQL 出错: {query} | 错误: {e}", exc_info=True)
                    results.append({"query": query, "error": str(e)})
            logger.info(f"📦 查询结果汇总: {results}")
            return {"results": results}
    except Exception as e:
        logger.error(f"❌ read_sql_query 出错: {e}", exc_info=True)
        return {"error": f"数据库连接失败: {str(e)}"}
    finally:
        if conn:
            conn.close()
            logger.debug("数据库连接已关闭。")
