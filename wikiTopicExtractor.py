import json
import pathlib
import time
import datetime
import sys
import os
import bz2
from opencc import OpenCC
from requests_html import HTMLSession
from tqdm import tqdm
import logging

logging.basicConfig(format='%(levelname)s : %(asctime)s : %(message)s', filename='completed.log', level=logging.INFO)
# 可以爬取階層架構的pair以及頁面內容
class WikiCrawler(object):
    """docstring for WikiCrawler"""
    def __init__(self):
        # super(WikiCrawler, self).__init__()
        self.folderName = 'pairfile'
        self.domain = 'https://zh.wikipedia.org'
        self.count = 2 # at least 2, because root and leaf
        self.height = 0
        self.visitList = []
        self.dataList = []
        self.keyword = ''
        self.dataDict = {}
        self.contentDict = {}
        self.opencc = OpenCC('s2t')
        sys.setrecursionlimit(1000000)

    def getName(self, item):
        name = ''
        if '台湾' in item.text or \
            '台灣' in item.text:
            name = ((self.opencc.convert(item.text)).replace('臺灣', '台灣')).replace(u'\u200e', u'')
        elif '台' in item.text:
            index = item.text.find('台')
            tmp = list(self.opencc.convert(item.text))
            tmp[index] = '台'
            name = (''.join(tmp)).replace(u'\u200e', u'')
        else:
            name = (self.opencc.convert(item.text)).replace(u'\u200e', u'')
        return name

    def nameFiltering(self, key):
        if 'Template:' not in key and \
            'Wikipedia:' not in key and \
            'User:' not in key and \
            'User talk:' not in key and \
            'Talk:' not in key and \
            'talk:' not in key and \
            'Template talk:' not in key:
            return True
        else:
            return False

    def loop(self, res, keyword):
        with HTMLSession() as sess:
            if res.url not in self.visitList:
                self.visitList.append(res.url)
            else:
                print('return')
                return

            for subCategory in res.html.find('.CategoryTreeLabelCategory'):
                subCategoryName = self.getName(subCategory)
                self.dataList.append(('Category:'+keyword, 'Category:'+subCategoryName))
                print(1, ('Category:'+keyword, 'Category:'+subCategoryName))

                innerUrl = self.domain+subCategory.attrs['href']
                try:
                    innerRes = sess.get(innerUrl)
                except:
                    print("ConnectionError, wait for 60s ...")
                    print("url:", innerUrl)
                    time.sleep(60)
                    innerRes = sess.get(innerUrl)

                if not innerRes.ok:
                    print("ResponseError, wait for 60s ...")
                    print('Response code:', innerRes.status_code)
                    print("url:", innerUrl)
                    time.sleep(180)
                    innerRes = sess.get(innerUrl)

                if not innerRes.html.find('.CategoryTreeLabelCategory, #mw-pages a'):
                    if not innerRes.html.find('p'):
                        if not innerRes.html.find('#SoftRedirect a'):
                            print("Get empty innerRes, wait for 60s ...")
                            print("url:", innerUrl)
                            time.sleep(60)
                            innerRes = sess.get(innerUrl)
                        else:
                            innerUrl = self.domain+innerRes.html.find('#SoftRedirect a')[0].attrs['href']
                            if innerUrl[:-2] not in self.visitList: # redirect url後面會加上#.
                                # ex: https://zh.wikipedia.org/wiki/Category:台灣藝術大學校友
                                redirectName = innerRes.html.find('#SoftRedirect a')[0].text.strip() # Category:台灣藝術大學校友
                                index = redirectName.find(':')
                                subCategoryName = redirectName[index+1:] # 台灣藝術大學校友
                                innerRes = sess.get(innerUrl)
                            else:
                                pass

                if innerRes.html.find('.CategoryTreeLabelCategory'):
                    self.count += 1
                    self.loop(innerRes, subCategoryName)
                else:
                    if innerRes.html.find('#mw-pages a'):
                        flag = False
                        while(True):
                            if self.opencc.convert(innerRes.html.find('#mw-pages a')[-1].text) == '下一頁）':
                                for page in innerRes.html.find('#mw-pages a'):
                                    if '下一頁）' not in self.opencc.convert(page.text) and '上一頁）（' not in self.opencc.convert(page.text):
                                        flag = True
                                        key = self.getName(page)
                                        if self.nameFiltering(key):
                                            self.dataList.append(('Category:'+subCategoryName, key))
                                            print(4, ('Category:'+subCategoryName, key))

                                nextPageUrl = 'https://zh.wikipedia.org'+innerRes.html.find('#mw-pages a')[-1].attrs['href']
                                innerRes = sess.get(nextPageUrl)
                            else:
                                for page in innerRes.html.find('#mw-pages a'):
                                    if '下一頁）' not in self.opencc.convert(page.text) and '上一頁）（' not in self.opencc.convert(page.text):  
                                        key = self.getName(page)
                                        if self.nameFiltering(key):
                                            self.dataList.append(('Category:'+subCategoryName, key))
                                            if flag:
                                                print(4, ('Category:'+subCategoryName, key))
                                            else:
                                                print(2, ('Category:'+subCategoryName, key))
                                break

            if res.html.find('#mw-pages a'):
                flag = False
                while(True):
                    if self.opencc.convert(res.html.find('#mw-pages a')[-1].text) == '下一頁）':
                        for page in res.html.find('#mw-pages a'):
                            if '下一頁）' not in self.opencc.convert(page.text) and '上一頁）（' not in self.opencc.convert(page.text):
                                flag = True
                                key = self.getName(page)
                                if self.nameFiltering(key):
                                    self.dataList.append(('Category:'+keyword, key)) # subCategoryName
                                    print(5, ('Category:'+keyword, key)) # subCategoryName

                        nextPageUrl = 'https://zh.wikipedia.org'+res.html.find('#mw-pages a')[-1].attrs['href']
                        res = sess.get(nextPageUrl)
                    else:
                        for page in res.html.find('#mw-pages a'):
                            if '下一頁）' not in self.opencc.convert(page.text) and '上一頁）（' not in self.opencc.convert(page.text):
                                key = self.getName(page)
                                if self.nameFiltering(key):
                                    self.dataList.append(('Category:'+keyword, key)) # subCategoryName
                                    if flag:
                                        print(5, ('Category:'+keyword, key)) # subCategoryName
                                    else:
                                        print(3, ('Category:'+keyword, key)) # subCategoryName
                        break

        if self.count > self.height:
            self.height = self.count
        self.count = 2

    def start(self, keyword):
        # 爬取階層關係架構
        self.keyword = keyword
        with HTMLSession() as sess:
            url = 'https://zh.wikipedia.org/wiki/Category:{0}'.format(self.keyword)
            try:
                res = sess.get(url)
            except:
                print("ConnectionError, wait for 60s ...")
                print("url:", url)
                time.sleep(60)
                res = sess.get(url)

            if not res.ok:
                print("ResponseError, wait for 60s ...")
                print('Response code:', res.status_code)
                print("url:", url)
                time.sleep(180)
                res = sess.get(url)

            startTime = datetime.datetime.now()
            if res.html.find('.CategoryTreeLabelCategory'):
                self.loop(res, keyword)
            else:
                print('No data.')
            endTime = datetime.datetime.now()

        if self.dataList:
            print('Time:', str(endTime - startTime))
            pathlib.Path(self.folderName).mkdir(parents=True, exist_ok=True)
            json.dump(self.dataList, open('{0}/{1}_pair.json'.format(self.folderName, self.keyword), 'w', encoding='utf-8'), ensure_ascii=False, indent=4)
            print('共儲存 {0} 對Pair於 {1}/{2}_pair.json'.format(len(self.dataList), self.folderName, self.keyword))
            logging.info('{0}_pair.json Time --> {1}'.format(self.keyword, str(endTime - startTime)))
            logging.info('{0}_pair.json -------> {1} pairs.'.format(self.keyword, len(self.dataList)))
        else:
            print('No data.')
        print("Maximum Height:", self.height)

    def convertToZh(self):
        # 將完整的rawText.xml轉換為繁體中文並儲存於zh_rawData.txt (需花費較長時間)
        with open('rawText.xml', 'r', encoding='utf-8') as file, \
            open('zh_rawText.txt', 'w', encoding='utf-8') as ofile:
            print('Load rawData.xml ...')
            rawData = file.read()
            print('Convert to zh_rawData.xml ...')
            self.zh_rawData = self.opencc.convert(rawData)
            ofile.write(self.zh_rawData)

    def getDataDict(self):
        # 檢查dataDict.json是否存在，已存在則讀取檔案，否則建立檔案
        if os.path.isfile(os.getcwd()+'/dataDict.json'):
            print('Load dataDict.json ...')
            with open('dataDict.json', 'r') as file:
                self.dataDict = json.load(file)
        else:
            print('dataDict.json is not found!')
            print('Create dataDict.json ...')
            for root, dirs, files in tqdm(os.walk('extracted'), ascii=True, desc='folders'): # extracted 為資料夾名稱
                for file in tqdm(files, ascii=True, desc='files'):
                    with bz2.BZ2File(os.path.join(root, file), 'r') as file: # , 'rb'
                        data = ''
                        title = ''
                        for line in file:
                            content = line.decode('utf-8').replace('\n', '')
                            if content:
                                if 'title="' in content and '">' in content:
                                    index = content.find('title="')
                                    title = self.opencc.convert(content[index+7:-2])
                                elif self.opencc.convert(content) == title:
                                    continue
                                else:
                                    if '</doc>' in content and data is not '':
                                        data = self.opencc.convert(data)
                                        self.dataDict[title] = data
                                        data = ''
                                    elif '<doc' not in content:
                                        data += content+'\n'
                                    else:
                                        print('"{0}" got error !'.format(title))
            json.dump(self.dataDict, open('dataDict.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=4)
            print('dataDict.json has been created.')

    def getContentDict(self, keyword):
        self.keyword = keyword
        filename = keyword+'_pair.json'
        title_list = []
        contentDict = {}
        # 查看是否已建立"keyword"_pair.json，若已建立則讀取檔案，否則爬取階層關係架構
        if not os.path.isfile(os.getcwd()+'/{0}/{1}'.format(self.folderName, filename)):
            self.start(keyword)

        startTime = datetime.datetime.now()
        with open('{0}/{1}'.format(self.folderName, filename), 'r', encoding='utf-8') as file:
            pair_list = json.load(file)
        # 將頁面名稱保存
        for item in tqdm(pair_list, ascii=True):
            if 'Category:' not in item[0] and item[0] not in title_list:
                title_list.append(item[0])
            if 'Category:' not in item[1] and item[1] not in title_list:
                title_list.append(item[1])

        # 讀取dataDict.json，裡面包含所有wiki頁面之內容，若已建立則讀取檔案，否則建立檔案(需花費較長時間)
        self.getDataDict()
        print('Loading Time:', str(datetime.datetime.now() - startTime))
        startTime = datetime.datetime.now()
        for title in tqdm(title_list, ascii=True):
            # 直接到dataDict.json中查詢
            if title in self.dataDict:
                self.contentDict[title] = self.dataDict[title]
                # print(title)
            else:
                # 若dataDcit.json中有缺漏此頁面則到網頁上爬取
                with HTMLSession() as sess:
                    url = self.domain+'/wiki/{0}'.format(title)
                    try:
                        res = sess.get(url)
                    except:
                        print("ConnectionError, wait for 60s ...")
                        print("url:", url)
                        time.sleep(60)
                        res = sess.get(url)

                    content = ''
                    for pageContent in res.html.find('p'):
                        content += self.opencc.convert(pageContent.text)
                    self.contentDict[title] = content
                    # print(title)

        endTime = datetime.datetime.now()
        print('Time:', str(endTime - startTime))
        pathlib.Path('jsonfile/').mkdir(parents=True, exist_ok=True)
        json.dump(self.contentDict, open('jsonfile/{0}.json'.format(keyword), 'w', encoding='utf-8'), ensure_ascii=False, indent=4)
        print('共儲存 {0} 篇文章於 {1}/{2}.json'.format(len(self.contentDict), 'jsonfile', self.keyword))
        logging.info('{0}.json Time -------> {1}'.format(self.keyword, str(endTime - startTime)))
        logging.info('{0}.json ------------> {1} articles.'.format(self.keyword, len(self.contentDict)))


if __name__ == '__main__':
    keyword = '台灣奧運運動員'
    crawler = WikiCrawler()
    crawler.getContentDict(keyword)