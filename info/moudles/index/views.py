from flask import current_app

from . import index_blu
from flask import render_template


@index_blu.route("/index")
def index():
    return render_template("news/index.html")


@index_blu.route("/favicon.ico")
def favicon():
    # send_static_file是服务器自动访问静态文件调用的方法
    # current_app是从flask导进来的应用上下文
    return current_app.send_static_file("news/favicon.ico")
