import random
import re
from datetime import datetime

from flask import make_response, jsonify
from flask import request
from flask import current_app
from flask import session

from info import redis_store, db
from info.lib.yuntongxun.sms import CCP
from info.models import User
from info.utils.captcha.captcha import captcha
from . import passport_blu
from info import constants
from info.utils.response_code import RET


@passport_blu.route("/loginout", mehtods=["POST"])
def loginout():
    """清除用户登录状态"""
    session.pop("user_id", None)
    session.pop("nick_name", None)
    session.pop("mobile", None)

    return jsonify(errno=RET.OK, errmsg="OK")


@passport_blu.route("/login")
def login():
    """
    登录功能后端实现: mobile password
    :return:
    """
    params_data = request.json
    mobile = params_data.get("mobile")
    password = params_data.get("password")

    if not all([mobile, password]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")
    try:
        user = User.query.filter_by(mobile=mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR, errmsg="查询数据失败")
    # 校验用户是否存在
    if not user:
        return jsonify(errno=RET.USERERR, errmsg="用户不存在")
    # 校验密码
    if not user.check_password(password):
        return jsonify(errno=RET.PWDERR, errmsg="密码错误")

    # 用户登录状态保存
    session["user_id"] = user.id
    session["nick_name"] = user.nick_name
    session["mobile"] = user.mobile
    user.last_login = datetime.now()
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(e)
    return jsonify(errno=RET.OK, errmsg="OK")


@passport_blu.route("/register", methods=["POST"])
def register():
    """
    获取参数并判断是否有值: mobile/sms_code/password
    获取redis中SMS_code,删除redis的sms_code,并和请求sms_code比较，是否一致,
    没被注册则保存到数据库,信息注册
    :return:
    """
    params_data = request.json
    mobile = params_data.get("mobile")
    sms_code = params_data.get("smscode")
    password = params_data.get("password")
    if not all([mobile, sms_code, password]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不全")
    try:
        real_sms_code = redis_store.get("SMS_" + mobile)
        # 控制台输出redis data内容
        # current_app.logger.debug(real_sms_code)
        # 解码
        real_sms_code.decode()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.NODATA, errmsg="获取本地短信验证码失败")

    if not real_sms_code:
        return jsonify(errno=RET.NODATA, errmsg="短信验证码已过期")
    if sms_code != real_sms_code.decode():
        return jsonify(errno=RET.DATAERR,errmsg="短信验证码错误")

    try:
        redis_store.delete("SMS_" + mobile)
    except Exception as e:
        current_app.logger.error(e)
    user = User()
    user.nick_name = mobile
    user.mobile = mobile
    user.password = password
    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR, errmsg="数据保存失败")

    session["user_id"] = user.id
    session["nick_name"] = user.nick_name
    session["mobile"] = user.mobile

    return jsonify(errno=RET.OK, errmsg="OK")


@passport_blu.route("/smscode", methods=["POST"])
def send_sms():
    """
    1.从注册前端获取mobile image_code_id image_code
    :return:
    """
    params_data = request.json
    # current_app.logger.debug("参数数据为: %s" % params_data)
    mobile = params_data.get("mobile")
    image_code_id = params_data.get("image_code_id")
    image_code = params_data.get("image_code")

    if not all([mobile, image_code_id, image_code]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不全")

    # 验证mobile格式是否正确
    if not re.match("^1[34578]\\d{9}", mobile):
        return jsonify(errno=RET.DATAERR, errmsg="手机号格式错误")

    # 通过image_code_id从redis中取到ImageCode
    try:
        redis_image_code = redis_store.get("ImageCode_" + image_code_id)
        if redis_image_code:
            # 取出来redis_image_code先解码后清缓存redis
            redis_image_code = redis_image_code.decode()
            redis_store.delete("ImageCode_" + image_code_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAEXIST, errmsg="获取图片验证码失败")

    # 判断验证码是否过期
    if not redis_image_code:
        return jsonify(errno=RET.NODATA, errmsg="图片验证码已过期")

    # 判断验证码是否正确 > 字符串全转小写
    if image_code.lower() != redis_image_code.lower():
        return jsonify(errno=RET.DATAERR, errmsg="图片验证码输入错误")

    # 通过mobile从数据库取user,验证mobile是否已经注册过
    try:
        user = User.query.filter_by(mobile=mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAEXIST, errmsg="数据库查询失败")
    if user:
        return jsonify(errno=RET.DATAEXIST, errmsg="此手机号已经注册")

    # 生成随机六位数字发送短信
    result = random.randint(0, 999999)
    sms_code = "%06d" % result
    current_app.logger.debug("短信验证码的内容是： %s" % sms_code)
    # CCP()调用通讯第三方类
    res = CCP().send_template_sms(mobile, [sms_code, constants.SMS_CODE_REDIS_EXPIRES / 60], "1")
    # res=0成功 否则失败
    if res != 0:
        return jsonify(errno=RET.THIRDERR, errmsg="短信发送失败")

    # 将生成的短信存储到redis中
    try:
        redis_store.set("SMS_" + mobile, sms_code, constants.SMS_CODE_REDIS_EXPIRES)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="短信验证码保存失败")
    # 发挥发送成功的响应
    return jsonify(errno=RET.OK, errmsg="短信发送成功")


@passport_blu.route("/image_code")
def get_image_code():
    """获取图片验证码"""
    # 1.根据url传参取出code_id
    code_id = request.args.get("code_id")
    # 2.生成图片验证码的name,text,image
    name, text, image = captcha.generate_captcha()
    # 3.向redis保存图片验证码内容
    try:
        redis_store.setex("ImageCode_" + code_id, constants.IMAGE_CODE_REDIS_EXPIRES, text)
    except Exception as e:
        current_app.logger.error(e)
        return make_response(jsonify(errno=RET.DATAERR, errmsg="图片验证码保存失败"))

    # 4.保存成功则将image返回前端,返回响应内容
    resp = make_response(image)
    # 5.设置返回数据类型
    resp.headers["Content-type"] = "image/jpg"
    return resp

