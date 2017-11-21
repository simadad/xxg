import os
import json
import time
import requests
from queue import Queue
from lxml.html import etree
from collections import namedtuple
from requests.exceptions import ConnectionError
from concurrent.futures import ThreadPoolExecutor, wait


# --------------- 初始配置 ---------------
# 群 id
gid = '4167757236964650'
Cookie = 'login_sid_t=9da2eb32c3618e94ab99a7d8db4c45e1; YF-Ugrow-G0=57484c7c1ded49566c905773d5d00f82; cross_origin_proto=SSL; YF-V5-G0=b1e3c8e8ad37eca95b65a6759b3fc219; WBStorage=82ca67f06fa80da0|undefined; _s_tentry=www.google.com; UOR=www.google.com,weibo.com,www.google.com; Apache=3435881701430.0503.1511069446373; SINAGLOBAL=3435881701430.0503.1511069446373; ULV=1511069446387:1:1:1:3435881701430.0503.1511069446373:; SUB=_2A253FWf2DeThGeRN7FEU8C3Iyj6IHXVUY94-rDV8PUNbmtBeLVajkW9oVw2bY_0tnKfwO-0-kWZA-54MKg..; SUBP=0033WrSXqPxfM725Ws9jqgMF55529P9D9W54ln0wJQEAZ8ux9eaQd.q75JpX5KzhUgL.Foz0S0efeheXeKz2dJLoIEBLxK-L12qLBonLxK.LBK.LB-eLxK-L1KzL1KBLxK-L1KzL1KBt; SUHB=0KAg4VPrhS_UFZ; ALF=1542605606; SSOLoginState=1511069606; wvr=6; wb_cusLike_2373503412=N; YF-Page-G0=2d32d406b6cb1e7730e4e69afbffc88c'
# 根目标配置，空值默认为当前项目文件夹
root_dir = r'C:\Users\AAA\Documents\PrivateFiles\MyDocument\xxg'
# 目标用户名，空值默认为匹配所有用户
target_names = []
# 起始消息 mid，空值默认为当前最新一条消息
mid = ''
# 已记录的最新一条消息 id，空值默认为 etc/newest_mid.txt 中记录的数据
mid_newest = ''
# 已记录的最早一条消息 id，空值默认为 etc/earliest.txt 中记录的数据
mid_earliest = ''
# ------------- 配置结束 ————————


url_pre = 'https://weibo.com/aj/groupchat/getdialog?'

data = {
    '_wv': '5',
    'ajwvr': '6',
    'gid': gid,
    '_t': '0',
    'count': '20',
    # 'mid': mid,
    # '__rnd': '',
}
# 命名元组 --- 匹配正则式、数据清理函数、文件扩展名
TargetChoice = namedtuple('TargetChoice', ('pattern', 'clean_func', 'ext'))

# 目标数据类型 - 命名元组对照表
target_type = {
    'AUDIO': TargetChoice('.//div[@class="private_player_mod"]', 'audio_type_data_clean', 'amr'),
    'IMG': TargetChoice('.//div[@class="pic_b_mod"]', 'image_type_data_clean', 'jpg'),
    'TEXT': TargetChoice('.//p[@class="page"]', 'text_type_data_clean', 'txt'),
}

# 群 gid - 地址对照表
gid_dict = {
    '4101723897939433': '宝儿群',
    '4167757236964650': '红剪花',
}

headers = {
    'Cookie': Cookie,
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36',
    'Connection': 'keep-alive',
}


def _get_root_dir():
    """
    获取根目录
    :return: 根目录
    """
    return root_dir or os.getcwd()


def _get_or_create_dir(root, sub):
    """
    得到或创建目录
    :param root: 根目录
    :param sub: 子目录
    :return: 目录路径
    """
    path = '{root}/{sub}'.format(root=root, sub=sub)
    if not os.path.exists(path):
        os.mkdir(path)
    return path


def init_root_dir():
    """
    创建目录树----etc 目录、data 目录
    """
    set_mid()
    dir_root = _get_root_dir()
    _get_or_create_dir(dir_root, 'etc')
    dir_data = _get_or_create_dir(dir_root, 'data')
    for _, group_name in gid_dict.items():
        dir_group = _get_or_create_dir(dir_data, group_name)
        for t in target_type:
            _get_or_create_dir(dir_group, t)


def _get_or_set_mid(mid_file):
    """
    读取并创建初始 mid
    :param mid_file:
    :return:
    """
    root = _get_root_dir()
    mid_file_path = '{root}/data/{mid_file}'.format(root=root, mid_file=mid_file)
    if not os.path.exists(mid_file_path):
        with open(mid_file_path, 'w'):
            pass
    with open(mid_file_path) as f:
        _mid = f.read()
    return _mid


def _get_is_continue():
    """
    用户交互，判断是否继续之前下载
    """
    while True:
        is_continue = input(r'是否继续上次下载？请输入： Y/N')
        if is_continue == 'Y' or is_continue == 'y':
            print(r'继续上次下载')
            return True
        elif is_continue == 'N' or is_continue == 'n':
            print(r'下载新数据')
            return False
        else:
            print('输入错误！')

def init_mid():
    """
    设定 mid 初始值，mid_earliest、mid_latest、mid
    """
    global mid_earliest, mid_newest, mid
    is_continue = _get_is_continue()
    if not mid_earliest:
        mid_earliest = _get_or_set_mid('earliest.txt')
    if not mid_newest:
        mid_newest = _get_or_set_mid('newest.txt')
    if is_continue:
        mid = mid_earliest
        mid_newest = ''


# def set_mid(_mid=None, is_final=True):
#     """
#     读取并设置
#     """
#     etc_dir = '{root}/etc'.format(root=get_root_dir())
#     latest_mid_file = '{etc}/last_mid.txt'.format(etc=etc_dir)
#     earliest_mid_file = '{etc}/earliest_mid.txt'.format(etc=etc_dir)
#     global mid_latest, mid_earliest
#     if _mid:
#         if is_final:
#             mid_latest= _mid
#         with open(latest_mid_file, 'w') as f:
#             f.write(_mid)
#     elif not os.path.exists(etc_dir):
#         os.mkdir(etc_dir)
#         mid_latest= ''
#         with open(latest_mid_file, 'w') as f:
#             f.write(mid_latest)
#     else:
#         with open(latest_mid_file) as f:
#             mid_latest= f.read()
#

def get_file_path(msg_name, data_type):
    """
    创建用户子目录
    :param msg_name: 发言人
    :param data_type: 数据类型
    :return: 文件路径
    """
    target = target_type[data_type]
    root = get_root_dir()
    file_dir = '{root_dir}/{group_name}/{type}/{username}'.format(
        root_dir=root,
        group_name=gid_dict[gid],
        type=data_type,
        username=msg_name
    )
    if data_type == 'TEXT':
        file_path = '{file_dir}.txt'.format(file_dir=file_dir)
    else:
        if not os.path.exists(file_dir):
            os.mkdir(file_dir)
        file_path = '{file_dir}/{file_name}.{ext}'.format(
            file_dir=file_dir,
            file_name=str(time.time()),
            ext=target.ext
        )
    return file_path


def _get_url(_mid):
    """
    生成访问地址
    """
    data['mid'] = _mid
    data['__rnd'] = __rnd()
    return url_pre + '&'.join(['{k}={v}'.format(k=k, v=v) for k, v in data.items()])


def __rnd():
    return str(int(time.time() * 1000))


def get_e(_mid):
    """
     接收全局变量 mid，生成页面 etree 解析器
    """
    url = _get_url(_mid)
    # print('url:\t', url)
    r = requests.get(url, headers=headers)
    text = json.loads(r.text)
    html = text['data']['html']
    with open('ttt_html.html', 'w', encoding='utf8') as f:
        f.write(html)
    e = etree.HTML(html)
    return e


def get_msg_list(e):
    """
     数据粗提取，消息组生成器, 返回(mid - 消息数据)元组
    """
    items = e.xpath('//div[@node-type="item"]')
    for item in items[::-1]:
        yield item


'''
def info_fork(msg_list_pre):
    """
    生成器数据数据分拆
    :param msg_list_pre: mid<0> + msg_list<1-20> 混合生成器
    :return: mid, 消息生成器
    """
    _mid = next(msg_list_pre)
    return _mid, msg_list_pre
'''


def data_clean_engine(_msg_list):
    """
    数据处理分发函数
    :param _msg_list: 消息生成器
    """
    global mid
    _mid = mid
    pool_data = ThreadPoolExecutor(20)
    ts_data = []
    target_username_list = username_target_filter(_msg_list)
    for _mid, msg_name, msg_cont in target_username_list:
        target_data = data_target_filter(msg_cont)
        if target_data:
            data_type, msg_data_pre = target_data
            data_clean_func = data_clean_func_reload(data_type)
            # print('data_type, clean_func:\t', data_type, data_clean_func)
            # t = Thread(target=data_clean_func, args=(msg_data_pre, msg_name))
            try:
                t_data = pool_data.submit(data_clean_func, msg_data_pre, msg_name)
                ts_data.append(t_data)
            except Exception as ee:
                error_msg = 'data clean error\n{ee}'.format(ee=str(ee))
                print(error_msg)
                error_log(error_msg)
            else:
                mid = _mid
    else:
        q_mid.put((_mid, False))
        wait(ts_data)


def username_target_filter(_msg_list):
    """
    筛选目标用户发送的消息，判断历史记录
    :param _msg_list: 消息生成器
    :return: yield 消息 item
    """
    for msg in _msg_list:
        _mid = msg.get('mid')
        msg_name = msg.findtext('.//p[@class="bubble_name"]')
        if not target_names or msg_name in target_names:
            msg_cont = msg.find('.//div[@class="cont"]')
            # print('msg_name, msg_cont_len:\t', msg_name, len(msg_cont))
            yield _mid, msg_name, msg_cont
        if mid_latest== _mid:
            # root = get_root_dir()
            # set_last_mid(root, _mid)
            break


def data_target_filter(msg_cont):
    """
    筛选目标文件类型消息
    :param msg_cont: 消息整体结构
    :return: 消息内容结构
    """
    for data_type, target in target_type.items():
        msg_data_pre = msg_cont.find(target.pattern)
        if msg_data_pre is not None:
            # print('data_type, pre_data_len:\t', data_type, len(msg_data_pre))
            return data_type, msg_data_pre


def text_type_data_clean(msg_data_pre, msg_name):
    """
    文字类型数据清洗
    :param msg_data_pre: 消息内容结构
    :param msg_name: 发布人
    :return:
    """
    # TODO 处理表情内容
    # TODO 处理链接内容
    file_path = get_file_path(msg_name, 'TEXT')
    msg_text = msg_data_pre.text
    if not msg_text:
        msg_text = '<表情>\n'
    else:
        msg_text += '\n'
    with open(file_path, 'a', encoding='utf8') as f:
        f.write(msg_text)
    # print('text:\t', msg_text)
    print('TEXT')


def image_type_data_clean(msg_data_pre, msg_name):
    """
    图片类型数据清洗
    :param msg_data_pre: 消息内容结构
    :param msg_name: 发布人
    """
    data_url = msg_data_pre.xpath('.//ul//a/@href')[1]
    r = requests.get(data_url, headers=headers)
    file_path = get_file_path(msg_name, 'IMG')
    with open(file_path, 'wb') as f:
        f.write(r.content)
    print('IMG')


def audio_type_data_clean(msg_data_pre, msg_name):
    """
    音频类型数据清洗
    :param msg_data_pre: 消息内容结构
    :param msg_name: 发布人
    """
    data_url = msg_data_pre.xpath('.//a[last()]/@href')[0]
    r = requests.get(data_url, headers=headers)
    file_path = get_file_path(msg_name, 'AUDIO')
    with open(file_path, 'wb') as f:
        f.write(r.content)
    print('AUDIO')
    return


def data_clean_func_reload(data_type):
    """
    数据清洗函数重载
    :param data_type: 数据类型
    :return: 数据清洗函数
    """
    target = target_type[data_type]
    return globals()[target.clean_func]


def error_log(error):
    """
    错误记录
    """
    root = get_root_dir()
    error_file = r'{root}\etc\error.txt'.format(root=root)
    with open(error_file, 'a') as f:
        f.write('mid:\t{mid}\nERROR:\t{e}\n\n'.format(
            e=str(error),
            mid=mid
        ))


def is_final(_mid, is_timeout):
    """
    爬取完毕判断
    :param _mid: 
    :param is_timeout:
    :return:
    """
    if (mid_earliest or not is_timeout) and _mid == mid_earliest:
        return True
    else:
        return False


if __name__ == '__main__':
    init_root_dir()
    # set_mid()
    init_mid()
    q_mid = Queue()
    q_mid.put((mid, False))
    pool_msg = ThreadPoolExecutor(5)
    ts_msg = []
    while True:
        print('LOOP ON:')
        mid_next_page, to_repeat = q_mid.get(timeout=10)
        print('mid:\t', mid, '\tlast_mid:\t', last_mid, '\tmid_next_page:\t', mid_next_page, '\tto_repeat:\t', to_repeat)
        if mid_next_page and mid_next_page == last_mid:
            break
        try:
            e_root = get_e(mid_next_page)
        except ConnectionError as e:
            e_msg = 'get_e_error\n{e}'.format(e=str(e))
            error_log(e_msg)
            set_last_mid(mid, False)
            q_mid.put((mid_next_page, True))
            print(e_msg)
            continue
        msg_list = get_msg_list(e_root)
        t_msg = pool_msg.submit(data_clean_engine, msg_list)
        ts_msg.append(t_msg)
    wait(ts_msg)
    set_last_mid(mid)
    print('LOOP OFF.')



# TODO earliest_mid  and last_mid
