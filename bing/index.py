import os
import sys
import requests
import json
import uuid
import base64
import logging
import oss2
import time
from pyDes import des, CBC, PAD_PKCS5
from urllib.parse import urlparse
from datetime import datetime

##################################################################################

weixin_token = "b8a313194e1e4f0f99f19354afdaeea5"

user = {
    'username': '20339503150442',
    'password': '19471X',
}

form = {
    'signInstanceWid': '',
    'signPhotoUrl': '',
    'longitude': 126.575376,
    'latitude': 43.929179,
    'isMalposition': 0,
    'abnormalReason': '',
    'position': '中国吉林省吉林市龙潭区博学路',
    'isNeedExtra': 0
}

##################################################################################

# 初始化信息报错系统
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
login_logger = logging.getLogger("登录")
login_getUnSignedTasks = logging.getLogger("签到")

apis = {}
photo = ["1.png", "2.png", "3.png", "4.png", "5.png", "6.png", "7.png"]
qiandao = {
    '信息': '',
    '签到任务ID': '',
    '签到任务名': '',
    '当前签到时间': ''
}

# 获取北华今日校园api


def getCpdailyApis():
    flag = False
    # http://authserver.beihua.edu.cn/authserver
    idsUrl = "http://authserver.beihua.edu.cn/authserver"
    # https://beihua.campusphere.net/wec-portal-mobile/client
    ampUrl = "https://beihua.campusphere.net/wec-portal-mobile/client"
    # http://my.beihua.edu.cn/newmobile/client
    ampUrl2 = "http://my.beihua.edu.cn/newmobile/client"
    if 'campusphere' in ampUrl or 'cpdaily' in ampUrl:
        parse = urlparse(ampUrl)
        host = parse.netloc
        apis[
            'login-url'] = idsUrl + '/login?service=' + parse.scheme + r"%3A%2F%2F" + host + r'%2Fportal%2Flogin'
        apis['host'] = host
    if 'campusphere' in ampUrl2 or 'cpdaily' in ampUrl2:
        parse = urlparse(ampUrl2)
        host = parse.netloc
        apis[
            'login-url'] = idsUrl + '/login?service=' + parse.scheme + r"%3A%2F%2F" + host + r'%2Fportal%2Flogin'
        apis['host'] = host
    if flag:
        login_logger.error('未加入今日校园或者学校全称错误')
        sendmessage("失败签到-今日校园", '未加入今日校园或者学校全称错误')
        sys.exit(0)
    login_logger.info("apis信息："+str(apis))
    return apis


def getSession():
    params = {
        # apis['login-url'],
        'login_url': 'http://authserver.beihua.edu.cn/authserver/login?service=https%3A%2F%2Fbeihua.campusphere.net%2Fportal%2Flogin',
        'needcaptcha_url': '',
        'captcha_url': '',
        'username': user['username'],
        'password': user['password']
    }
    cookies = {}
    # 借助上一个项目开放出来的登陆API，模拟登陆
    res = requests.post(
        url="http://swu.zimo.wiki:8080/wisedu-unified-login-api-v1.0/api/login", data=params)
    cookieStr = str(res.json()['cookies'])
    login_logger.debug("Cookie信息："+str(cookieStr))
    if cookieStr == 'None':
        login_logger.error("登录错误 一次" + str(res.json()))
        time.sleep(1)  # 休眠1秒
        res = requests.post(
            url="http://swu.zimo.wiki:8080/wisedu-unified-login-api-v1.0/api/login", data=params)
        cookieStr = str(res.json()['cookies'])
        if cookieStr == 'None':
            login_logger.error("登录错误 二次" + str(res.json()))
            time.sleep(2)  # 休眠2秒
            res = requests.post(
                url="http://swu.zimo.wiki:8080/wisedu-unified-login-api-v1.0/api/login", data=params)
            cookieStr = str(res.json()['cookies'])
            if cookieStr == 'None':
                login_logger.error("登录错误 三次" + str(res.json()))
                time.sleep(3)  # 休眠3秒
                res = requests.post(
                    url="http://swu.zimo.wiki:8080/wisedu-unified-login-api-v1.0/api/login", data=params)
                cookieStr = str(res.json()['cookies'])
                if cookieStr == 'None':
                    login_logger.error("登录错误 四次" + str(res.json()))
                    time.sleep(4)  # 休眠4秒
                    res = requests.post(
                        url="http://swu.zimo.wiki:8080/wisedu-unified-login-api-v1.0/api/login", data=params)
                    cookieStr = str(res.json()['cookies'])
                    if cookieStr == 'None':
                        login_logger.error("登录错误 五次 退出" + str(res.json()))
                        sendmessage("失败签到-今日校园", '登录失败：' + str(res.json()))
                        sys.exit(0)
    # 解析cookie
    for line in cookieStr.split(';'):
        name, value = line.strip().split('=', 1)
        cookies[name] = value
    session = requests.session()
    session.cookies = requests.utils.cookiejar_from_dict(
        cookies, cookiejar=None, overwrite=True)
    return session


# 上传图片到阿里云oss
def uploadPicture(session, image, apis):
    url = 'https://{host}/wec-counselor-sign-apps/stu/sign/getStsAccess'.format(
        host=apis['host'])
    res = session.post(url=url, headers={
                       'content-type': 'application/json'}, data=json.dumps({}))
    datas = res.json().get('datas')
    fileName = datas.get('fileName')
    accessKeyId = datas.get('accessKeyId')
    accessSecret = datas.get('accessKeySecret')
    securityToken = datas.get('securityToken')
    endPoint = datas.get('endPoint')
    bucket = datas.get('bucket')
    try:
        bucket = oss2.Bucket(oss2.Auth(access_key_id=accessKeyId,
                                   access_key_secret=accessSecret), endPoint, bucket)
    except:
        sendmessage("失败签到-今日校园", '图片上传失败：oss连接错误')
        login_getUnSignedTasks.error("图片上传失败：oss连接错误")
        sys.exit(0)
    with open(image, "rb") as f:
        data = f.read()
    try:
        bucket.put_object(key=fileName, headers={
                        'x-oss-security-token': securityToken}, data=data)
    except:
        sendmessage("失败签到-今日校园", '图片上传失败：oss_put错误')
        login_getUnSignedTasks.error("图片上传失败：oss_put错误")
        sys.exit(0)
    res = bucket.sign_url('PUT', fileName, 60)
    return fileName


# 获取图片上传位置
def getPictureUrl(session, fileName, apis):
    url = 'https://{host}/wec-counselor-sign-apps/stu/sign/previewAttachment'.format(
        host=apis['host'])
    data = {
        'ossKey': fileName
    }
    res = session.post(url=url, headers={
                       'content-type': 'application/json'}, data=json.dumps(data), verify=False)
    photoUrl = res.json().get('datas')
    return photoUrl

# 获取最新未签到任务


def getUnSignedTasks(session, apis):
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36',
        'content-type': 'application/json',
        'Accept-Encoding': 'gzip,deflate',
        'Accept-Language': 'zh-CN,en-US;q=0.8',
        'Content-Type': 'application/json;charset=UTF-8'
    }
    # 第一次请求每日签到任务接口，主要是为了获取MOD_AUTH_CAS
    res = session.post(
        url='https://{host}/wec-counselor-sign-apps/stu/sign/getStuSignInfosInOneDay'.format(
            host=apis['host']),
        headers=headers, data=json.dumps({}))
    # 第二次请求每日签到任务接口，拿到具体的签到任务
    res = session.post(
        url='https://{host}/wec-counselor-sign-apps/stu/sign/getStuSignInfosInOneDay'.format(
            host=apis['host']),
        headers=headers, data=json.dumps({}))
    if len(res.json()['datas']['unSignedTasks']) < 1:
        sendmessage("失败签到-今日校园", '当前没有未签到任务')
        login_getUnSignedTasks.error('当前没有未签到任务')
        sys.exit(0)

    latestTask = res.json()['datas']['unSignedTasks'][0]

    login_getUnSignedTasks.info("今日第一个签到ID："+latestTask['signInstanceWid'])
    form['signInstanceWid'] = latestTask['signInstanceWid']
    qiandao['签到任务名'] = latestTask['taskName']
    qiandao['签到任务ID'] = latestTask['signInstanceWid']
    qiandao['当前签到时间'] = latestTask['currentTime']

    return {
        'signInstanceWid': latestTask['signInstanceWid'],
        'signWid': latestTask['signWid']
    }


# DES加密
def DESEncrypt(s, key='ST83=@XV'):
    key = key
    iv = b"\x01\x02\x03\x04\x05\x06\x07\x08"
    k = des(key, CBC, iv, pad=None, padmode=PAD_PKCS5)
    encrypt_str = k.encrypt(s)
    return base64.b64encode(encrypt_str).decode()

# 提交签到任务


def submitForm(session, user, form, apis):
    # Cpdaily-Extension
    extension = {
        "lon": form['longitude'],
        "model": "OPPO R11 Plus",
        "appVersion": "8.2.7",
        "systemVersion": "4.4.4",
        "userId": user['username'],
        "systemName": "android",
        "lat": form['latitude'],
        "deviceId": str(uuid.uuid1())
    }

    headers = {
        # 'tenantId': '1019318364515869',
        'User-Agent': 'Mozilla/5.0 (Linux; Android 4.4.4; OPPO R11 Plus Build/KTU84P) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/33.0.0.0 Safari/537.36 okhttp/3.12.4',
        'CpdailyStandAlone': '0',
        'extension': '1',
        'Cpdaily-Extension': DESEncrypt(json.dumps(extension)),
        'Content-Type': 'application/json; charset=utf-8',
        'Accept-Encoding': 'gzip',
        # 'Host': 'swu.cpdaily.com',
        'Connection': 'Keep-Alive'
    }
    res = session.post(url='https://{host}/wec-counselor-sign-apps/stu/sign/submitSign'.format(host=apis['host']),
                       headers=headers, data=json.dumps(form))
    message = res.json()['message']
    if message == 'SUCCESS':
        login_getUnSignedTasks.info('今日校园签到成功！')
        sendmessage("成功签到-今日校园", "今日校园签到成功！")
    else:
        login_getUnSignedTasks.info('自动签到失败，原因是：' + message)
        sendmessage("失败签到-今日校园", '自动签到失败，原因是：' + message)
        sys.exit(0)

def sendmessage(tetile, message):
    qiandao['信息'] = message
    posturl = "http://pushplus.hxtrip.com/send"
    data = {
        "token": weixin_token,
        "title": tetile,
        "content": json.dumps(qiandao),
        "template": "json"
    }
    requests.post(posturl, data=data)
    return


def main():
    apis = getCpdailyApis()
    session = getSession()
    getUnSignedTasks(session, apis)

    dayOfWeek = str(datetime.now().isoweekday())
    login_getUnSignedTasks.info('今天星期几：' + dayOfWeek)

    filePath = str(sys.path[0]) + "\\" + dayOfWeek + ".png"
    login_getUnSignedTasks.info('图片径路：' + filePath)
    if not os.path.exists(filePath):
        sendmessage("失败签到-今日校园", '图片上传失败，文件不存在：' + filePath)
        login_getUnSignedTasks.error("图片不存在："+filePath)
        sys.exit(0)

    fileName = uploadPicture(session, filePath, apis)
    form['signPhotoUrl'] = getPictureUrl(session, fileName, apis)
    login_getUnSignedTasks.info("图片上传信息："+form['signPhotoUrl'])

    submitForm(session, user, form, apis)


if __name__ == '__main__':
    main()
