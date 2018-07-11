# WikiTopicExtractor


### 資料下載 (英文則將zhwiki改為enwiki)
中文wiki資料下載： `wget https://dumps.wikimedia.org/zhwiki/latest/zhwiki-latest-pages-articles.xml.bz2`

下載完成後透過`WikiExtractor.py`將資料壓切成多份小檔案
* 原始下載處： https://github.com/attardi/wikiextractor
* 解壓縮至extracted： `WikiExtractor.py -cb 250K -o extracted zhwiki-latest-pages-articles.xml.bz2`

簡繁轉換套件openncc下載處： https://github.com/yichen0831/opencc-python


### 使用方法
輸入欲爬取之主題名稱TOPIC，`getContentDict(TOPIC)`將會產生：
* 該主題下每個路徑的pair至`pairfile/TOPIC_pair.json`
* 該主題下所有頁面內容至`jsonfile/TOPIC.json`
