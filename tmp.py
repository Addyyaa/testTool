#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import logging
import asyncio
import time
from dotenv import load_dotenv
from sql_connecter import DatabaseConnectionPool

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(module)s:%(filename)s:%(lineno)d - %(funcName)s() - %(message)s',
    handlers=[
        logging.FileHandler("sql_test.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# 创建.env文件（如果不存在）
def create_env_file():
    """创建示例.env文件（如果不存在）"""
    if not os.path.exists('.env'):
        with open('.env', 'w', encoding='utf-8') as f:
            f.write("""# MySQL配置
MYSQL_HOST=139.224.192.36
MYSQL_PORT=3405
MYSQL_USER=root
MYSQL_PASSWORD=your_password_here
MYSQL_DATABASE=your_database_here
MYSQL_CHARSET=utf8mb4
MYSQL_TIMEOUT=30
MYSQL_READ_TIMEOUT=30
MYSQL_WRITE_TIMEOUT=30
MYSQL_DEADLOCK_RETRY_COUNT=3
MYSQL_DEADLOCK_RETRY_DELAY=1
MYSQL_ISOLATION_LEVEL=REPEATABLE READ
MYSQL_LOCK_WAIT_TIMEOUT=50
MYSQL_PROGRAM_NAME=TestApplication
""")
        logging.info("已创建示例.env文件，请修改其中的配置")
        return False
    return True

class DBTester:
    """数据库测试类"""
    _db_pool = None  # 类级别的数据库连接池

    @classmethod
    def get_db_pool(cls):
        """获取或初始化数据库连接池"""
        if cls._db_pool is None:
            cls._db_pool = DatabaseConnectionPool()
        return cls._db_pool

    @classmethod
    def query_sql(cls, sql: str, params: tuple = None) -> list:
        """执行SQL查询"""
        try:
            # 获取MySQL连接
            with cls.get_db_pool().get_connection('mysql') as db:
                # 执行SQL
                results = db.execute(sql, params) if params else db.execute(sql)
                return results
        except Exception as e:
            logging.error(f"数据库查询出错: {str(e)}")
            # 不要抛出异常，返回空结果
            return []

    @classmethod
    def test_connection(cls):
        """测试数据库连接"""
        # 简单的SELECT测试
        logging.info("执行简单的SELECT 1测试...")
        result = cls.query_sql("SELECT 1 AS test")
        if result and isinstance(result, list) and len(result) > 0:
            logging.info(f"连接测试成功: {result}")
        else:
            logging.error("连接测试失败: 无法获取结果")
        return result

    @classmethod
    def test_update(cls):
        """测试UPDATE语句"""
        # 确保表存在
        try:
            logging.info("测试UPDATE语句...")
            # 使用安全的参数化查询
            device_id = "PS04testLtest01"
            status = 1
            
            # 尝试查询记录是否存在
            select_sql = "SELECT * FROM t_ota_upgrade_record WHERE device_id = %s"
            result = cls.query_sql(select_sql, (device_id,))
            
            if result:
                # 更新记录
                update_sql = "UPDATE t_ota_upgrade_record SET status = %s WHERE device_id = %s"
                update_result = cls.query_sql(update_sql, (status, device_id))
                logging.info(f"更新结果: {update_result}")
            else:
                # 插入记录
                insert_sql = "INSERT INTO t_ota_upgrade_record (device_id, status) VALUES (%s, %s)"
                insert_result = cls.query_sql(insert_sql, (device_id, status))
                logging.info(f"插入结果: {insert_result}")
                
            return True
        except Exception as e:
            logging.error(f"UPDATE测试失败: {e}")
            return False

def main():
    """主函数"""
    # 确保.env文件存在
    if not create_env_file():
        return
    
    # 加载环境变量
    load_dotenv()
    
    # 启动测试
    logging.info("开始数据库连接测试...")
    
    # 测试连接
    connection_result = DBTester.test_connection()
    
    if connection_result:
        # 测试UPDATE
        DBTester.test_update()
    
    logging.info("数据库测试完成")

if __name__ == "__main__":
    main()
