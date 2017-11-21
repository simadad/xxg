import os
import json
import time
import requests
from lxml.html import etree
from collections import namedtuple
from threading import Thread

# --------------- 初始配置 ---------------
# 目标用户名
target_names = []
# 根目标配置，空值默认为当前项目文件夹
root_dir = r'C:\Users\AAA\Documents\PrivateFiles\MyDocument\xxg'
# 起始消息 id
mid = ''
# 群 id
gid = '4101723897939433'
Cookie = 'login_sid_t=9da2eb32c3618e94ab99a7d8db4c45e1; YF-Ugrow-G0=57484c7c1ded49566c905773d5d00f82; cross_origin_proto=SSL; YF-V5-G0=b1e3c8e8ad37eca95b65a6759b3fc219; WBStorage=82ca67f06fa80da0|undefined; _s_tentry=www.google.com; UOR=www.google.com,weibo.com,www.google.com; Apache=3435881701430.0503.1511069446373; SINAGLOBAL=3435881701430.0503.1511069446373; ULV=1511069446387:1:1:1:3435881701430.0503.1511069446373:; SUB=_2A253FWf2DeThGeRN7FEU8C3Iyj6IHXVUY94-rDV8PUNbmtBeLVajkW9oVw2bY_0tnKfwO-0-kWZA-54MKg..; SUBP=0033WrSXqPxfM725Ws9jqgMF55529P9D9W54ln0wJQEAZ8ux9eaQd.q75JpX5KzhUgL.Foz0S0efeheXeKz2dJLoIEBLxK-L12qLBonLxK.LBK.LB-eLxK-L1KzL1KBLxK-L1KzL1KBt; SUHB=0KAg4VPrhS_UFZ; ALF=1542605606; SSOLoginState=1511069606; wvr=6; wb_cusLike_2373503412=N; YF-Page-G0=2d32d406b6cb1e7730e4e69afbffc88c'
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
}

headers = {
    'Cookie': Cookie,
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36',
    'Connection': 'keep-alive',
}


def create_root_dir():
    """
    创建目录树
    """
    root = root_dir or os.getcwd()
    for _, group_name in gid_dict.items():
        group_path = '{root_dir}/{group_name}/'.format(
            root_dir=root,
            group_name=group_name,
        )
        if not os.path.exists(group_path):
            os.mkdir(group_path)
            for t in target_type:
                type_path = '{group_path}/{type}'.format(
                    group_path=group_path,
                    type=t
                )
                os.mkdir(type_path)


def get_file_path(msg_name, data_type):
    """
    创建用户子目录
    :param msg_name: 发言人
    :param data_type: 数据类型
    :return:
    """
    target = target_type[data_type]
    root = root_dir or os.getcwd()
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


def _get_url():
    """
    生成访问地址
    """
    data['mid'] = mid
    data['__rnd'] = __rnd()
    return url_pre + '&'.join(['{k}={v}'.format(k=k, v=v) for k, v in data.items()])


def __rnd():
    return str(int(time.time() * 1000))


def get_e():
    """
     接收全局变量 mid，生成页面 etree 解析器
    """
    url = _get_url()
    # print('url:\t', url)
    r = requests.get(url, headers=headers)
    text = json.loads(r.text)
    html = text['data']['html']
    e = etree.HTML(html)
    return e


def get_msg_list(e):
    """
     数据粗提取，返回 mid + 消息组，混合生成器
    """
    items = e.xpath('//div[@node-type="item"]')
    yield items[0].get('mid')
    for item in items:
        yield item


def info_fork(msg_list_pre):
    """
    生成器数据数据分拆
    :param msg_list_pre: mid<0> + msg_list<1-20> 混合生成器
    :return: mid, 消息生成器
    """
    _mid = next(msg_list_pre)
    return _mid, msg_list_pre


def data_clean_engine(_msg_list):
    """
    数据处理分发函数
    :param _msg_list: 消息生成器
    """
    target_username_list = username_target_filter(_msg_list)
    for msg_name, msg_cont in target_username_list:
        target_data = data_target_filter(msg_cont)
        if target_data:
            data_type, msg_data_pre = target_data
            data_clean_func = data_clean_func_reload(data_type)
            # print('data_type, clean_func:\t', data_type, data_clean_func)
            try:
                data_clean_func(msg_data_pre, msg_name)
            except Exception as ee:
                error_log(ee)


def username_target_filter(_msg_list):
    """
    筛选目标用户发送的消息
    :param _msg_list: 消息生成器
    :return: yield 消息 item
    """
    for msg in _msg_list:
        msg_name = msg.findtext('.//p[@class="bubble_name"]')
        if not target_names or msg_name in target_names:
            msg_cont = msg.find('.//div[@class="cont"]')
            # print('msg_name, msg_cont_len:\t', msg_name, len(msg_cont))
            yield msg_name, msg_cont


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
    file_path = get_file_path(msg_name, 'TEXT')
    msg_text = msg_data_pre.text
    if not msg_text:
        msg_text = '<表情>\n'
    else:
        msg_text += '\n'
    with open(file_path, 'a', encoding='utf8') as f:
        f.write(msg_text)
    print('text:\t', msg_text)


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
    print('img:\t', data_url)


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
    print('audio:\t', data_url)
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
    with open('error.txt', 'a') as f:
        f.write('ERROR\t{e}\nmid:\t{mid}\n'.format(
            e=str(error),
            mid=mid
        ))


if __name__ == '__main__':
    create_root_dir()
    while True:
        print('LOOP ON:')
        e_root = get_e()
        m_list = get_msg_list(e_root)
        try:
            mid, msg_list = info_fork(m_list)
        except Exception as err:
            error_log(err)
            continue
        print('mid:\t', mid)
        Thread(target=data_clean_engine(msg_list)).start()
        print('LOOP OFF.')
        # break
