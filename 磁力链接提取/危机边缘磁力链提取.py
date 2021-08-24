import time
import urllib
import os
import requests
from bs4 import BeautifulSoup
def getHTMLText(url):
    try:
        #获取服务器的响应内容，并设置最大请求时间为6秒
        res = requests.get(url, timeout = 6)
        #判断返回状态码是否为200
        res.raise_for_status()
        #设置该html文档可能的编码
        res.encoding = res.apparent_encoding
        #返回网页HTML代码
        return res.text
    except:
        return 'Error!'
def check(T):
    for b in T.find_all('a'):
        return b.get('href')
def main():
    url='https://www.115mj.com/vod-detail-id-3315.html'
    soup = BeautifulSoup(getHTMLText(url), 'html.parser')
    for a in soup.find_all("div",class_='mox'):
        break
    for b in a.find_all("div",class_='dwww'):
        c=check(b)
        if c!=None:
            print(c)
main()
    

