import re

from pyquery import PyQuery


async def _doc_get_abs_url(url, pq, tag='a', attr='href'):
    for _ in pq(tag):
        el = pq(_)
        _url = el.attr('href')
        if not _url:
            continue
        _url = _url.strip()
        pl = re.search(r'^(https|http)', _url)
        if pl:
            pl = pl.group(1)
        if not pl:
            pl = re.search(r'^(https|http)', url)
            if pl:
                pl = pl.group(1)
        if _url:
            if re.match(r'^#', _url):
                continue
            if not re.match(r'^http', _url):
                if re.match(r'^//', _url):
                    _url = pl + ':' + _url
                else:
                    _url = re.search('^(http(s{0,1})://(\w*\.)+\w+)', url.strip()).group(0) + _url
            el.attr(attr, _url)
    return pq


async def get_pq_doc(url, html):
    pq = PyQuery(html)
    url = str(url)
    pq = await _doc_get_abs_url(url, pq, tag='a', attr='href')
    pq = await _doc_get_abs_url(url, pq, tag='img', attr='src')
    return pq

