from flask import current_app
from flask import session

from info import constants
from info.models import User, News
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
    # 获取新闻首页新闻点击排行榜
    news_list = None
    try:
        news_list = News.query.order_by(News.clicks.desc()).limit(constants.HOME_PAGE_MAX_NEWS)
    except Exception as e:
        current_app.logger.error(e)

    click_news_list = []
    if news_list:
        for news in news_list:
            click_news_list.append(news.to_basic_dict())
    data = {
        "user_info": user.to_dict() if user else None,
        "click_news_list": click_news_list,
    }

    return render_template("news/index.html", data=data)


@index_blu.route("/favicon.ico")
def favicon():
    # send_static_file是服务器自动访问静态文件调用的方法
    # current_app是从flask导进来的应用上下文
    return current_app.send_static_file("news/favicon.ico")
