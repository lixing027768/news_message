
import redis
import logging
from flask import Flask
# 导入数据库拓展
from flask_sqlalchemy import SQLAlchemy
# 导入csrf验证拓展
from flask_wtf.csrf import CSRFProtect
from flask_session import Session
from redis import StrictRedis
from config import config
from logging.handlers import RotatingFileHandler

# 初始化数据库
db = SQLAlchemy()
redis_store = None  # type: StrictRedis


def setup_log(config_name):
    """配置日志"""

    # 设置日志的记录等级
    logging.basicConfig(level=config[config_name].LOG_LEVEL)  # 调试debug级
    # 创建日志记录器，指明日志保存的路径、每个日志文件的最大大小、保存的日志文件个数上限
    file_log_handler = RotatingFileHandler("logs/log", maxBytes=1024 * 1024 * 100, backupCount=10)
    # 创建日志记录的格式 日志等级 输入日志信息的文件名 行数 日志信息
    formatter = logging.Formatter('%(levelname)s %(filename)s:%(lineno)d %(message)s')
    # 为刚创建的日志记录器设置日志记录格式
    file_log_handler.setFormatter(formatter)
    # 为全局的日志工具对象（flask app使用的）添加日志记录器
    logging.getLogger().addHandler(file_log_handler)


def create_app(config_name):

    setup_log(config_name)

    app = Flask(__name__)
    # 加载对象配置信息
    app.config.from_object(config[config_name])
    # 配置数据库
    db.init_app(app)
    global redis_store
    redis_store = redis.StrictRedis(host=config[config_name].REDIS_HOST, port=config[config_name].REDIS_PORT)
    # csrf_token验证
    CSRFProtect(app)
    # 数据保存到redis
    Session(app)

    from flask_wtf.csrf import generate_csrf

    @app.after_request
    def after_request(response):
        csrf_token = generate_csrf()
        response.set_cookie("csrf_token", csrf_token)
        return response

    # 蓝图注册
    from info.moudles.index import index_blu
    app.register_blueprint(index_blu)
    # 登录注册模块
    from  info.moudles.passport import passport_blu
    app.register_blueprint(passport_blu)

    # 自定义过滤器:点击排行榜
    from info.utils.common import do_index_class
    app.add_template_filter(do_index_class, "index_class")

    return app