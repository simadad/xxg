# 小戏骨应援相关项目

### 项目列表：
1. 微博群爬虫 `wb.py`


### 项目简介
#### 微博群爬虫
爬取微博群中所有消息，并储存至本地。
##### 可配置参数：
1. 需要抓取的用户（比如“群主”、“小戏骨”）
    `target_names = []`
    空值获取抓取群内全部成员
1. 需要抓取的群 id 及对应群文件储存地址
    `gid = ''`
    配置 `gid` 的同时，需要配置 `gid_dict` 
    可从**开发者工具获取**

1. 需要获取的数据类型
    `target_type = {...}`
    **（默认获取全部种类数据，不需要的数据直接从代码中注释即可。）**
    - `AUDIO` 音频数据
    - `IMG` 图片数据
    - `TEXT` 文本数据
1. 数据存储根目录
    `root_dir = ''` 
    空值默认根目录为项目文件所在目录
1. 起始消息 id        
    `mid = ''`
    起始消息 id，必须提供，可从**开发者工具获取**
1. 登录状态信息
    `Cookie = ''`
    必须提供，可从**开发者工具获取**

##### 项目运行流程简介
1. 生成环境配置
    1. `Python3` 安装——[点击下载][1]
    1. `git` 安装——[点击下载][2]
    1. 克隆仓库代码 `git clone https://github.com/simadad/xxg.git`
    1. 安装依赖包 `pip install -r requirements.txt`
1. 项目初始化配置
    1. 登录网页版微博，获取并配置 Cookie
    1. 获取并配置群 id 及 `{qid: 群目录}` ——`gid`、`gid_dict`
    1. 获取并配置起始消息 id——`mid`
    1. 其余特殊需求配置 `target_names`、`target_type `、`root_dir`
1. 运行项目 `python wb.py`

[1]: https://www.python.org/downloads/release/python-352/    
[2]: https://git-scm.com/downloads
