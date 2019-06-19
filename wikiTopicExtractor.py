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
logging.getLogger('requests').setLevel(logging.WARNING)
# 可以爬取階層架構的pair以及頁面內容
class WikiTopicExtractor(object):
    """docstring for WikiTopicExtractor"""
    def __init__(self):
        self.pairFolderName = 'pairfile'
        self.jsonFolderName = 'jsonfile'
        self.domain = 'https://zh.wikipedia.org'
        self.count = 2 # at least 2, because root and leaf
        self.height = 0
        self.zh_zh_count = 0
        self.zh_cn_count = 0
        self.cn_zh_count = 0
        self.cn_cn_count = 0
        self.zh_articles = 0
        self.cn_articles = 0
        self.visitList = []
        # self.init_visitList()
        self.dataList = []
        self.all_title_list = []
        self.topic = ''
        self.dataDict = {}
        self.dataDict_cn = {}
        self.contentDict = {}
        self.opencc = OpenCC('s2t')
        sys.setrecursionlimit(1000000)

    def init_visitList(self):
        with open('./topic_list.txt', 'r', encoding='utf-8') as file:
            for line in file.readlines():
                self.visitList.append(line.replace('\n', '').strip())
                
    def opencc_s2t(self, item):
        converted = ''
        if '台湾' in item or \
            '台灣' in item:
            converted = ((self.opencc.convert(item)).replace('臺灣', '台灣')).replace(u'\u200e', u'')
        elif '台' in item:
            index = item.find('台')
            tmp = list(self.opencc.convert(item))
            tmp[index] = '台'
            converted = (''.join(tmp)).replace(u'\u200e', u'')
        else:
            converted = (self.opencc.convert(item)).replace(u'\u200e', u'')
        return converted

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

    def appendToAllTitleList(self, article):
        if article not in self.all_title_list:
            self.all_title_list.append(article)

    def start(self, topic):
        # 爬取階層關係架構
        self.topic = topic
        with HTMLSession() as sess:
            url = 'https://zh.wikipedia.org/wiki/Category:{0}'.format(self.topic)
            try:
                res = sess.get(url)
            except:
                print('ConnectionError, wait for 120s ...')
                print('url:', url)
                time.sleep(120)
                res = sess.get(url)

            if not res.ok:
                delay_time = int()
                if res.status_code == 429:
                    delay_time = 180
                elif res.status_code == 404:
                    delay_time = 5
                else:
                    delay_time = 60
                print('Response error code: {0}, please wait for {1}s ...'.format(res.status_code, delay_time))
                print('url:', url)
                time.sleep(delay_time)
                res = sess.get(url)

            startTime = datetime.datetime.now()
            if res.html.find('.CategoryTreeLabelCategory'):
                self.loop(res, self.topic)
            else:
                print('No data.')
            endTime = datetime.datetime.now()

        if self.dataList:
            print('Pair Time:', str(endTime - startTime))
            pathlib.Path(self.pairFolderName).mkdir(parents=True, exist_ok=True)
            json.dump(self.dataList, open('{0}/{1}_pair.json'.format(self.pairFolderName, self.topic), 'w', encoding='utf-8'), ensure_ascii=False, indent=4)
            print('共儲存 {0} 對Pair於 {1}/{2}_pair.json'.format(len(self.dataList), self.pairFolderName, self.topic))
            logging.info('{0}_pair.json Time --> {1}'.format(self.topic, str(endTime - startTime)))
            logging.info('{0}_pair.json -------> {1} pairs.'.format(self.topic, len(self.dataList)))
        else:
            print('No data.')
            logging.info('{} does not get the data.'.format(self.topic))
        print("Maximum Height:", self.height)

    def loop(self, res, keyword):
        with HTMLSession() as sess:
            if res.url not in self.visitList:
                self.visitList.append(res.url)
            else:
                print('return')
                return

            for subCategory in res.html.find('.CategoryTreeLabelCategory'):
                subCategoryName = self.opencc_s2t(subCategory.text)
                self.dataList.append(('Category:'+keyword, 'Category:'+subCategoryName))
                print(1, ('Category:'+keyword, 'Category:'+subCategoryName))

                innerUrl = self.domain+subCategory.attrs['href']
                try:
                    innerRes = sess.get(innerUrl)
                except:
                    print('ConnectionError, wait for 120s ...')
                    print('url:', innerUrl)
                    time.sleep(120)
                    innerRes = sess.get(innerUrl)

                if not innerRes.ok:
                    delay_time = int()
                    if innerRes.status_code == 429:
                        delay_time = 180
                    elif innerRes.status_code == 404:
                        delay_time = 5
                    else:
                        delay_time = 60
                    print('Response error code: {0}, please wait for {1}s ...'.format(innerRes.status_code, delay_time))
                    print('url:', innerUrl)
                    time.sleep(delay_time)
                    innerRes = sess.get(innerUrl)

                if not innerRes.html.find('.CategoryTreeLabelCategory, #mw-pages a'):
                    if not innerRes.html.find('p'):
                        if not innerRes.html.find('#SoftRedirect a'):
                            print('Get empty innerRes, wait for 5s ...')
                            print('url:', innerUrl)
                            time.sleep(5)
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
                            try:
                                if self.opencc.convert(innerRes.html.find('#mw-pages a')[-1].text) == '下一頁）':
                                    for page in innerRes.html.find('#mw-pages a'):
                                        if '下一頁）' not in self.opencc.convert(page.text) and '上一頁）（' not in self.opencc.convert(page.text):
                                            flag = True
                                            key = self.opencc_s2t(page.text)
                                            if self.nameFiltering(key):
                                                self.dataList.append(('Category:'+subCategoryName, key))
                                                self.appendToAllTitleList(key) #####
                                                print(4, ('Category:'+subCategoryName, key))

                                    nextPageUrl = 'https://zh.wikipedia.org'+innerRes.html.find('#mw-pages a')[-1].attrs['href']
                                    innerRes = sess.get(nextPageUrl)
                                else:
                                    for page in innerRes.html.find('#mw-pages a'):
                                        if '上一頁）（下一頁）' not in self.opencc.convert(page.text):  
                                            key = self.opencc_s2t(page.text)
                                            if self.nameFiltering(key):
                                                self.dataList.append(('Category:'+subCategoryName, key))
                                                if flag:
                                                    self.appendToAllTitleList(key) #####
                                                    print(4, ('Category:'+subCategoryName, key))
                                                else:
                                                    self.appendToAllTitleList(key) #####
                                                    print(2, ('Category:'+subCategoryName, key))
                                    break
                            except:
                                print('(break in line 202)多頁之頁面發生問題於url:', innerRes.url)
                                break

            if res.html.find('#mw-pages a'):
                flag = False
                while(True):
                    try:
                        if self.opencc.convert(res.html.find('#mw-pages a')[-1].text) == '下一頁）':
                            for page in res.html.find('#mw-pages a'):
                                if '下一頁）' not in self.opencc.convert(page.text) and '上一頁）（' not in self.opencc.convert(page.text):
                                    flag = True
                                    key = self.opencc_s2t(page.text)
                                    if self.nameFiltering(key):
                                        self.dataList.append(('Category:'+keyword, key))
                                        self.appendToAllTitleList(key) #####
                                        print(5, ('Category:'+keyword, key))

                            nextPageUrl = 'https://zh.wikipedia.org'+res.html.find('#mw-pages a')[-1].attrs['href']
                            res = sess.get(nextPageUrl)
                        else:
                            for page in res.html.find('#mw-pages a'):
                                if '上一頁）（下一頁）' not in self.opencc.convert(page.text):
                                    key = self.opencc_s2t(page.text)
                                    if self.nameFiltering(key):
                                        self.dataList.append(('Category:'+keyword, key))
                                        self.appendToAllTitleList(key) #####
                                        if flag:
                                            self.appendToAllTitleList(key) #####
                                            print(5, ('Category:'+keyword, key))
                                        else:
                                            self.appendToAllTitleList(key) #####
                                            print(3, ('Category:'+keyword, key))
                            break
                    except:
                        print('多頁之頁面發生問題於url:', res.url)
                        break

        if self.count > self.height:
            self.height = self.count
        self.count = 2

    def convertToZh(self):
        # 將完整的rawText.xml轉換為繁體中文並儲存於zh_rawData.txt (需花費較長時間)
        if os.path.exists(os.path.join(os.getcwd(), 'zh_rawText.txt')):
            return

        with open('rawText.xml', 'r', encoding='utf-8') as file, \
            open('zh_rawText.txt', 'w', encoding='utf-8') as ofile:
            print('Load rawData.xml ...')
            rawData = file.read()
            print('Convert to zh_rawData.xml ...')
            self.zh_rawData = self.opencc.convert(rawData)
            ofile.write(self.zh_rawData)

    def getDataDict_total(self):
        # 檢查dataDict.json是否存在，已存在則讀取檔案，否則建立檔案
        if os.path.exists(os.path.join(os.getcwd(), 'dataDict_total.json')):
            print('Load dataDict_total.json ...')
            with open('dataDict_total.json', 'r', encoding='utf-8') as file:
                self.dataDict = json.load(file)
        else:
            print('dataDict_total.json is not found!')
            print('Create dataDict_total.json ...')
            for root, dirs, files in tqdm(os.walk('extracted'), ascii=True, desc='folders'): # extracted 為資料夾名稱
                for file in tqdm(files, ascii=True, desc='files'):
                    with bz2.BZ2File(os.path.join(root, file), 'r') as file: # , 'rb'
                        data = ''
                        title = ''
                        for line in file:
                            content = line.decode('utf-8').replace('\n', '').strip()
                            if content:
                                if 'title="' in content and '">' in content:
                                    index = content.find('title="')
                                    title = self.opencc_s2t(content[index+7:-2])
                                elif self.opencc_s2t(content) == title:
                                    continue
                                else:
                                    if '</doc>' in content and data is not '':
                                        data = self.opencc_s2t(data)
                                        self.dataDict[title] = data
                                        data = ''
                                    elif '<doc' not in content:
                                        if '</doc>' not in content:
                                            data += content+'\n'
                                    else:
                                        print('"{0}" got error !'.format(title))
            json.dump(self.dataDict, open('dataDict_total.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=4)
            print('dataDict_total.json has been created.')

    def getDataDict_zh_cn(self):
        # 檢查dataDict.json是否存在，已存在則讀取檔案，否則建立檔案
        if os.path.exists(os.path.join(os.getcwd(), 'dataDict_zh.json')) and \
            os.path.exists(os.path.join(os.getcwd(), 'dataDict_cn.json')):
            print('Load dataDict_zh.json ...')
            with open('dataDict_zh.json', 'r', encoding='utf-8') as file:
                self.dataDict = json.load(file)

            print('Load dataDict_cn.json ...')
            with open('dataDict_cn.json', 'r', encoding='utf-8') as file:
                self.dataDict_cn = json.load(file)
        else:
            print('dataDict_zh.json and dataDict_cn.json are not found!')
            print('Create dataDict_zh.json and dataDict_cn.json ...')
            for root, dirs, files in tqdm(os.walk('extracted'), ascii=True, desc='folders'): # extracted 為資料夾名稱
                for file in tqdm(files, ascii=True, desc='files'):
                    with bz2.BZ2File(os.path.join(root, file), 'r') as file: # , 'rb'
                        data = ''
                        title = ''
                        origin_title = ''
                        for line in file.readlines():
                            content = line.decode('utf-8').replace('\n', '')
                            if content:
                                if 'title="' in content and '">' in content:
                                    index = content.find('title="')
                                    origin_title = content[index+7:-2]
                                    title = self.opencc_s2t(content[index+7:-2])
                                    if title == origin_title:
                                        self.zh_articles += 1
                                    else:
                                        self.cn_articles += 1
                                elif self.opencc_s2t(content) == title:
                                    continue
                                else:
                                    if '</doc>' in content and data is not '':
                                        # data = self.opencc_s2t(data)
                                        if title == origin_title: # 繁體標題
                                            self.dataDict[origin_title] = self.opencc_s2t(data)
                                        else: # 簡體標題
                                            self.dataDict_cn[origin_title] = data
                                        data = ''
                                    elif '<doc' not in content:
                                        content_list = content.replace('，', '。').split('。')
                                        new_content = ''
                                        for sentc in content_list:
                                            sentc = sentc.replace('\n', '').strip()
                                            if sentc and '</doc>' not in sentc:
                                                if title == origin_title:
                                                    if self.opencc_s2t(sentc) == sentc: # 繁體標題中之繁體句子
                                                        # new_content += sentc+' '
                                                        self.zh_zh_count += 1
                                                    else: # 繁體標題中之簡體句子
                                                        self.zh_cn_count += 1
                                                else:
                                                    if self.opencc_s2t(sentc) == sentc: # 簡體標題中之繁體句子
                                                        # new_content += sentc+' '
                                                        self.cn_zh_count += 1
                                                    else: # 簡體標題中之簡體句子
                                                        self.cn_cn_count += 1
                                                new_content += sentc+' '
                                        if new_content:
                                            data += new_content+'\n'
                                    else:
                                        print('"{0}" got error !'.format(title))
            json.dump(self.dataDict, open('dataDict_zh.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=4)
            json.dump(self.dataDict_cn, open('dataDict_cn.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=4)
            print('dataDict_zh.json and dataDict_cn.json have been created.')
            print('繁體標題數:', self.zh_articles)
            print('簡體標題數:', self.cn_articles)
            print('繁體標題中，簡體繁體句子比例 --> 繁體句子: {0}, 簡體句子: {1}'.format(self.zh_zh_count, self.zh_cn_count))
            print('簡體標題中，簡體繁體句子比例 --> 繁體句子: {0}, 簡體句子: {1}'.format(self.cn_zh_count, self.cn_cn_count))
            print('繁體中文句子數:', self.zh_zh_count+self.cn_zh_count)
            print('簡體中文句子數:', self.zh_cn_count+self.cn_cn_count)
                    
    def getDataDict(self):
        # 檢查dataDict.json是否存在，已存在則讀取檔案，否則建立檔案
        if os.path.exists(os.path.join(os.getcwd(), 'dataDict.json')):
            print('Load dataDict.json ...')
            with open('dataDict.json', 'r', encoding='utf-8') as file:
                self.dataDict = json.load(file)
        else:
            print('dataDict.json is not found!')
            print('Create dataDict.json ...')
            for root, dirs, files in tqdm(os.walk('extracted'), ascii=True, desc='folders'): # extracted 為資料夾名稱
                for file in tqdm(files, ascii=True, desc='files'):
                    with bz2.BZ2File(os.path.join(root, file), 'r') as file: # , 'rb'
                        data = ''
                        title = ''
                        origin_title = ''
                        for line in file.readlines():
                            content = line.decode('utf-8').replace('\n', '')
                            if content:
                                if 'title="' in content and '">' in content:
                                    index = content.find('title="')
                                    origin_title = content[index+7:-2]
                                    title = self.opencc_s2t(content[index+7:-2])
                                    if title == origin_title:
                                        self.zh_articles += 1
                                    else:
                                        self.cn_articles += 1
                                elif self.opencc_s2t(content) == title:
                                    continue
                                else:
                                    if '</doc>' in content and data is not '':
                                        data = self.opencc_s2t(data)
                                        self.dataDict[title] = data
                                        data = ''
                                    elif '<doc' not in content:
                                        content_list = content.replace('，', '。').split('。')
                                        new_content = ''
                                        for sentc in content_list:
                                            sentc = sentc.replace('\n', '').strip()
                                            if sentc and '</doc>' not in sentc:
                                                if title == origin_title:
                                                    if self.opencc_s2t(sentc) == sentc: # 繁體標題中之繁體句子
                                                        new_content += sentc+' '
                                                        self.zh_zh_count += 1
                                                    else: # 繁體標題中之簡體句子
                                                        self.zh_cn_count += 1
                                                else:
                                                    if self.opencc_s2t(sentc) == sentc: # 簡體標題中之繁體句子
                                                        new_content += sentc+' '
                                                        self.cn_zh_count += 1
                                                    else: # 簡體標題中之簡體句子
                                                        self.cn_cn_count += 1
                                        if new_content:
                                            data += new_content+'\n'
                                    else:
                                        print('"{0}" got error !'.format(title))
            json.dump(self.dataDict, open('dataDict.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=4)
            print('dataDict.json has been created.')
            print('繁體標題數:', self.zh_articles)
            print('簡體標題數:', self.cn_articles)
            print('繁體標題中，簡體繁體句子比例 --> 繁體句子: {0}, 簡體句子: {1}'.format(self.zh_zh_count, self.zh_cn_count))
            print('簡體標題中，簡體繁體句子比例 --> 繁體句子: {0}, 簡體句子: {1}'.format(self.cn_zh_count, self.cn_cn_count))
            print('繁體中文句子數:', self.zh_zh_count+self.cn_zh_count)
            print('簡體中文句子數:', self.zh_cn_count+self.cn_cn_count)

    def getContentDict(self, topic):
        startTime = datetime.datetime.now() 
        self.topic = topic
        # title_list = []
        # 查看是否已建立"topic"_pair.json，若已建立則讀取檔案，否則爬取階層關係架構
        if not os.path.exists(os.path.join(os.getcwd(), '{0}/{1}_pair.json'.format(self.pairFolderName, self.topic))):
            self.start(self.topic)
        else:
            print('INFO: {0}_pair.json is existed, load pair data ...'.format(self.topic))

            with open('{0}/{1}_pair.json'.format(self.pairFolderName, self.topic), 'r', encoding='utf-8') as file:
                pair_list = json.load(file)

            # 將頁面名稱保存
            for item in tqdm(pair_list, ascii=True):
                if 'Category:' not in item[0] and item[0] not in self.all_title_list:
                    self.all_title_list.append(item[0])
                if 'Category:' not in item[1] and item[1] not in self.all_title_list:
                    self.all_title_list.append(item[1])

        # 讀取dataDict.json，裡面包含所有wiki頁面之內容，若已建立則讀取檔案，否則建立檔案(需花費較長時間)
        self.getDataDict()

        for title in tqdm(self.all_title_list, ascii=True):
            # 直接到dataDict.json中查詢
            if title in self.dataDict:
                self.contentDict[title] = self.dataDict[title]
            # else:
                # pass # *2018/07/16討論修訂為不爬
                # # 若dataDict.json中有缺漏此頁面則到網頁上爬取 
                # with HTMLSession() as sess:
                #     url = self.domain+'/wiki/{0}'.format(title)
                #     try:
                #         res = sess.get(url)
                #     except:
                #         print("ConnectionError, wait for 120s ...")
                #         print("url:", url)
                #         time.sleep(120)
                #         res = sess.get(url)

                #     content = ''
                #     for pageContent in res.html.find('p'):
                #         content += self.opencc.convert(pageContent.text)
                #     self.contentDict[title] = content
        endTime = datetime.datetime.now()

        print('Json Time:', str(endTime - startTime))
        pathlib.Path(self.jsonFolderName).mkdir(parents=True, exist_ok=True)
        json.dump(self.contentDict, open('{0}/{1}.json'.format(self.jsonFolderName, self.topic), 'w', encoding='utf-8'), ensure_ascii=False, indent=4)
        print('共儲存 {0} 篇文章於 {1}/{2}.json'.format(len(self.contentDict), self.jsonFolderName, self.topic))
        logging.info('{0}.json Time -------> {1}'.format(self.topic, str(endTime - startTime)))
        logging.info('{0}.json ------------> {1} articles.'.format(self.topic, len(self.contentDict)))


if __name__ == '__main__':
    topic = '南美洲'
    crawler = WikiTopicExtractor()
    crawler.getContentDict(topic)
