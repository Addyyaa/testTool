# 数据库连接器使用文档

这是一个功能强大的数据库连接器工具，支持 MySQL 和 SQLite 数据库，提供了连接池管理、异常处理、事务管理等功能。

## 功能特点

- 支持 MySQL 和 SQLite 数据库
- 连接池管理（单例模式）
- 自动重连机制
- 完善的异常处理
- 事务管理
- 死锁处理
- 详细的日志记录
- 自动加载环境变量配置

## 快速开始

1. 安装依赖：
```bash
pip install pymysql python-dotenv
```

2. 创建 `.env` 文件，配置数据库信息：
```env
# MySQL配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=your_database
```

3. 直接使用：
```python
from sql_connecter import DatabaseConnectionPool

# 获取连接池实例
pool = DatabaseConnectionPool()

# 直接获取连接（会自动读取.env中的配置）
try:
    with pool.get_connection('mysql') as db:
        results = db.execute(
            "SELECT * FROM users WHERE age > %s",
            (18,)
        )
        print("查询结果:", results)
except Exception as e:
    print(f"错误: {e}")
```

## 配置说明

### 1. 自动配置（推荐）
工具会自动从 `.env` 文件读取配置，你只需要：
1. 创建 `.env` 文件
2. 设置需要的配置项
3. 直接使用 `pool.get_connection('mysql')` 或 `pool.get_connection('sqlite')`

完整的环境变量配置选项：
```env
# MySQL必需配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=your_database

# MySQL可选配置（已有默认值）
MYSQL_CHARSET=utf8mb4
MYSQL_TIMEOUT=5
MYSQL_READ_TIMEOUT=30
MYSQL_WRITE_TIMEOUT=30
MYSQL_DEADLOCK_RETRY_COUNT=3
MYSQL_DEADLOCK_RETRY_DELAY=1
MYSQL_ISOLATION_LEVEL=REPEATABLE READ
MYSQL_LOCK_WAIT_TIMEOUT=50

# SQLite配置
SQLITE_DATABASE=path/to/your/database.db
SQLITE_TIMEOUT=10
```

### 2. 手动配置（可选）
如果需要覆盖环境变量配置，可以手动传入配置：
```python
mysql_config = {
    'host': 'custom_host',
    'port': 3307,
    'user': 'custom_user',
    'password': 'custom_password',
    'database': 'custom_db'
}

with pool.get_connection('mysql', **mysql_config) as db:
    # 使用自定义配置
    pass
```

### 3. 日志配置

日志文件会自动创建在 `logs` 目录下，格式为 `sql_YYYYMMDD_HHMMSS.log`。

## 使用示例

### 1. 基本查询
```python
with pool.get_connection('mysql') as db:
    results = db.execute(
        "SELECT * FROM users WHERE age > %s",
        (18,)
    )
```

### 2. 事务处理
```python
with pool.get_connection('mysql') as db:
    # 自动开始事务
    db.execute(
        "UPDATE users SET status = %s WHERE id = %s",
        ('active', 1)
    )
    db.execute(
        "INSERT INTO logs (user_id, action) VALUES (%s, %s)",
        (1, 'status_update')
    )
    # 事务自动提交
```

### 3. SQLite 使用
```python
with pool.get_connection('sqlite') as db:
    db.execute(
        "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT)"
    )
```

## 异常处理

工具提供了多种异常类型：

- `DatabaseError`: 基础异常类
- `ConnectionError1`: 连接相关异常
- `AuthenticationError`: 认证相关异常
- `QueryError`: 查询相关异常
- `TransactionError`: 事务相关异常
- `PoolError`: 连接池相关异常
- `TimeoutError1`: 超时异常
- `DeadlockError`: 死锁异常
- `ConcurrencyError`: 并发异常
- `DataError`: 数据相关异常
- `IntegrityError`: 完整性约束异常
- `OperationalError`: 数据库操作异常

示例：
```python
try:
    with pool.get_connection('mysql') as db:
        results = db.execute("SELECT * FROM non_existent_table")
except QueryError as e:
    print(f"查询错误: {e}")
except ConnectionError1 as e:
    print(f"连接错误: {e}")
except AuthenticationError as e:
    print(f"认证错误: {e}")
```

## 最佳实践

1. 使用环境变量管理配置：
```python
from dotenv import load_dotenv
import os

load_dotenv()

mysql_config = {
    'host': os.getenv('MYSQL_HOST'),
    'port': int(os.getenv('MYSQL_PORT')),
    # ... 其他配置
}
```

2. 使用上下文管理器（with语句）：
```python
with pool.get_connection('mysql') as db:
    # 自动处理连接的获取和释放
    pass
```

3. 合理使用事务：
```python
with pool.get_connection('mysql') as db:
    # 事务会自动开始和提交/回滚
    pass
```

4. 正确处理异常：
```python
try:
    with pool.get_connection('mysql') as db:
        # 数据库操作
        pass
except DatabaseError as e:
    logging.error(f"数据库错误: {e}")
    # 错误处理
finally:
    pool.close_all()  # 确保连接被正确关闭
```