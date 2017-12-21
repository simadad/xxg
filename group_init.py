import json
from collections import namedtuple

with open('settings.json', encoding='utf8') as _:
    settings = json.load(_)

gid_dict = settings['groups']
root_dir = settings['root_dir']
target_names = settings['target_names']
reconnect_times = settings['reconnect_times']
sleep_times = settings['sleep_times']
thr_pool_nums = settings['thr_pool_nums']
url_pre = "https://weibo.com/aj/groupchat/getdialog?"


def _get_group_id():
    group_items = {str(n + 1): group for n, group in enumerate(gid_dict)}
    for index, group_name in group_items.items():
        print('{index}:\t{group_name}'.format(index=index, group_name=group_name))
    while 1:
        try:
            choice = input(u'请输入要爬取的群所对应的序号\n')
            group = group_items[choice]
            return group
        except KeyError:
            print(u'请输入正确序号')


group_name = _get_group_id()
gid = gid_dict[group_name]

Cookie = settings['cookie']


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

headers = {
    'Cookie': Cookie,
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36',
    'Connection': 'keep-alive',
}
