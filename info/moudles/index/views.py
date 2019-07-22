from flask import current_app, jsonify
from flask import request
from flask import session

from info import constants
from info.models import User, News, Category
from info.utils.response_code import RET
from . import index_blu
from flask import render_template


@index_blu.route("/news_list")
def get_news_list():
    """获取新闻列表"""
    page = request.args.get("page", "1")
    per_page = request.args.get("per_page", constants.HOME_PAGE_MAX_NEWS)
    category_id = request.args.get("cid", "1")

    try:
        page = int(page)
        per_page = int(per_page)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    # 查询数据并分页
    filters = []
    if category_id != "1":
        filters.append(News.category_id == category_id)
    try:
        # 按照新闻创建时间排序查询
        paginte = News.query.filter(*filters).order_by(News.create_time.desc()).paginate(page, per_page, False)
        news_list = paginte.items
        total_page = paginte.pages
        current_page = paginte.page
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR, errmsg="查询数据失败")

    news_dicts_li = []

    for news in news_list:
        news_dicts_li.append(news.to_basic_dict())
    data = {
        "total_page": total_page,
        "current_page": current_page,
        "news_li": news_dicts_li,
        "cid": category_id,
    }
    return jsonify(errno=RET.OK, errmsg="OK", data=data)


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

    # 新闻分类
    categorys = Category.query.all()
    # 定义列表保存分类数据
    category_dicts = []
    # enumerate(items)提供了iter和next方法，使对象可迭代
    for category in categorys:
        category_dicts.append(category.to_dict())

    data = {
        "user_info": user.to_dict() if user else None,
        "click_news_list": click_news_list,
        "categories": category_dicts,
    }
    return render_template("news/index.html", data=data)


@index_blu.route("/favicon.ico")
def favicon():
    # send_static_file是服务器自动访问静态文件调用的方法
    # current_app是从flask导进来的应用上下文
    return current_app.send_static_file("news/favicon.ico")
