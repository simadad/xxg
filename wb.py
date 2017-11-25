import re
import os
import json
import time
import requests
import threading
from queue import Queue
from threading import Thread
from lxml.html import etree
from collections import namedtuple
from requests.exceptions import ConnectionError
from concurrent.futures import ThreadPoolExecutor, wait


# --------------- 初始配置 ---------------
# 群 id
gid = '4176659651822678'
Cookie = 'SINAGLOBAL=3435881701430.0503.1511069446373; wb_cmtLike_2373503412=1; wvr=6; UOR=www.google.com,weibo.com,login.sina.com.cn; YF-Ugrow-G0=56862bac2f6bf97368b95873bc687eef; login_sid_t=08250c8ec0fe5f0339a8b672222eae9b; cross_origin_proto=SSL; YF-V5-G0=3d0866500b190395de868745b0875841; WBStorage=82ca67f06fa80da0|undefined; _s_tentry=passport.weibo.com; Apache=3471385025918.8516.1511599490149; ULV=1511599490162:14:14:14:3471385025918.8516.1511599490149:1511494767352; SCF=AnialW-1WRKw7QjY2BjUKntnIU-jjz4LSUlkHBo06bPBt3XmPR-UdUOuUOQSZ3vjl4rW7rbmA-XNuQu9B0RIl9A.; SUB=_2A253HV3MDeThGeRN7FEU8C3Iyj6IHXVUa8gErDV8PUNbmtANLRjEkW9NHetkT1sGu3HNCMTc_4cwCCgdQPN8O9aC; SUBP=0033WrSXqPxfM725Ws9jqgMF55529P9D9W54ln0wJQEAZ8ux9eaQd.q75JpX5KzhUgL.Foz0S0efeheXeKz2dJLoIEBLxK-L12qLBonLxK.LBK.LB-eLxK-L1KzL1KBLxK-L1KzL1KBt; SUHB=05irf0Wq06Qauj; ALF=1543135516; SSOLoginState=1511599516; wb_cusLike_2373503412=N; YF-Page-G0=19f6802eb103b391998cb31325aed3bc'
# 根目标配置，空值默认为当前项目文件夹
root_dir = r'C:\Users\AAA\Documents\PrivateFiles\MyDocument\xxg'
# 目标用户名，空值默认为匹配所有用户
target_names = []
# 断线重连次数
reconnect_times = 5
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
    '4176659651822678': '测试群'
}

headers = {
    'Cookie': Cookie,
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36',
    'Connection': 'keep-alive',
}


def get_and_update_newest_mid():
    """
    获取并更新最新 mid
    """
    url = 'https://weibo.com/message/history?gid={gid}&type=2'.format(gid=gid)
    r = requests.get(url, headers=headers)
    mid = re.findall(r'mid=(\d+)', r.text)[-1]
    newest_mid_path = '{group_path}/NEWEST'.format(group_path=group_path)
    with open(newest_mid_path, 'w') as f:
        print('newest_mid:\t', mid)
        f.write(mid)
    return mid


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
    is_new_dir = False
    path = '{root}/{sub}'.format(root=root, sub=sub)
    if not os.path.exists(path):
        os.mkdir(path)
        is_new_dir = True
    return path, is_new_dir


def init_root_dir():
    """
    创建目录树----etc 目录、data 目录
    """
    dir_root = _get_root_dir()
    _get_or_create_dir(dir_root, 'etc')
    dir_data, is_new_dir = _get_or_create_dir(dir_root, 'data')
    group_name = gid_dict[gid]
    print(u'准备爬取群组:\t', group_name)
    dir_group, is_new_dir = _get_or_create_dir(dir_data, group_name)
    for _type in target_type:
        _get_or_create_dir(dir_group, _type)
    return dir_group, is_new_dir


def get_is_continue():
    """
    用户交互，判断是否继续之前下载
    """
    if is_first_time:
        print(u'首次爬取，请耐心等候，中止程序请回车')
        return False
    finished_mark = '{group_path}/FINISHED'.format(group_path=group_path)
    if os.path.exists(finished_mark):
        print(u'下载新数据...')
        return False
    while True:
        _is_continue = input(u'是否继续上次下载？请输入: Y/N\n')
        if _is_continue == 'Y' or _is_continue == 'y':
            print(u'继续上次下载...')
            return True
        elif _is_continue == 'N' or _is_continue == 'n':
            print(u'下载新数据...')
            return False
        else:
            print(u'输入错误！')


def _get_or_set_mid(mid_file, mid=''):
    """
    读取或设置 mid 记录
    """
    mid_file_path = '{group_path}/{file}'.format(group_path=group_path, file=mid_file)
    if mid or is_first_time:
        with open(mid_file_path, 'w') as f:
            f.write(mid)
    else:
        with open(mid_file_path) as f:
            mid = f.read()
    return mid


def init_mid():
    """
    设定 mid 初始值，ON-OFF
    """
    if is_continue:
        _mid_on = _get_or_set_mid('EARLIEST')
        _mid_off = ''
    else:
        _mid_off = _get_or_set_mid('NEWEST')
        print('init_mid_off:\t', _mid_off)
        _mid_on = get_and_update_newest_mid()
        print('init_mid_on:\t', _mid_on)
    return _mid_on, _mid_off


def get_file_path(msg_name, data_type):
    """
    创建用户子目录
    :param msg_name: 发言人
    :param data_type: 数据类型
    :return: 文件路径
    """
    target = target_type[data_type]
    root = _get_root_dir()
    file_dir = '{root_dir}/data/{group_name}/{type}/{username}'.format(
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
    # with open('ttt_html.html', 'w', encoding='utf8') as f:
    #     f.write(html)
    e = etree.HTML(html)
    return e


def get_msg_list(e):
    """
     数据粗提取，消息组生成器, 返回(mid - 消息数据)元组
    """
    items = e.xpath('//div[@node-type="item"]')
    for item in items[::-1]:
        mid = item.get('mid')
        yield mid, item


def data_clean_engine(mid, item):
    """
    数据处理分发函数
    """
    target_data = data_target_filter(item)
    if target_data:
        msg_name, data_type, msg_data_pre = target_data
        data_clean_func = data_clean_func_reload(data_type)
        # print('data_type, clean_func:\t', data_type, data_clean_func)
        # t = Thread(target=data_clean_func, args=(msg_data_pre, msg_name))
        for i in range(1, 6):
            try:
                data_clean_func(msg_data_pre, msg_name)
                break
            except Exception as error:
                error_msg = 'data clean error\n{e}'.format(e=str(error))
                # print(error_msg)
                error_log(error_msg, mid, i)


def data_target_filter(item):
    """
    筛选目标文件类型消息
    :param item: 消息整体结构
    :return: 消息内容结构
    """
    msg_name = item.findtext('.//p[@class="bubble_name"]')
    msg_cont = item.find('.//div[@class="cont"]')
    for data_type, target in target_type.items():
        msg_data_pre = msg_cont.find(target.pattern)
        if msg_data_pre is not None:
            # print('data_type, pre_data_len:\t', data_type, len(msg_data_pre))
            return msg_name, data_type, msg_data_pre


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


def error_log(error, mid, times=0):
    """
    错误记录
    """
    root = _get_root_dir()
    error_file = r'{root}\etc\error.txt'.format(root=root)
    with open(error_file, 'a') as f:
        f.write('mid:\t{mid}\ttimes:\t{times}\n{e}\n\n'.format(
            e=str(error),
            mid=mid,
            times=times
        ))


def thr_router():
    """
    调度线程
    """
    global mid_off, is_loop_finished
    _earliest_mid = mid = mid_on
    while True:
        q_router_to_process.put(mid)
        mid_items = q_process_to_router.get()
        if not mid_items:
            print(u'thr_router:\tbreak\n进程中断，回车结束程序')
            mid_off = mid
            break
        for mid, item in mid_items:
            thr = pool_items.submit(data_clean_engine, mid, item)
            ts_items.append(thr)
            print('mid_router:\t', mid, '\tmid_off:\t', mid_off, '\tmid == mid_off:\t', mid == mid_off)
            if mid == mid_off or program_pause:
                print(u'thr_router:\treturn\t爬取完毕')
                if mid == mid_off:
                    is_loop_finished = True
                q_router_to_process.put(False)
                mid_off = mid
                return
        if _earliest_mid == mid or program_pause:
            print(u'thr_router:\tbreak\t爬取完毕')
            if _earliest_mid == mid:
                is_loop_finished = True
            q_router_to_process.put(False)
            mid_off = mid
            break
        else:
            _earliest_mid = mid


def thr_process():
    """
    进度线程
    """
    times = 0
    while True:
        # 从调度线程获取 mid，获取值为 False，循环结束
        mid = q_router_to_process.get()
        print('mid_process:\t', mid)
        if mid is False:
            print(u'thr_process:\tbreak\n爬取完毕，回车结束程序')
            break
        try:
            e_root = get_e(mid)
        except ConnectionError as error:
            times += 1
            error_log(error, mid, times)
            if times <= reconnect_times:
                q_router_to_process.put(mid)
                continue
            else:
                print(u'thr_process:\tbreak\n网络信号不稳定')
                q_process_to_router.put(False)
                break
        msg_list = get_msg_list(e_root)
        q_process_to_router.put(msg_list)
        times = 0


def mid_save():
    if is_first_time or is_continue:
        if is_loop_finished:
            _get_or_set_mid('FINISHED', mid_off)
        else:
            _get_or_set_mid('EARLIEST', mid_off)
    else:
        # TODO 非首次运行时，程序中止处理
        pass


if __name__ == '__main__':
    # ------------------- init on ---------------------
    group_path, is_first_time = init_root_dir()
    is_continue = get_is_continue()
    mid_on, mid_off = init_mid()
    if mid_on == mid_off:
        print(u'暂无新数据')
    else:
        program_pause = False
        is_loop_finished = False
        q_router_to_process = Queue(1)
        q_process_to_router = Queue(1)
        q_router_to_source = Queue(1)
        pool_items = ThreadPoolExecutor(20)
        ts_items = []
        ts = [Thread(target=thr_process, name='thr_process'), Thread(target=thr_router, name='thr_router')]
        print(444444, threading.active_count())
        for t in ts:
            t.start()
        print(55555, threading.active_count())
        # ------------------ init off ------------------------
        print('LOOP ON:')
        input(u'回车中止爬取\n')
        # q_control.put(True)
        program_pause = True
        print(11111, threading.active_count())
        for t in ts:
            t.join()
        print(2222, threading.active_count())
        wait(ts_items)
        print(3333, threading.active_count())
        print('LOOP OFF')
        # if is_continue:
        #     _get_or_set_mid('EARLIEST', mid_off)
        mid_save()
    print(u'退出程序')
