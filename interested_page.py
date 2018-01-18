import re
import sys
import time
import json
import psutil
import requests
import threading
from PIL import Image
from http import cookiejar

# 构造 Request headers
agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36'
headers = {
    'User-Agent': agent,
    "Content-Type": "application/x-www-form-urlencoded",
    'Connection': 'keep-alive',
}

session = requests.session()
session.cookies = cookiejar.LWPCookieJar('weibo_cookies.txt')

# 访问初始页面带上 cookie
index_url = "http://weibo.com/"
try:
    session.get(index_url, headers=headers, timeout=2)
except:
    session.get(index_url, headers=headers)

time_img = 0


def open_img(image_name):
    """
    打开图片
    :param image_name: 图片的路径
    :return:
    """
    global time_img
    with Image.open(image_name) as im:
        # print(time.time())
        time_img = time.time()
        im.show()
        # print(time_img)


def login():
    """
    登录主函数
    :return:
    """
    while True:
        try:
            image_name, qrcode_qrid = get_qrcode()
        except Exception as e:
            print(type(e), e.__str__())
            print(u'网络错误，正在重连')
            continue
        break
    print(u"请用手机微博扫描二维码")
    time.sleep(0.5)
    threading.Thread(target=open_img, name="open", args=(image_name,)).start()
    # 下面判断是否已经扫描了二维码
    statu = 0
    while not statu:
        qrcode_check_page = scan_qrcode(qrcode_qrid, get_rnd())
        if "50114002" in qrcode_check_page:
            statu = 1
            print(u"---成功扫描，请在手机点击确认以登录---")
        time.sleep(1)

    # 下面判断是否已经点击登录,并获取alt的内容
    alt = ''
    while statu:
        qrcode_click_page = scan_qrcode(qrcode_qrid, get_rnd())
        if "succ" in qrcode_click_page:
            # 登录成功后显示的是如下内容,需要获取到alt的内容
            # {"retcode":20000000,"msg":"succ","data":{"alt":"ALT-MTgxODQ3MTYyMQ==-sdfsfsdfsdfsfsdf-39A12129240435A0D"}}
            statu = 0
            alt = re.search(r'"alt":"(?P<alt>.+?)"', qrcode_click_page).group("alt")
            print(u"---正在登录---")
        time.sleep(1)

    # 下面是登录请求获取登录的跨域请求
    params = {
        "entry": "weibo",
        "returntype": "TEXT",
        "crossdomain": 1,
        "cdult": 3,
        "domain": "weibo.com",
        "alt": alt,
        "savestate": 30,
        "callback": "STK_" + get_rnd()
    }
    login_url_list = "http://login.sina.com.cn/sso/login.php"
    login_list_page = session.get(login_url_list, params=params, headers=headers)
    # 返回的数据如下所示，需要提取出4个url
    # STK_145809336258600({"retcode":"0","uid":"1111111","nick":"*****@sina.cn","crossDomainUrlList":
    # ["http:***************","http:\/\***************","http:\/\/***************","http:\/\/***************"]});
    url_list = [i.replace("\/", "/") for i in login_list_page.text.split('"') if "http" in i]
    for i in url_list:
        session.get(i, headers=headers)
        time.sleep(0.5)
    session.cookies.save(ignore_discard=True, ignore_expires=True)
    print(u"---登录成功---")
    close_img()


def image_program_judge(process_name):
    result = process_name == 'Microsoft.Photos.exe' or \
        process_name == 'dllhost.exe'
    return result


def close_img():
    """
    关闭图片
    """
    for p in psutil.process_iter():
        # TODO 此处需修改为系统默认图片工具
        if p.create_time() - time_img < 1 and image_program_judge(p.name()):
            p.kill()


def get_qrcode():
    """
    获取二维码图片以及二维码编号
    :return: qrcode_image, qrcode_qrid
    """
    qrcode_before = "http://login.sina.com.cn/sso/qrcode/image?entry=weibo&size=180&callback=STK_" + get_rnd()
    qrcode_before_page = session.get(qrcode_before, headers=headers)
    if qrcode_before_page.status_code != 200:
        sys.exit(u"可能微博改了接口!请联系 @司马咔咔 修改")
    qrcode_before_data = qrcode_before_page.text
    qrcode_image = re.search(r'"image":"(?P<image>.*?)"', qrcode_before_data).group("image").replace("\/", "/")
    qrcode_qrid = re.search(r'"qrid":"(?P<qrid>[\w\-]*)"', qrcode_before_data).group("qrid")
    qrcode_image = 'http:' + qrcode_image
    cha_page = session.get(qrcode_image, headers=headers)
    image_name = u"cha." + cha_page.headers['content-type'].split("/")[1]
    with open(image_name, 'wb') as f:
        f.write(cha_page.content)
        f.close()
    return image_name, qrcode_qrid


def scan_qrcode(qrcode_qrid, _time):
    """
    判断是否扫码等需要
    :return: html
    """
    params = {
        "entry": "weibo",
        "qrid": qrcode_qrid,
        "callback": "STK_" + _time
    }
    qrcode_check = "http://login.sina.com.cn/sso/qrcode/check"
    return session.get(qrcode_check, params=params, headers=headers).text


def is_login():
    """
    判断是否登录成功
    :return: 登录成功返回True，失败返回False
    """
    try:
        session.cookies.load(ignore_discard=True, ignore_expires=True)
    except:
        print(u"没有检测到cookie文件")
        return False
    url = "http://weibo.com/"
    my_page = session.get(url, headers=headers)
    if "我的首页" in my_page.text:
        return True
    else:
        return False


def get_rnd():
    return str(int(time.time() * 1000))


def check_in_page(pid):
    """
    超话签到
    """
    params = {
        'ajwvr': 6,
        'api': 'http://i.huati.weibo.com/aj/super/checkin',
        'texta': '签到',
        'textb': '已签到',
        'status': 0,
        'id': pid,
        'location': 'page_100808_super_index',
        '__rnd': get_rnd()
    }
    url = 'https://weibo.com/p/aj/general/button'
    return session.get(url, params=params, headers=headers)


def get_uid():
    """
    得到 uid
    """
    url = 'https://weibo.com'
    r = session.get(url)
    uid = re.findall(r"(\d+)\\/myfollow", r.text)[0]
    return uid


def get_interest_pages_list(uid):
    """
    获取兴趣主页 (nick,uid) 列表
    """
    url = 'https://weibo.com/p/{uid}/myfollow?relate=interested'.format(uid=uid)
    r = session.get(url)
    return re.findall(r'nick=(\w+)&uid=\d+:(\w+)&', r.text)


def get_reply(nick, r):
    """
    得到返回消息
    """
    data = json.loads(r.text)
    if int(data['code']) == 100000:
        reply = data['data']['alert_title']
    elif int(data['code']) == 382004:
        reply = data['msg']
    else:
        reply = u'签到异常'
    return '{nick:{black}<20}{reply}'.format(nick=nick, reply=reply, black=chr(12288))


def check_in():
    """
    签到
    """
    uid = get_uid()
    pages_list = get_interest_pages_list(uid)
    for nick, pid in pages_list:
        r = check_in_page(pid)
        reply = get_reply(nick, r)
        print(reply)


if __name__ == '__main__':
    login()
    check_in()
    input(u'签到完毕，回车退出\n')
