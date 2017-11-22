import os
import json
import time
import requests
from lxml.html import etree
from collections import namedtuple
from threading import Thread
# from testools.declog import log_this

# --------------- ��ʼ���� ---------------
# Ŀ���û���
target_names = []
# ��Ŀ�����ã���ֵĬ��Ϊ��ǰ��Ŀ�ļ���
root_dir = r'C:\Users\AAA\Documents'
# ��ʼ��Ϣ id
mid = '4176660045876012'
# Ⱥ id
gid = '4176659651822678'
Cookie = 'SINAGLOBAL=3435881701430.0503.1511069446373; wb_cmtLike_2373503412=1; UOR=www.google.com,weibo.com,www.google.com.hk; wvr=6; YF-Ugrow-G0=b02489d329584fca03ad6347fc915997; SSOLoginState=1511263953; SCF=AnialW-1WRKw7QjY2BjUKntnIU-jjz4LSUlkHBo06bPBg6z68mgoO_8yFKZbIBf99pfa1WEgeSUqAUzcsIAmfPk.; SUB=_2A253EH6BDeThGeRN7FEU8C3Iyj6IHXVUZNdJrDV8PUNbmtBeLRHNkW9NHetkT2O5Usavvo662EJT8RqbIf1R3-LP; SUBP=0033WrSXqPxfM725Ws9jqgMF55529P9D9W54ln0wJQEAZ8ux9eaQd.q75JpX5KzhUgL.Foz0S0efeheXeKz2dJLoIEBLxK-L12qLBonLxK.LBK.LB-eLxK-L1KzL1KBLxK-L1KzL1KBt; SUHB=0ElLrvUIqk3efQ; ALF=1542799952; YF-V5-G0=b2423472d8aef313d052f5591c93cb75; _s_tentry=login.sina.com.cn; Apache=6136087806431.84.1511263958335; ULV=1511263958378:6:6:6:6136087806431.84.1511263958335:1511230013851; YF-Page-G0=ed0857c4c190a2e149fc966e43aaf725'
# ----------------- ���ý��� ����������������

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
# ����Ԫ�� --- ƥ������ʽ���������������ļ���չ��
TargetChoice = namedtuple('TargetChoice', ('pattern', 'clean_func', 'ext'))

# Ŀ���������� - ����Ԫ����ձ�
target_type = {
    'AUDIO': TargetChoice('.//div[@class="private_player_mod"]', 'audio_type_data_clean', 'amr'),
    'IMG': TargetChoice('.//div[@class="pic_b_mod"]', 'image_type_data_clean', 'jpg'),
    'TEXT': TargetChoice('.//p[@class="page"]', 'text_type_data_clean', 'txt'),
}

# Ⱥ gid - ��ַ���ձ�
gid_dict = {
    '4101723897939433': '����Ⱥ',
    '4176659651822678': '����Ⱥ'
}

headers = {
    'Cookie': Cookie,
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36',
    'Connection': 'keep-alive',
}


def create_root_dir():
    """
    ����Ŀ¼��
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
    �����û���Ŀ¼
    :param msg_name: ������
    :param data_type: ��������
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


# @log_this
def _get_url():
    """
    ���ɷ��ʵ�ַ
    """
    data['mid'] = mid
    data['__rnd'] = __rnd()
    return url_pre + '&'.join(['{k}={v}'.format(k=k, v=v) for k, v in data.items()])


# @log_this
def __rnd():
    return str(int(time.time() * 1000))


# @log_this
def get_e():
    """
     ����ȫ�ֱ��� mid������ҳ�� etree ������
    """
    url = _get_url()
    # print('url:\t', url)
    r = requests.get(url, headers=headers)
    text = json.loads(r.text)
    html = text['data']['html']
    with open('ttt.html', 'w') as f:
        f.write(html)
    e = etree.HTML(html)
    return e


# @log_this
def get_msg_list(e):
    """
     ���ݴ���ȡ������ mid + ��Ϣ�飬���������
    """
    items = e.xpath('//div[@node-type="item"]')
    yield items[0].get('mid')
    for item in items:
        yield item


# @log_this
def info_fork(msg_list_pre):
    """
    �������������ݷֲ�
    :param msg_list_pre: mid<0> + msg_list<1-20> ���������
    :return: mid, ��Ϣ������
    """
    _mid = next(msg_list_pre)
    return _mid, msg_list_pre


# @log_this
def data_clean(_msg_list):
    """
    ���ݴ���ַ�����
    :param _msg_list: ��Ϣ������
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


# @log_this
def username_target_filter(_msg_list):
    """
    ɸѡĿ���û����͵���Ϣ
    :param _msg_list: ��Ϣ������
    :return: yield ��Ϣ item
    """
    for msg in _msg_list:
        msg_name = msg.findtext('.//p[@class="bubble_name"]')
        if not target_names or msg_name in target_names:
            msg_cont = msg.find('.//div[@class="cont"]')
            # print('msg_name, msg_cont_len:\t', msg_name, len(msg_cont))
            yield msg_name, msg_cont


# @log_this
def data_target_filter(msg_cont):
    """
    ɸѡĿ���ļ�������Ϣ
    :param msg_cont: ��Ϣ����ṹ
    :return: ��Ϣ���ݽṹ
    """
    for data_type, target in target_type.items():
        msg_data_pre = msg_cont.find(target.pattern)
        if msg_data_pre is not None:
            # print('data_type, pre_data_len:\t', data_type, len(msg_data_pre))
            return data_type, msg_data_pre


# @log_this
def text_type_data_clean(msg_data_pre, msg_name):
    """
    ��������������ϴ
    :param msg_data_pre: ��Ϣ���ݽṹ
    :param msg_name: ������
    :return:
    """
    # TODO �����������
    file_path = get_file_path(msg_name, 'TEXT')
    msg_text = msg_data_pre.text
    if not msg_text:
        msg_text = '<����>\n'
    else:
        msg_text += '\n'
    with open(file_path, 'a', encoding='utf8') as f:
        f.write(msg_text)
    print('text:\t', msg_text)


# @log_this
def image_type_data_clean(msg_data_pre, msg_name):
    """
    ͼƬ����������ϴ
    :param msg_data_pre: ��Ϣ���ݽṹ
    :param msg_name: ������
    """
    data_url = msg_data_pre.xpath('.//ul//a/@href')[1]
    r = requests.get(data_url, headers=headers)
    file_path = get_file_path(msg_name, 'IMG')
    with open(file_path, 'wb') as f:
        f.write(r.content)
    print('img:\t', data_url)


# @log_this
def audio_type_data_clean(msg_data_pre, msg_name):
    """
    ��Ƶ����������ϴ
    :param msg_data_pre: ��Ϣ���ݽṹ
    :param msg_name: ������
    """
    data_url = msg_data_pre.xpath('.//a[last()]/@href')[0]
    r = requests.get(data_url, headers=headers)
    file_path = get_file_path(msg_name, 'AUDIO')
    with open(file_path, 'wb') as f:
        f.write(r.content)
    print('audio:\t', data_url)
    return


# @log_this
def data_clean_func_reload(data_type):
    """
    ������ϴ��������
    :param data_type: ��������
    :return: ������ϴ����
    """
    target = target_type[data_type]
    return globals()[target.clean_func]


def error_log(error):
    """
    �����¼
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
        Thread(target=data_clean(msg_list)).start()
        print('LOOP OFF.')
        # break
