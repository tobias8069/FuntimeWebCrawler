#!/usr/bin/python
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import pandas as pd
import datetime
import os
import time
import re 
import threading
import queue
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import WebDriverException

def hotel_lists(area,checkin,checkout):
    
    #搜尋條件網址，area == 地區， checkin == 入住時間， checkout == 離開時間
    
    HOST = 'https://www.funtime.com.tw/'
    query = 'ovehotel/search-hotel/{0}?resultID=0&checkin={1}&checkout={2}' \
            '&Rooms=1&adults_1=1&label=HTLsearch_2_api&lowRate=0&sort=Popularity-desc&pageIndex=0'\
            .format(area, checkin, checkout)
    queryurl = HOST + query
    
    #use selenium to search 比價網 
    
    browser = webdriver.Chrome('chromedriver')
    browser.get(queryurl)
    wait = WebDriverWait(browser,10)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.hotel-rates > a')))  #等搜尋結果出來
    wait.until(EC.invisibility_of_element_located((By.CLASS_NAME, 'loading')))            #等loading頁面消失
    browser.find_element_by_css_selector('#bottom_ad_delete_btn').click()                 #把廣告按掉
    
    
    #搜尋結果資訊: 總共有幾家旅館，共幾頁
    
    searchresult = browser.find_elements_by_css_selector('#SearchResultsHolder')
    totalpages = int(searchresult[0].get_attribute('data-totalpages'))
    totalhotel = searchresult[0].get_attribute('data-propertiesavailabletranslation')
    print('Total hotels : ' + totalhotel)
    print('總共'+str(totalpages)+'頁')
    

    
    #搜尋旅館 url，放進 hotellists 中，返回 list
    hotelquery = re.compile('/(ovehotel/search-hotel/\S+)%3Fmobile')
    base = '?checkin={0}&checkout={1}&Rooms=1&adults_1=2&label=HTLsearch_1_api'.format(checkin,checkout)
    hotellists = []
    
    while True:
        try:
            linklist = browser.find_elements_by_css_selector('div.hotel-rates > a')
            
            hotellists.extend([HOST + re.findall(hotelquery,g.get_attribute('href'))[0] +base  for g in linklist])
            
            browser.execute_script('window.scrollBy(30, document.body.scrollHeight)')    #瀏覽器網最下面按
            browser.find_element_by_link_text("下一頁 →").click()                         #按下一頁
            WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.hotel-rates > a')))
            WebDriverWait(browser, 10).until(EC.invisibility_of_element_located((By.CLASS_NAME, 'loading')))
            
 
                 
        except NoSuchElementException :
            break
        
    
    
    browser.quit()
    
    return hotellists

def get_hotel_content(queue,list):
    
    
    #從 queue 中拿 url
    while not queue.empty():
        url = queue.get()
    

        resp = requests.get(url)
        soup = BeautifulSoup(resp.text, 'lxml')
        listcontent = soup.select('tr[data-index]')  # 所有商家內容

        for i in range(0, len(listcontent)):
            content = {}
            if soup.select_one('span.hotel-name').text.strip() == '':
                content['旅館名稱'] = soup.select_one('span.hotel-transliteratedName').text.strip()
                content['旅館中文名稱'] = ''
            else:
                content['旅館名稱'] = soup.select_one('span.hotel-name').text.strip()
                content['旅館中文名稱'] = soup.select_one('span.hotel-transliteratedName').text.strip()
            content['旅館地址'] = soup.select_one('#wrapper > div.hotel-data-wrapper > p').text.strip()
            content['商家'] = listcontent[i]['data-provider-name']  # 代訂商家名稱
            content['內容'] = listcontent[i].select_one('.roomName').text.strip()  # 房間描述
            content['價錢'] = int(
                listcontent[i].select_one('.roomRate').text.replace('NT$', '').replace(',', '').strip())  # 房間價錢
            list.append(content)
            


            
def to_csv(list,path,area):
    
    if not os.path.exists(path):
        os.makedirs(path)    
    
    df = pd.DataFrame(list)
    df = df.reindex(columns=['旅館名稱', '旅館中文名稱', '商家', '內容', '價錢', '旅館地址'])
    df.to_csv(path+'/{}.csv'.format(area), index=False, encoding='utf-8-sig')
   


    
    
    
def main() :
   
    datedir = datetime.date.today().strftime("%Y-%m-%d")
    if not os.path.exists(datedir):
        os.makedirs(datedir)

    
    checkin = (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    checkout = (datetime.date.today() + datetime.timedelta(days=2)).strftime("%Y-%m-%d")
   
    

    with open('AreaInAsia.csv','r') as f:
         for n in f.readlines()[1:]:

            country, area, query = n.split(',')
            
            start = time.time()

            print('搜尋條件 \n\t地點: ' + area, '\n\t入住時間: '+checkin,'\n\t離開時間: '+checkout)
            print('\n現在時間 ' + time.strftime('%H:%M:%S',time.localtime(start)))
            print('\n........搜尋中 .......')
            
                         
            
            
            hotelurls = queue.Queue() #建立queue物件
            hotellists = hotel_lists(query,checkin,checkout)
            for url in hotellists:
                page.put(url)

            csvlist = []
            threads = []
            
            for i in range(10):  #開thread
                t = threading.Thread(target=get_hotel_content, args=(hotelurls,csvlist))
                t.start()
                threads.append(t)
       
            for thread in threads:
                thread.join()
            
            
            csvpath = datedir +'/'+ country
            to_csv(csvlist, csvpath, area)
            
            end = time.time()
            print('Querytime : ' + str(round((end - start)/60,2)) + ' minutes\n')
            print('\n搜尋完成時間 ' + time.strftime('%H:%M:%S',time.localtime(start)))
        
            
            
if __name__ == '__main__':
    main()
