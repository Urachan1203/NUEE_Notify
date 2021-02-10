import csv
import os
import sys
import re
import io
import datetime
import pandas as pd
import twitter
from time import sleep
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
# from html.parser import HTMLParser
from html.parser import HTMLParser
from datetime import date,datetime
from enum import IntEnum

URL = 'https://auth.nagoya-u.ac.jp/cas/login?service=https%3A%2F%2Fwww.nuee.nagoya-u.ac.jp%2Finternal'
LAST_UPDATED_DATE_PATH = '/path/to/last_updated_log.txt'
LOG_PATH = '/path/to/log.txt'

#kkkk
#タグ除去
# class MyHtmlStripper(HTMLParser):
#     def __init__(self, s):
#         super().__init__()
#         self.sio = io.StringIO()
#         self.feed(s)

#     def handle_starttag(self, tag, attrs):
#         pass

#     def handle_endtag(self, tag):
#         pass

#     def handle_data(self, data):
#         self.sio.write(data)

#     @property
#     def value(self):
#         return self.sio.getvalue() 

class Info(IntEnum):
    URL = 0
    TARGET = 1
    CATEGORY = 2
    SUBJECT = 3
    UPDATED = 4


#cas認証突破
def login(url):
    #url = "https://auth.nagoya-u.ac.jp/cas/login?service=https%3A%2F%2Fwww.nuee.nagoya-u.ac.jp%2Finternal"
    login = "NU_ID" #名大ID
    password = "NU_PASSWORD" #パスワード

    options = Options()
    options.add_argument('--headless')

    driver = webdriver.Chrome(executable_path="/usr/lib/chromium-browser/chromedriver", chrome_options=options)

    driver.implicitly_wait(10)
    
    driver.get(url)

    driver.find_element_by_id("username").send_keys(login)
    driver.find_element_by_id("password").send_keys(password)
    driver.find_element_by_name("submit").send_keys(Keys.ENTER)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.close()
    driver.quit()
    return soup
    

def get_info(url_list):

    info_list=[]

    ctr=1

    for elem in url_list:
        print('loading...')
        url = URL + elem
        soup_contents = login(url)

        target = ""
        category = ""
        subject = ""
        last_updated = ""

        for tmp in soup_contents.find_all('td'):
            if(ctr == 1 or ctr == 2):
                ctr += 1
            elif(ctr == 3):
                target += tmp.text
                ctr += 1
            elif(ctr == 4):
                category += tmp.text
                ctr += 1
            elif(ctr == 5):
                subject += tmp.text
                ctr = 1
                break
        tmp_date=[]
        for tmp in soup_contents.find_all('td',class_='col-sm-9'):
            tmp_date.append(tmp.text.replace(" ",""))
        last_updated += tmp_date[1]

        tmp_list = [url,target,category,subject,last_updated]
        info_list.append(tmp_list)

    
    return info_list


def tweet_info(url,target,category,subject):
    
    #Twitter API key を入力
    auth=twitter.OAuth(consumer_key="CONSUMER_KEY",
    consumer_secret="CONSUMER_SECRET",
    token="TOKEN",
    token_secret="TOKEN_SECRET")

    t=twitter.Twitter(auth=auth)

    str="【電子掲示板が更新されました】"+'\n'+'\n'+target+'\n'+category+'\n'+subject+\
        '\n\n'+"詳細はこちらから↓"+'\n'+url

    try:
        t.statuses.update(status=str)
    except twitter.api.TwitterHTTPError:
        return str,False
    
    return str,True

def print_log_with_tweet(url,target,category,subject):
    with io.open(LOG_PATH,'a',encoding='utf-8') as f:
        f.write('【'+ get_date() + '】'+'\n')
        f.write('更新がありました\n')
        str=tweet_info(url,target,category,subject)
        f.write(str[0]+'\n')
        if str[1]:
            f.write('ツイートに成功しました\n')
        else:
            f.write('ツイートに失敗しました\n')
        f.write('-------\n')
        f.close()

            
def print_log():
    with io.open(LOG_PATH,'a',encoding='utf-8') as f:
        f.write('【'+ get_date() + '】' + '\n')
        f.write('更新はありません\n')
        f.write('-------\n')
        f.close()

def get_date():
    now=datetime.now()
    return now.strftime('%Y-%m-%d %H:%M:%S')

def has_logfile():
    if os.path.exists(LAST_UPDATED_DATE_PATH):
        return 1
    else:
        return 0

def write_last_updated_date(info):
    with io.open(LAST_UPDATED_DATE_PATH,'w',encoding='utf-8') as f:
        f.write(info)
        f.close()

def convert_str_to_datetime(str):
    # print(str)
    try:
        return datetime.strptime(str,'%Y年%m月%d日%H時%M分')
    except ValueError:
        print('Error：last_updated_log.txtの書式が不正です')
        exit(1)

def get_last_updated_date():
    last_updated_date = ""
    with io.open(LAST_UPDATED_DATE_PATH,'r',encoding='utf-8') as f:
        last_updated_date = f.readline()
        f.close()
    return convert_str_to_datetime(last_updated_date)
    



def main():
    soup=login(URL) #お知らせ一覧へアクセス

    url_list = [] #urlのリスト
    for elem in soup.find_all('a',class_ = 'btn btn-default'): #お知らせ詳細のurlを取得
        tmp=elem.get('href')
        url=tmp.split('/')
        if(url[3] == 'detail'):
            tmp2 = tmp.replace('/internal','')
            url_list.append(tmp2)

    info_list = get_info(url_list)
    

    if(has_logfile()): #logファイルがあったら処理開始
        last_updated_date = get_last_updated_date() #最終更新日時を取得
        fg=1 #一番上か？
        update_fg=0 #updateされたか
        str=""
        for elem in info_list:
            if(fg): #一番上なら
                str = elem[int(Info.UPDATED)] #一番上にあるお知らせの日時を保持する
                fg=0
            date = convert_str_to_datetime(elem[int(Info.UPDATED)]) 
            if(date > last_updated_date): #最終更新日時よりも新しいものを発見したら
                #print(elem[int(Info.URL)],elem[int(Info.TARGET)],elem[int(Info.CATEGORY)],elem[int(Info.SUBJECT)]) #debug
                print_log_with_tweet(elem[int(Info.URL)],elem[int(Info.TARGET)],elem[int(Info.CATEGORY)],elem[int(Info.SUBJECT)])
                update_fg=1
            else:
                if(update_fg):
                    write_last_updated_date(str)
                else:
                    print_log()
                break
    else:
        write_last_updated_date(info_list[0])

    

if __name__ == '__main__':
    main()
