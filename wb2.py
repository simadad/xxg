import re
import os
import json
import time
import random
import requests
from queue import Queue
from threading import Thread
from lxml.html import etree
from collections import namedtuple
from requests.exceptions import ConnectionError
from concurrent.futures import ThreadPoolExecutor, wait


# --------------- 初始配置 ---------------
# 群 id
gid = '4101723897939433'
Cookie = input(u'请输入cookie\n')
# 根目标配置，空值默认为当前项目文件夹
root_dir = ''
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
    # '4167757236964650': '红剪花',
    # '4176659651822678': '测试群'
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
    newest_mid_path = '{group_path}/NEWEST'.format(group_path=group_path_etc)
    with open(newest_mid_path, 'w') as f:
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
    dir_etc, is_new_dir = _get_or_create_dir(dir_root, 'etc')
    dir_data, is_new_dir = _get_or_create_dir(dir_root, 'data')
    group_name = gid_dict[gid]
    print(u'准备爬取群组:\t', group_name)
    dir_group_data, is_new_dir = _get_or_create_dir(dir_data, group_name)
    dir_group_etc, is_new_dir = _get_or_create_dir(dir_etc, group_name)
    for _type in target_type:
        _get_or_create_dir(dir_group_data, _type)
    return dir_group_etc, is_new_dir


def get_is_continue():
    """
    用户交互，判断是否继续之前下载
    """
    if is_first_time:
        print(u'首次爬取，请耐心等候，中止程序请回车')
        return False
    finished_mark = '{group_path}/FINISHED'.format(group_path=group_path_etc)
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
    mid_file_path = '{group_path}/{file}'.format(group_path=group_path_etc, file=mid_file)
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


def _save_error_json_file(_mid, r):
    """
    保存错误请求信息
    """
    error_path = '{path}/error_{mid}.json'.format(
        path=group_path_etc,
        mid=_mid
    )
    with open(error_path, 'w', encoding='utf8') as f:
        f.write(r.text)


def get_e(_mid):
    """
     接收全局变量 mid，生成页面 etree 解析器
    """
    url = _get_url(_mid)
    r = requests.get(url, headers=headers)
    try:
        text = json.loads(r.text)
    except Exception as error:
        _save_error_json_file(_mid, r)
        error_log('get_e', error, _mid)
        raise ConnectionError
    html = text['data']['html']
    e = etree.HTML(html)
    if e is None:
        _save_error_json_file(_mid, r)
        raise ConnectionError
    return e


def get_msg_list(e):
    """
     数据粗提取，消息组生成器, 返回(mid - 消息数据)元组
    """
    try:
        items = e.xpath('//div[@node-type="item"]')
    except Exception as error:
        error_log('get_msg_list', error, 0)
        return False
    for item in items[::-1]:
        mid = item.get('mid')
        msg_name = item.findtext('.//p[@class="bubble_name"]')
        yield msg_name, mid, item


def data_clean_engine(msg_name, mid, item):
    """
    数据处理分发函数
    """
    target_data = data_target_filter(item)
    if target_data:
        data_type, msg_data_pre = target_data
        data_clean_func = data_clean_func_reload(data_type)
        for i in range(1, 6):
            try:
                data_clean_func(msg_data_pre, msg_name)
                break
            except Exception as error:
                error_func = 'data_clean_func_{type}'.format(type=data_type)
                error_log(error_func, error, mid, i)


def data_target_filter(item):
    """
    筛选目标文件类型消息
    :param item: 消息整体结构
    :return: 消息内容结构
    """
    msg_cont = item.find('.//div[@class="cont"]')
    for data_type, target in target_type.items():
        msg_data_pre = msg_cont.find(target.pattern)
        if msg_data_pre is not None:
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
    global sum_text
    file_path = get_file_path(msg_name, 'TEXT')
    msg_text = msg_data_pre.text
    if not msg_text:
        msg_text = '<表情>\n'
    else:
        msg_text += '\n'
    with open(file_path, 'a', encoding='utf8') as f:
        f.write(msg_text)
    sum_text += 1


def image_type_data_clean(msg_data_pre, msg_name):
    """
    图片类型数据清洗
    :param msg_data_pre: 消息内容结构
    :param msg_name: 发布人
    """
    global sum_img
    data_url = msg_data_pre.xpath('.//ul//a/@href')[1]
    r = requests.get(data_url, headers=headers)
    file_path = get_file_path(msg_name, 'IMG')
    with open(file_path, 'wb') as f:
        f.write(r.content)
    sum_img += 1


def audio_type_data_clean(msg_data_pre, msg_name):
    """
    音频类型数据清洗
    :param msg_data_pre: 消息内容结构
    :param msg_name: 发布人
    """
    global sum_audio
    data_url = msg_data_pre.xpath('.//a[last()]/@href')[0]
    r = requests.get(data_url, headers=headers)
    file_path = get_file_path(msg_name, 'AUDIO')
    with open(file_path, 'wb') as f:
        f.write(r.content)
    sum_audio += 1


def data_clean_func_reload(data_type):
    """
    数据清洗函数重载
    :param data_type: 数据类型
    :return: 数据清洗函数
    """
    target = target_type[data_type]
    return globals()[target.clean_func]


def error_log(func, error, mid, times=0):
    """
    错误记录
    """
    print(u'程序错误，请将 etc 文件夹发送给司马咔咔 simadad@sina.com 帮助改进程序')
    error_file = r'{path}\error.txt'.format(path=group_path_etc)
    with open(error_file, 'a') as f:
        f.write(u'mid：{mid}\tfunc：{func}\ttype：{type}\ttimes：{times}\n{e}\n\n'.format(
            e=str(error),
            mid=mid,
            times=times,
            type=type(error),
            func=func
        ))


def thr_router():
    """
    调度线程
    """
    global mid_off, is_loop_finished, error_shut_down
    _earliest_mid = mid = mid_on
    while True:
        q_router_to_process.put(mid)
        mid_items = q_process_to_router.get()
        if not mid_items:
            print(u'程序中断\n网络信号不稳定，请回车退出，稍后再试。')
            error_shut_down = True
            mid_off = mid
            break
        for msg_name, mid, item in mid_items:
            if not target_names or msg_name in target_names:
                thr = pool_items.submit(data_clean_engine, msg_name, mid, item)
                ts_items.append(thr)
            if mid == mid_off or program_pause:
                print(u'程序中止')
                if mid == mid_off:
                    print(u'恭喜，本次数据爬取完毕！')
                    is_loop_finished = True
                q_router_to_process.put(False)
                mid_off = mid
                return
        if _earliest_mid == mid or program_pause:
            print(u'程序中止')
            if _earliest_mid == mid:
                print(u'恭喜，本次数据爬取完毕！')
                is_loop_finished = True
            q_router_to_process.put(False)
            mid_off = mid
            break
        else:
            _earliest_mid = mid
            time.sleep(random.random()*sleep_times)


def thr_process():
    """
    进度线程
    """
    times = 0
    while True:
        # 从调度线程获取 mid，获取值为 False，循环结束
        mid = q_router_to_process.get()
        log_print = u'本次获取数据\t文字条目：{text:<10}图片条目：{img:<10}音频条目：{audio:<10}暂停请回车。'.format(
            text=sum_text,
            img=sum_img,
            audio=sum_audio
        )
        print(log_print)
        if mid is False:
            print(u'回车结束程序。')
            break
        try:
            e_root = get_e(mid)
        except ConnectionError as error:
            times += 1
            error_log('thr_process', error, mid, times)
            if times <= reconnect_times:
                q_router_to_process.put(mid)
                continue
            else:
                q_process_to_router.put(False)
                break
        msg_list = get_msg_list(e_root)
        q_process_to_router.put(msg_list)
        times = 0


def mid_save():
    """
    mid 信息储存
    """
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
    group_path_etc, is_first_time = init_root_dir()
    is_continue = get_is_continue()
    mid_on, mid_off = init_mid()
    if mid_on == mid_off:
        input(u'暂无新数据，回车退出程序\n')
    else:
        sum_text = sum_img = sum_audio = 0
        error_shut_down = is_loop_finished = program_pause = False
        q_router_to_process = Queue(1)
        q_process_to_router = Queue(1)
        q_router_to_source = Queue(1)
        pool_items = ThreadPoolExecutor(20)
        ts_items = []
        sleep_times = 1
        ts = [Thread(target=thr_process, name='thr_process'), Thread(target=thr_router, name='thr_router')]
        # ------------------ init off ------------------------
        print('LOOP ON:')
        for t in ts:
            t.start()
        input()
        program_pause = True
        for t in ts:
            t.join()
        wait(ts_items)
        print('LOOP OFF')
        mid_save()
    print(u'退出程序')
