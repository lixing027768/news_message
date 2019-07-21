from flask import current_app
from flask import session

from info.models import User
from . import index_blu
from flask import render_template


@index_blu.route("/index")
def index():
    user_id = session.get("user_id")
    user = None
    try:
        user = User.query.get(user_id)
    except Exception as e:
        current_app.logger.error(e)
    return render_template("news/index.html", data={"user_info": user.to_dict() if user else None})


@index_blu.route("/favicon.ico")
def favicon():
    # send_static_file是服务器自动访问静态文件调用的方法
    # current_app是从flask导进来的应用上下文
    return current_app.send_static_file("news/favicon.ico")
