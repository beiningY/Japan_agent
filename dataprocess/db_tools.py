
import asyncio
import aiomysql
import logging
logger = logging.getLogger("db_tools")
logger.setLevel(logging.INFO)

DB_CONFIG = {
    "host": "rm-0iwx9y9q368yc877wbo.mysql.japan.rds.aliyuncs.com",
    "user": "root",
    "password": "Root155017",
    "db": "cognitive"
}
async def list_sql_tables() -> dict:

    conn = None  
    try:
        conn = await aiomysql.connect(**DB_CONFIG)
        async with conn.cursor() as cursor:
            await cursor.execute("SHOW TABLES;")
            result = await cursor.fetchall()
            tables = [row[0] for row in result]
            print(f"查询到的表: {tables}")
            return {"tables": tables}
    except Exception as e:
        return {"error": f"数据库连接失败: {str(e)}"}
    finally:
        if conn:
            conn.close() 

async def get_tables_schema(table_names: list) -> dict:
    conn = None
    try:
        conn = await aiomysql.connect(**DB_CONFIG)
        async with conn.cursor() as cursor:
            result = {}
            for table in table_names:
                await cursor.execute(f"DESCRIBE {table};")
                schema = await cursor.fetchall()
                result[table] = schema
            print(f"查询到的表结构: {result}")
            return {"schemas": result}
    except Exception as e:
        return {"error": f"数据库连接失败: {str(e)}"}
    finally:
        if conn:
            conn.close() 

async def read_sql_query(table_queries: list) -> dict:
    conn = None
    try:
        conn = await aiomysql.connect(**DB_CONFIG)
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            results = []
            for item in table_queries: 
                query = item.get("query")
                if not query:
                    results.append({"error": "缺少 query 字段"})
                    continue
                try:
                    await cursor.execute(query)
                    rows = await cursor.fetchall()
                    results.append({"query": query, "rows": rows})
                except Exception as e:
                    results.append({"query": query, "error": str(e)})
            print(f"查询结果: {results}")
            return {"results": results}
    except Exception as e:
        return {"error": f"数据库连接失败: {str(e)}"}
    finally:
        if conn:
            conn.close()
