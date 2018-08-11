import json
import re
import itertools

from datetime import datetime
from aiohttp.client import ClientSession
from dataclasses import dataclass
from asyncio import sleep
from pyquery import PyQuery
from types import FunctionType
from asyncio import Lock

from framework.core.spider import Spider, UrlTask
from framework.utils.limit import Limit
from framework.utils.pydoc import get_pq_doc

from db import Video, VideoInfo, VideoNumber


async def find_videos(url):
    try:
        for _ in range(5):
            async with ClientSession() as session:
                async with session.get(url) as response:
                    _json = await response.json()
                    pq = PyQuery(_json['data'])

                    doc = pq('.num-tab-main a[data-num]')
                    links = {}

                    for x in doc:
                        x = pq(x)
                        link = x.attr('href')
                        if not link.startswith('#'):
                            # print(x.attr('data-num'))
                            links[x.attr('data-num')] = link
                    temp = []
                    for name in sorted(links.keys(), key=lambda x: int(x)):
                        temp.append(dict(name=name, link=links[name]))
                    return temp
    except:
        return None


@dataclass(init=True)
class Response:
    url: str = None
    save: dict = None
    text: str = None
    doc: any = None
    callback: FunctionType = None


class MySpider(Spider):
    _write_lock = Lock()

    max_works = 100
    loop = None # event loop
    limit = Limit()
    retry_count = 10
    retry_time = 5
    limit_time = 600
    limit_count = 12000
    limit_wait = True
    output = False

    async def get_url_text(self, url):
        async with ClientSession() as se:
            async with se.get(url) as resp:
                return await resp.text()

    async def on_process(self, data: UrlTask):
        await self.limit.wait(self.limit_time, self.limit_count, wait=self.limit_wait)

        # 重试次数
        for _ in range(self.retry_count):
            try:
                doc_text = await self.get_url_text(data.url)
                break
            except:
                doc_text = None
            await sleep(self.retry_time)

        if not doc_text and self.output:
            print('error: %s' % data.url)
            return
        else:
            print('success: %s' % data.url)

        try:
            result = await data.callback(Response(url=data.url, text=doc_text, save=data.save,
                                                  doc=await get_pq_doc(url=data.url, html=doc_text),
                                                  callback=data.callback))
        except Exception:
            result = None

        # 返回保存
        if result:
            try:
                data.save = result
                await self.on_save(data)
            except:
                pass

    async def on_start(self):
        print('%s: start' % datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S'))
        await self.crawl('http://www.360kan.com/dianshi/list', callback=self.index_page, priority=1)

    async def on_exit(self):
        print('%s: exit' % datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S'))

    async def on_save(self, data: Response):
        url = data.url
        save = data.save
        func = data.callback
        if func == self.get_video_info and save:
            info = save['info']
            async with self._write_lock:
                video = Video.objects(cid=info['cid']).upsert_one(cid=info['cid'])

                temp = []
                for x in info['videos']:
                    tv_name, _videos = x['name'], x['links']
                    _links = []
                    for __ in _videos:
                        k = __['name']
                        v = __['link']
                        _links.append(VideoNumber(name=k, link=v))

                    temp.append(VideoInfo(name=tv_name, links=_links))

                if not video.update_time or video.videos != temp:
                    video.update_time = datetime.strftime(datetime.now(), "%Y-%m-%d")

                if temp:
                    video.topcls_name = info['topcls_name']
                    if info['subcls_name'] not in video.subcls_name:
                        video.subcls_name.append(info['subcls_name'])
                    video.title = info['title']
                    video.score = info['score']
                    video.pic = info['pic']
                    video.year = info['year']
                    video.area = info['area']
                    video.director = info['director']
                    video.actor = info['actor']
                    video.desc = info['desc']
                    video.update_to = info['update_to']
                    video.all_num = info['all_num']

                    video.videos = temp
                    video.save()

    async def index_page(self, response):
        topcls_name = response.doc('dl.s-filter-item:eq(0) .on').text()
        await self.crawl(response.url, callback=self.get_tag_list, save=dict(topcls_name=topcls_name), priority=2)
        for each in response.doc('dl.s-filter-item:eq(0) dd.item > a').items():
            await self.crawl(each.attr.href, callback=self.get_tag_list, save=dict(topcls_name=each.text()), priority=2)

    async def get_tag_list(self, response):
        for each in response.doc('dl.s-filter-item:gt(0)').items():
            c_name = each.find('dt').text()
            if c_name.find('明星') == -1 and c_name.find('频道') == -1:
                for each in response.doc(each).find('dd.item > a').items():
                    if each.text().find('全部') == -1:
                        await self.crawl(each.attr.href, callback=self.get_videos,
                                   save=dict(topcls_name=response.save['topcls_name'], subcls_name=each.text()),
                                         priority=3)

    async def get_videos(self, response):
        for each in response.doc("a.js-tongjic").items():
            await self.crawl(each.attr.href, callback=self.get_video_info,
                             save=dict(topcls_name=response.save['topcls_name'],
                                       subcls_name=response.save['subcls_name']),
                             priority=4)
        el = response.doc("#js-ew-page > a:last")
        if el.text().find('下一页') > -1:
            await self.crawl(el.attr.href, callback=self.get_videos,save=dict(topcls_name=response.save['topcls_name'],
                                                                              subcls_name=response.save['subcls_name']),
                             priority=4)

    async def get_video_info(self, response):
        info = dict()
        info['topcls_name'] = response.save['topcls_name']
        info['subcls_name'] = response.save['subcls_name']
        info['title'] = response.doc('div.title-left h1').text()
        info['score'] = response.doc('div.title-left span.s').text()
        info['pic'] = response.doc('a.s-cover-img img').attr.src

        tags_info = {}
        for each in response.doc("#js-desc-switch p.item").items():
            name = each.find('span').text()
            content = each.text().replace(name, '')
            name = name.replace("：", "")
            temp = []
            for x in ' '.join(content.split()).split('/'):
                temp.append(x)
            tags_info[name] = ' '.join(temp)

        info['year'] = tags_info.get('年代', None) if tags_info.get('年代', None) else ''
        info['area'] = tags_info.get('地区', None) if tags_info.get('地区', None) else ''
        info['director'] = tags_info.get('导演', None).split() if tags_info.get('导演', None) else []
        if tags_info.get('演员', None):
            info['actor'] = tags_info.get('演员', None).split()
        if tags_info.get('主持', None):
            info['actor'] = tags_info.get('主持', None).split()
        if tags_info.get('人物', None):
            info['actor'] = tags_info.get('人物', None).split()

        el = response.doc("#js-desc-switch .item-desc.js-close-wrap")
        info['desc'] = el.text()
        info['desc'] = info['desc'].replace(response.doc(el).find('span').text(), "").replace(
            response.doc(el).find('a').text(), "")

        info['update_to'] = '全集'
        info['all_num'] = '未知'

        info['videos'] = []
        if response.save.get('topcls_name', '').find('电视剧') > -1:
            info['update_to'] = '更新至 ' + response.doc('p.tag > span').text()
            info['all_num'] = response.doc('p.tag').text()
            if info['all_num'].find('/') > -1:
                info['all_num'] = info['all_num'].split('/')[1]

        elif response.save.get('topcls_name', '').find('电影') > -1:  # OJBK
            info['videos'] = []
            for el in response.doc('.top-list-zd a[data-daochu]').items():
                info['videos'].append(dict(name=el.text(), links=[dict(name=el.text(), link=el.attr.href)]))

        if response.save.get('topcls_name', '').find('动漫') > -1:
            info['update_to'] = response.doc('p.tag').text()
            info['all_num'] = ''

        if response.save.get('topcls_name', '').find('综艺') > -1:
            links = []
            for x in response.doc('#js-site-wrap li'):
                x = response.doc(x)
                links.append(dict(name=x.attr('title'), link=x.find('a:eq(0)').attr('href')))

            info['videos'] = [dict(name=info['title'], links=links)]

        if response.save.get('topcls_name', '').find('动漫') > -1:
            category = '4'
        elif response.save.get('topcls_name', '').find('电视剧') > -1:
            category = '2'
        temp = re.search(r'var serverdata(.|\n)*?<\/script>', response.text)

        try:
            v_id = re.search(r'(\w+)\.html', response.url).group(1)
            info['cid'] = v_id
        except:
            return None
        if temp:
            text = temp.group(0)
            if response.save.get('topcls_name', '').find('动漫') > -1 or response.save.get('topcls_name', '').find(
                    '电视剧') > -1:
                v_info = ''

                try:
                    v_info = re.search(r'playsite:(\[\{.*?\}\])\,', text).group(1)
                except:
                    # 空剧集可能捕获不到, 丢回队列吧
                    await self.crawl(el.attr.href, callback=self.get_videos,
                                     save=dict(topcls_name=response.save['topcls_name'],
                                               subcls_name=response.save['subcls_name']), priority=4)
                    return None
                v_info = json.loads(v_info)

                v_video = []
                for field in v_info:
                    url = 'http://www.360kan.com/cover/switchsite?site=' + \
                          field['ensite'] + '&id=' + v_id + '&category=' + category
                    v = await find_videos(url)
                    if v:
                        v_video.append(dict(name=field['cnsite'], links=v))
                info['videos'] = v_video
        return dict(info=info)
