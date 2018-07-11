# WikiTopicExtractor

### 資料下載
中文wiki資料下載： `wget https://dumps.wikimedia.org/zhwiki/latest/zhwiki-latest-pages-articles.xml.bz2`

下載完成後透過`WikiExtractor.py`將資料壓切成多份小檔案
* 原始下載處： https://github.com/attardi/wikiextractor
* 解壓縮至extracted `WikiExtractor.py -cb 250K -o extracted zhwiki-latest-pages-articles.xml.bz2` 



### 使用方法
輸入欲爬取之主題名稱TOPIC，`getContentDict(TOPIC)`將會產生該主題下每個路徑的pair及頁面內容。
