import logging
import os
from typing import Any, Dict, Optional, Union
from abc import ABC, abstractmethod
import pymysql
import sqlite3
import threading
from datetime import datetime
import socket
import time
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

# 配置日志
if not os.path.exists('logs'):
    os.makedirs('logs')

log_filename = os.path.join('logs', f'sql_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(module)s:%(filename)s:%(lineno)d - %(funcName)s() - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()
    ]
)


class DatabaseError(Exception):
    """数据库基础异常类"""

    def __init__(self, message: str, error_code: int = None, original_error: Exception = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.original_error = original_error
        self.timestamp = datetime.now()

    def __str__(self):
        error_info = f"[{self.timestamp}] {self.__class__.__name__}: {self.message}"
        if self.error_code:
            error_info += f" (错误代码: {self.error_code})"
        if self.original_error:
            error_info += f"\n原始错误: {str(self.original_error)}"
        return error_info


class ConnectionError1(DatabaseError):
    """连接相关异常"""

    def __init__(self, message: str, error_code: int = None, original_error: Exception = None, host: str = None,
                 port: int = None):
        super().__init__(message, error_code, original_error)
        self.host = host
        self.port = port

    def __str__(self):
        error_info = super().__str__()
        if self.host:
            error_info += f"\n连接信息: {self.host}"
            if self.port:
                error_info += f": {self.port}"
        return error_info


class AuthenticationError(ConnectionError1):
    """认证相关异常"""

    def __init__(self, message: str, error_code: int = None, original_error: Exception = None, user: str = None):
        super().__init__(message, error_code, original_error)
        self.user = user

    def __str__(self):
        error_info = super().__str__()
        if self.user:
            error_info += f"\n用户: {self.user}"
        return error_info


class QueryError(DatabaseError):
    """查询相关异常"""

    def __init__(self, message: str, error_code: int = None, original_error: Exception = None, query: str = None):
        super().__init__(message, error_code, original_error)
        self.query = query

    def __str__(self):
        error_info = super().__str__()
        if self.query:
            error_info += f"\n问题查询: {self.query}"
        return error_info


class TransactionError(DatabaseError):
    """事务相关异常"""

    def __init__(self, message: str, error_code: int = None, original_error: Exception = None,
                 transaction_id: str = None):
        super().__init__(message, error_code, original_error)
        self.transaction_id = transaction_id

    def __str__(self):
        error_info = super().__str__()
        if self.transaction_id:
            error_info += f"\n事务ID: {self.transaction_id}"
        return error_info


class PoolError(DatabaseError):
    """连接池相关异常"""

    def __init__(self, message: str, error_code: int = None, original_error: Exception = None, pool_size: int = None):
        super().__init__(message, error_code, original_error)
        self.pool_size = pool_size

    def __str__(self):
        error_info = super().__str__()
        if self.pool_size is not None:
            error_info += f"\n连接池大小: {self.pool_size}"
        return error_info


class TimeoutError1(DatabaseError):
    """超时异常"""

    def __init__(self, message: str, error_code: int = None, original_error: Exception = None,
                 timeout_seconds: float = None):
        super().__init__(message, error_code, original_error)
        self.timeout_seconds = timeout_seconds

    def __str__(self):
        error_info = super().__str__()
        if self.timeout_seconds is not None:
            error_info += f"\n超时时间: {self.timeout_seconds}秒"
        return error_info


class DeadlockError(DatabaseError):
    """死锁异常"""

    def __init__(self, message: str, error_code: int = None, original_error: Exception = None, waiting_for: str = None,
                 held_by: str = None):
        super().__init__(message, error_code, original_error)
        self.waiting_for = waiting_for
        self.held_by = held_by

    def __str__(self):
        error_info = super().__str__()
        if self.waiting_for:
            error_info += f"\n等待资源: {self.waiting_for}"
        if self.held_by:
            error_info += f"\n资源持有者: {self.held_by}"
        return error_info


class ConcurrencyError(DatabaseError):
    """并发异常"""

    def __init__(self, message: str, error_code: int = None, original_error: Exception = None,
                 conflict_resource: str = None):
        super().__init__(message, error_code, original_error)
        self.conflict_resource = conflict_resource

    def __str__(self):
        error_info = super().__str__()
        if self.conflict_resource:
            error_info += f"\n冲突资源: {self.conflict_resource}"
        return error_info


class DataError(DatabaseError):
    """数据相关异常"""

    def __init__(self, message: str, error_code: int = None, original_error: Exception = None,
                 invalid_value: Any = None):
        super().__init__(message, error_code, original_error)
        self.invalid_value = invalid_value

    def __str__(self):
        error_info = super().__str__()
        if self.invalid_value is not None:
            error_info += f"\n无效数据: {self.invalid_value}"
        return error_info


class IntegrityError(DatabaseError):
    """完整性约束异常"""

    def __init__(self, message: str, error_code: int = None, original_error: Exception = None,
                 constraint_name: str = None):
        super().__init__(message, error_code, original_error)
        self.constraint_name = constraint_name

    def __str__(self):
        error_info = super().__str__()
        if self.constraint_name:
            error_info += f"\n约束名称: {self.constraint_name}"
        return error_info


class OperationalError(DatabaseError):
    """数据库操作异常"""

    def __init__(self, message: str, error_code: int = None, original_error: Exception = None, operation: str = None):
        super().__init__(message, error_code, original_error)
        self.operation = operation

    def __str__(self):
        error_info = super().__str__()
        if self.operation:
            error_info += f"\n操作: {self.operation}"
        return error_info


def format_error_message(e1: Exception, context: str = None) -> str:
    """格式化错误信息"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    error_type = type(e1).__name__
    error_msg = str(e1)

    if context:
        return f"[{timestamp}] {context} - {error_type}: {error_msg}"
    return f"[{timestamp}] {error_type}: {error_msg}"


class DatabaseConnectionPool:
    """数据库连接池 - 单例模式"""
    _instance = None
    _lock = threading.Lock()
    _pools: Dict[str, 'DatabaseConnector'] = {}
    _active_connections = set()  # 跟踪活动连接
    _max_retries = 3
    _retry_delay = 1
    _cleanup_threshold = 100  # 连接数量达到阈值时触发清理
    
    # 添加默认配置，从环境变量读取
    _default_mysql_config = {
        'host': os.getenv('MYSQL_HOST', 'localhost'),
        'port': int(os.getenv('MYSQL_PORT', '3306')),
        'user': os.getenv('MYSQL_USER', 'root'),
        'password': os.getenv('MYSQL_PASSWORD', ''),
        'database': os.getenv('MYSQL_DATABASE', ''),
        'charset': os.getenv('MYSQL_CHARSET', 'utf8mb4'),
        'timeout': int(os.getenv('MYSQL_TIMEOUT', '5')),
        'read_timeout': int(os.getenv('MYSQL_READ_TIMEOUT', '30')),
        'write_timeout': int(os.getenv('MYSQL_WRITE_TIMEOUT', '30')),
        'deadlock_retry_count': int(os.getenv('MYSQL_DEADLOCK_RETRY_COUNT', '3')),
        'deadlock_retry_delay': int(os.getenv('MYSQL_DEADLOCK_RETRY_DELAY', '1')),
        'isolation_level': os.getenv('MYSQL_ISOLATION_LEVEL', 'REPEATABLE READ'),
        'lock_wait_timeout': int(os.getenv('MYSQL_LOCK_WAIT_TIMEOUT', '50')),
        'program_name': os.getenv('MYSQL_PROGRAM_NAME', 'Application')
    }
    
    _default_sqlite_config = {
        'database': os.getenv('SQLITE_DATABASE', ':memory:'),
        'timeout': float(os.getenv('SQLITE_TIMEOUT', '5.0')),
        'isolation_level': os.getenv('SQLITE_ISOLATION_LEVEL', None)
    }

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(DatabaseConnectionPool, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # 5分钟清理一次

    def _cleanup_expired_connections(self):
        """清理过期连接"""
        current_time = time.time()
        if current_time - self._last_cleanup > self._cleanup_interval:
            with self._lock:
                for conn in list(self._active_connections):
                    if not conn.is_active():
                        try:
                            conn.disconnect()
                        except Exception as e:
                            logging.warning(f"清理过期连接失败: {e}")
                        self._active_connections.remove(conn)
            self._last_cleanup = current_time

    def get_connection(self, db_type: str, **kwargs) -> 'DatabaseConnector':
        """获取数据库连接
        
        自动从环境变量加载默认配置，调用时可覆盖特定参数
        
        Args:
            db_type: 数据库类型 ('mysql' 或 'sqlite')
            **kwargs: 可选的连接参数，会覆盖默认配置
            
        Returns:
            数据库连接器实例
        """
        try:
            # 检查并清理过期连接
            if len(self._active_connections) > self._cleanup_threshold:
                self._cleanup_expired_connections()

            # 根据数据库类型选择默认配置
            if db_type.lower() == 'mysql':
                default_config = self._default_mysql_config.copy()
            elif db_type.lower() == 'sqlite':
                default_config = self._default_sqlite_config.copy()
            else:
                default_config = {}
            
            # 使用传入的参数更新默认配置
            config = default_config.copy()
            config.update(kwargs)
            
            # 使用更新后的配置构建连接池键
            pool_key = f"{db_type}_{config.get('host', 'localhost')}_{config.get('database', 'default')}"

            if pool_key not in self._pools:
                with self._lock:
                    if pool_key not in self._pools:
                        for attempt in range(self._max_retries):
                            try:
                                connector = DatabaseFactory.create_database(db_type, **config)
                                self._pools[pool_key] = connector
                                self._active_connections.add(connector)
                                break
                            except (ConnectionError1, socket.error) as e:
                                if attempt == self._max_retries - 1:
                                    raise ConnectionError1(f"无法建立数据库连接: {str(e)}")
                                logging.warning(f"连接尝试 {attempt + 1}/{self._max_retries} 失败: {str(e)}")
                                time.sleep(self._retry_delay * (attempt + 1))
                            except Exception as e:
                                raise PoolError(f"创建连接池失败: {str(e)}")

            connector = self._pools[pool_key]
            if not connector.is_active():
                connector.connect()
            return connector

        except Exception as e:
            logging.error(f"获取数据库连接失败: {str(e)}", exc_info=True)
            raise

    def close_all(self):
        """关闭所有连接"""
        errors = []
        with self._lock:
            for key, pool in list(self._pools.items()):
                try:
                    pool.disconnect()
                    self._active_connections.remove(pool)
                    del self._pools[key]
                except Exception as e:
                    errors.append(f"关闭连接 {key} 失败: {str(e)}")

        if errors:
            raise PoolError("关闭连接池时发生错误: " + "; ".join(errors))

    def __del__(self):
        """析构函数，确保所有连接被关闭"""
        try:
            self.close_all()
        except Exception as e:
            logging.error(f"关闭连接池失败: {e}")


class DatabaseConnector(ABC):
    """抽象数据库连接器基类"""

    def __init__(self, **kwargs):
        self.connection = None
        self.cursor = None
        self.config = kwargs
        self._lock = threading.Lock()
        self._transaction_level = 0
        self._max_reconnect_attempts = 3
        self._reconnect_delay = 1
        self._timeout = int(kwargs.get('timeout', 30))
        self._deadlock_retry_count = kwargs.get('deadlock_retry_count', 3)
        self._deadlock_retry_delay = kwargs.get('deadlock_retry_delay', 1)
        self._last_active = time.time()
        self._max_idle_time = kwargs.get('max_idle_time', 3600)  # 1小时
        self.sql_templates = {}  # SQL模板存储

    def is_active(self) -> bool:
        """检查连接是否活跃"""
        if not self.connection or not self.cursor:
            return False
        if time.time() - self._last_active > self._max_idle_time:
            return False
        try:
            self.cursor.execute("SELECT 1")
            self._last_active = time.time()
            return True
        except Exception:
            return False

    def load_sql_template(self, name: str, sql: str) -> None:
        """加载SQL模板"""
        self.sql_templates[name] = sql

    def load_sql_from_file(self, file_path: str) -> None:
        """从文件加载SQL模板"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            # 简单的SQL解析，按分号分割
            sql_statements = [s.strip() for s in content.split(';') if s.strip()]
            for i, sql in enumerate(sql_statements):
                name = f"sql_{i+1}"
                if sql.startswith('-- name:'):
                    # 支持命名SQL：-- name: get_users
                    name = sql[8:sql.find('\n')].strip()
                    sql = sql[sql.find('\n'):].strip()
                self.sql_templates[name] = sql
        except Exception as e:
            raise DatabaseError(f"加载SQL文件失败: {str(e)}")

    def execute_template(self, template_name: str, params: Optional[Union[tuple, list, dict]] = None) -> Any:
        """执行SQL模板"""
        if template_name not in self.sql_templates:
            raise QueryError(f"SQL模板 '{template_name}' 不存在")
        return self.execute(self.sql_templates[template_name], params)

    @abstractmethod
    def connect(self) -> None:
        """建立数据库连接"""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """断开数据库连接"""
        pass

    def _ensure_connected(self):
        """确保数据库连接可用"""
        try:
            if not self.connection or not self.cursor:
                self.connect()
                return

            # 测试连接是否有效
            try:
                self.cursor.execute("SELECT 1")
            except Exception:
                logging.warning("数据库连接已断开，尝试重新连接")
                self.connect()

        except Exception as e:
            logging.error(f"确保数据库连接时发生错误: {str(e)}", exc_info=True)
            raise ConnectionError1(f"无法确保数据库连接: {str(e)}")

    def _handle_operational_error(self, e: Exception, context: str) -> None:
        """处理操作性错误"""
        error_msg = format_error_message(e, context)
        if "timeout" in str(e).lower():
            raise TimeoutError1(error_msg, original_error=e)
        elif "deadlock" in str(e).lower():
            raise DeadlockError(error_msg, original_error=e)
        elif "lock wait timeout" in str(e).lower():
            raise ConcurrencyError(error_msg, original_error=e)
        else:
            raise OperationalError(error_msg, original_error=e)

    def _handle_data_error(self, e: Exception, context: str) -> None:
        """处理数据错误"""
        error_msg = format_error_message(e, context)
        if "foreign key constraint" in str(e).lower():
            raise IntegrityError(error_msg, original_error=e)
        elif "duplicate entry" in str(e).lower():
            raise IntegrityError(error_msg, original_error=e)
        else:
            raise DataError(error_msg, original_error=e)

    def execute(self, sql: str, params: Optional[Union[tuple, list, dict]] = None) -> Any:
        """执行SQL语句"""
        with self._lock:
            last_error = None
            deadlock_retries = self._deadlock_retry_count

            while deadlock_retries > 0:
                try:
                    for attempt in range(self._max_reconnect_attempts):
                        try:
                            self._ensure_connected()

                            # 检查SQL语句
                            if not sql.strip():
                                raise QueryError("SQL语句不能为空")

                            logging.debug(f"执行SQL: {sql}, 参数: {params}")

                            # 设置语句超时
                            if hasattr(self.cursor, 'execute'):
                                try:
                                    timeout_ms = int(self._timeout * 1000)
                                    self.cursor.execute("SET SESSION MAX_EXECUTION_TIME = %s", (timeout_ms,))
                                except Exception as e:
                                    logging.warning(f"设置查询超时失败: {e}")

                            # 执行SQL
                            if params:
                                self.cursor.execute(sql, params)
                            else:
                                self.cursor.execute(sql)

                            # 处理结果
                            if sql.strip().upper().startswith(('SELECT', 'SHOW')):
                                result = self.cursor.fetchall()
                                logging.debug(f"查询结果: {result}")
                                return result
                            else:
                                if self._transaction_level == 0:
                                    self.connection.commit()
                                affected_rows = self.cursor.rowcount
                                logging.debug(f"影响行数: {affected_rows}")
                                return affected_rows

                        except (pymysql.Error, sqlite3.Error) as e:
                            last_error = e
                            error_msg = str(e).lower()

                            # 处理死锁
                            if "deadlock" in error_msg:
                                if deadlock_retries > 1:
                                    deadlock_retries -= 1
                                    logging.warning(f"检测到死锁，等待 {self._deadlock_retry_delay} 秒后重试")
                                    time.sleep(self._deadlock_retry_delay)
                                    break  # 跳出内层循环，重试整个事务
                                else:
                                    self._handle_operational_error(e, "死锁重试次数已用完")

                            # 处理连接问题
                            if any(err in error_msg for err in ["gone away", "lost connection", "broken pipe"]):
                                if attempt < self._max_reconnect_attempts - 1:
                                    logging.warning(f"数据库连接断开，第 {attempt + 1} 次重试")
                                    time.sleep(self._reconnect_delay * (attempt + 1))
                                    continue

                            # 处理其他数据库错误
                            if "duplicate" in error_msg or "foreign key" in error_msg:
                                self._handle_data_error(e, "数据完整性错误")
                            elif "timeout" in error_msg:
                                self._handle_operational_error(e, "查询超时")
                            else:
                                raise QueryError(f"SQL执行错误: {str(e)}", original_error=e)

                        except Exception as e:
                            last_error = e
                            if attempt < self._max_reconnect_attempts - 1:
                                logging.warning(f"执行错误，第 {attempt + 1} 次重试: {str(e)}")
                                time.sleep(self._reconnect_delay * (attempt + 1))
                                continue
                            raise

                    # 如果执行到这里，说明重试成功
                    break

                except DeadlockError:
                    if deadlock_retries > 1:
                        deadlock_retries -= 1
                        continue
                    raise

            if last_error:
                if self.connection and self._transaction_level > 0:
                    self.connection.rollback()
                logging.error(f"SQL执行失败: {str(last_error)}", exc_info=True)
                raise QueryError(f"SQL执行失败: {str(last_error)}", original_error=last_error)

    def begin_transaction(self):
        """开始事务"""
        try:
            with self._lock:
                self._ensure_connected()
                if self._transaction_level == 0:
                    if hasattr(self.connection, 'begin'):
                        self.connection.begin()
                    else:
                        self.execute("BEGIN TRANSACTION")
                self._transaction_level += 1
        except Exception as e:
            self._handle_operational_error(e, "开始事务失败")

    def commit(self):
        """提交事务"""
        try:
            with self._lock:
                if self._transaction_level > 0:
                    self._transaction_level -= 1
                    if self._transaction_level == 0:
                        try:
                            self.connection.commit()
                        except Exception as e:
                            self.rollback()
                            self._handle_operational_error(e, "提交事务失败")
        except Exception as e:
            raise TransactionError(f"提交事务失败: {str(e)}", original_error=e)

    def rollback(self):
        """回滚事务"""
        try:
            with self._lock:
                if self._transaction_level > 0:
                    self._transaction_level = 0
                    self.connection.rollback()
        except Exception as e:
            raise TransactionError(f"回滚事务失败: {str(e)}", original_error=e)

    def __enter__(self):
        """上下文管理器入口"""
        self.begin_transaction()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        if exc_type:
            self.rollback()
            logging.error(f"执行出错: {exc_val}", exc_info=True)
        else:
            try:
                self.commit()
            except Exception as e:
                self.rollback()
                raise TransactionError(f"提交事务失败: {str(e)}")


class MySQLConnector(DatabaseConnector):
    """MySQL连接器"""

    def connect(self) -> None:
        try:
            if self.connection:
                try:
                    self.connection.ping(reconnect=True)
                    return
                except Exception:
                    self.disconnect()

            self.connection = pymysql.connect(
                host=self.config.get('host', 'localhost'),
                port=int(self.config.get('port', 3306)),
                user=self.config.get('user', 'root'),
                password=self.config.get('password', ''),
                database=self.config.get('database', ''),
                charset=self.config.get('charset', 'utf8mb4'),
                connect_timeout=self.config.get('timeout', 10),
                read_timeout=self.config.get('read_timeout', 30),
                write_timeout=self.config.get('write_timeout', 30),
                autocommit=False,  # 显式控制事务
                ssl=self.config.get('ssl'),
                program_name=self.config.get('program_name', 'MySQLConnector')
            )

            # 设置会话变量
            with self.connection.cursor() as cursor:
                # 设置事务隔离级别
                isolation_level = self.config.get('isolation_level', 'REPEATABLE READ')
                cursor.execute(f"SET SESSION TRANSACTION ISOLATION LEVEL {isolation_level}")

                # 设置等待超时
                lock_wait_timeout = self.config.get('lock_wait_timeout', 50)
                cursor.execute(f"SET SESSION innodb_lock_wait_timeout = {lock_wait_timeout}")

                # 检查死锁检测状态
                try:
                    cursor.execute("SELECT @@GLOBAL.innodb_deadlock_detect")
                    result = cursor.fetchone()
                    deadlock_detect_status = result[0] if result else None
                    if deadlock_detect_status == 0:  # 如果禁用了
                        logging.warning("警告: MySQL服务器全局设置 innodb_deadlock_detect 已禁用，可能会影响死锁处理")
                except Exception as e:
                    # 如果查询失败，记录警告但继续执行
                    logging.warning(f"无法检查 innodb_deadlock_detect 状态: {e}")

            self.cursor = self.connection.cursor(pymysql.cursors.DictCursor)
            logging.info(f"MySQL连接成功: {self.config.get('host')}:{self.config.get('port')}")

        except pymysql.Error as e:
            error_code = e.args[0]
            if error_code == 1045:  # Access denied
                raise AuthenticationError(f"MySQL认证失败: {str(e)}", error_code=error_code, original_error=e)
            elif error_code == 2003:  # Can't connect
                raise ConnectionError1(f"MySQL连接失败: {str(e)}", error_code=error_code, original_error=e)
            elif error_code == 2013:  # Lost connection
                raise ConnectionError1(f"MySQL连接丢失: {str(e)}", error_code=error_code, original_error=e)
            elif error_code == 1205:  # Lock wait timeout
                raise TimeoutError1(f"MySQL锁等待超时: {str(e)}", error_code=error_code, original_error=e)
            elif error_code == 1213:  # Deadlock
                raise DeadlockError(f"MySQL死锁: {str(e)}", error_code=error_code, original_error=e)
            else:
                raise DatabaseError(f"MySQL连接错误: {str(e)}", error_code=error_code, original_error=e)
        except Exception as e:
            raise ConnectionError1(f"MySQL连接失败: {str(e)}", original_error=e)

    def disconnect(self) -> None:
        try:
            if self.cursor:
                self.cursor.close()
            if self.connection:
                self.connection.close()
            logging.info("MySQL连接已关闭")
        except Exception as e:
            raise ConnectionError1(f"MySQL断开连接失败: {str(e)}")


class SQLiteConnector(DatabaseConnector):
    """SQLite连接器"""

    def connect(self) -> None:
        try:
            if not self.connection:
                db_path = self.config.get('database', ':memory:')

                # 检查数据库文件路径
                if db_path != ':memory:' and not os.path.exists(os.path.dirname(db_path)):
                    os.makedirs(os.path.dirname(db_path))

                self.connection = sqlite3.connect(
                    db_path,
                    timeout=self.config.get('timeout', 10),
                    isolation_level=self.config.get('isolation_level', None)
                )
                self.connection.row_factory = sqlite3.Row
                self.cursor = self.connection.cursor()
                logging.info(f"SQLite连接成功: {db_path}")
        except sqlite3.Error as e:
            if "unable to open database file" in str(e).lower():
                raise ConnectionError1(f"SQLite数据库文件访问失败: {str(e)}")
            elif "database is locked" in str(e).lower():
                raise ConnectionError1(f"SQLite数据库被锁定: {str(e)}")
            else:
                raise DatabaseError(f"SQLite连接错误: {str(e)}")
        except Exception as e:
            raise ConnectionError1(f"SQLite连接失败: {str(e)}")

    def disconnect(self) -> None:
        try:
            if self.cursor:
                self.cursor.close()
            if self.connection:
                self.connection.close()
            logging.info("SQLite连接已关闭")
        except Exception as e:
            raise ConnectionError1(f"SQLite断开连接失败: {str(e)}")


class DatabaseFactory:
    """数据库工厂类"""

    @staticmethod
    def create_database(db_type: str, **kwargs) -> DatabaseConnector:
        """创建数据库连接器"""
        db_types = {
            'mysql': MySQLConnector,
            'sqlite': SQLiteConnector
        }

        connector_class = db_types.get(db_type.lower())
        if not connector_class:
            raise ValueError(f"不支持的数据库类型: {db_type}")

        return connector_class(**kwargs)


# 使用示例
if __name__ == "__main__":
    # MySQL示例
    pool = None  # 初始化为 None
    try:
        # 获取连接池实例
        pool = DatabaseConnectionPool()

        # MySQL连接配置
        mysql_config = {
            'host': os.getenv('MYSQL_HOST', 'localhost'),
            'port': int(os.getenv('MYSQL_PORT', 3306)),
            'user': os.getenv('MYSQL_USER', 'root'),
            'password': os.getenv('MYSQL_PASSWORD', ''),
            'database': os.getenv('MYSQL_DATABASE', ''),
            'charset': os.getenv('MYSQL_CHARSET', 'utf8mb4'),
            'timeout': int(os.getenv('MYSQL_TIMEOUT', 5)),
            'read_timeout': int(os.getenv('MYSQL_READ_TIMEOUT', 30)),
            'write_timeout': int(os.getenv('MYSQL_WRITE_TIMEOUT', 30)),
            'deadlock_retry_count': int(os.getenv('MYSQL_DEADLOCK_RETRY_COUNT', 3)),
            'deadlock_retry_delay': int(os.getenv('MYSQL_DEADLOCK_RETRY_DELAY', 1)),
            'isolation_level': os.getenv('MYSQL_ISOLATION_LEVEL', 'REPEATABLE READ'),
            'lock_wait_timeout': int(os.getenv('MYSQL_LOCK_WAIT_TIMEOUT', 50)),
            'program_name': 'TestApplication'
        }

        # 使用事务执行多个操作
        with pool.get_connection('mysql', **mysql_config) as mysql_db:
            try:
                # 查询操作
                results = mysql_db.execute(
                    "SELECT * FROM users WHERE age > %s AND status = %s",
                    (18, 'active')
                )
                print("MySQL查询结果:", results)

                # 插入操作
                affected = mysql_db.execute(
                    "INSERT INTO users (name, age, status) VALUES (%s, %s, %s)",
                    ('张三', 25, 'active')
                )
                print("MySQL插入影响行数:", affected)

            except QueryError as e:
                print(f"查询错误: {e}")
                if e.original_error:
                    print(f"原始错误: {e.original_error}")
            except TransactionError as e:
                print(f"事务错误: {e}")
            except DeadlockError as e:
                print(f"死锁错误: {e}")
            except TimeoutError1 as e:
                print(f"超时错误: {e}")
            except IntegrityError as e:
                print(f"完整性约束错误: {e}")
            except DataError as e:
                print(f"数据错误: {e}")

    except AuthenticationError as e:
        print(f"认证错误 [{e.error_code}]: {e}")
    except ConnectionError1 as e:
        print(f"连接错误: {e}")
    except DatabaseError as e:
        print(f"数据库错误: {e}")
    except Exception as e:
        print(f"未预期的错误: {e}")
    finally:
        try:
            # 关闭所有连接
            if pool is not None:  # 检查 pool 是否已创建
                pool.close_all()
        except PoolError as e:
            print(f"关闭连接池错误: {e}")
