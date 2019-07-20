import random
import re
from flask import make_response, jsonify
from flask import request
from flask import current_app
from info import redis_store
from info.lib.yuntongxun.sms import CCP
from info.models import User
from info.utils.captcha.captcha import captcha
from . import passport_blu
from info import constants
from info.utils.response_code import RET


@passport_blu.route("/sms_code")
def send_sms():
    """
    1.从注册前端获取mobile image_code_id image_code
    :return:
    """
    mobile = request.args.get("mobile")
    image_code_id = request.args.get("image_code_id")
    image_code = request.args.get("image_code")

    if not all([mobile, image_code_id, image_code]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不全")

    # 验证mobile格式是否正确
    if not re.match(r"^1[34578]\d{9}$", mobile):
        return jsonify(errno=RET.DATAERR, errmsg="手机号格式错误")

    # 通过image_code_id从redis中取到ImageCode
    try:
        redis_image_code = redis_store.get("ImageCode_" + image_code_id)
        # 取出来redis_image_code后清缓存redis
        redis_store.delete(redis_image_code)
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
        user = User.query.filter_by(mobile=mobile).frist()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAEXIST, errmsg="数据库查询失败")
    if user:
        return jsonify(errno=RET.DATAEXIST, errmsg="此手机号已经注册")

    # 生成随机六位数字发送短信
    result = random.randint(0, 999999)
    sms_code = "%06d" % result
    current_app.logger.debug("短信验证码的内容是： %s" % sms_code)
    res = CCP.send_template_sms(mobile, [sms_code, constants.SMS_CODE_REDIS_EXPIRES/60], "1")
    # res=0成功 否则失败
    if res != 0:
        return jsonify(errno=RET.THIRDERR, errmsg="短信发送失败")

    # 将生成的短信存储到redis中
    try:
        redis_store.set("SMS_"+mobile, sms_code, constants.SMS_CODE_REDIS_EXPIRES)
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

