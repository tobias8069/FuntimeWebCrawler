import argparse
import requests
from bs4 import BeautifulSoup
import pandas as pd
import datetime
import os
import time
import queue
import threading
import pymysql



def create_mysql(checkin,checkout):
    conn = pymysql.connect(host='localhost', port=3306, user='root', password='1234', use_unicode=True,
                           charset='utf8mb4')
    cur = conn.cursor()
    cur.execute('CREATE DATABASE IF NOT EXISTS hotelprice ;')
    cur.execute('USE hotelprice; ')

    cur.execute("""CREATE TABLE IF NOT EXISTS {0} (
    旅館名稱 VARCHAR(100),
    商家 VARCHAR(10),
    房型 VARCHAR(5),
    內容 VARCHAR(200),
    價錢 int,
    旅館地址 VARCHAR(1000),
    旅館ID VARCHAR(1000),
    地區 VARCHAR(500),
    URL VARCHAR(500)
    PRIMARY KEY (旅館名稱, 商家, 房型 ,內容)
    );""".format("price_" + checkin +"_" + checkout))

    conn.commit()


def to_mysql(row):

    conn = pymysql.connect(host='localhost', port=3306, user='root', password='1234',
                           use_unicode=True, charset='utf8mb4')
    cur = conn.cursor()
    cur.execute('USE hotelprice; ')
    cur.execute("""INSERT INTO price VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (row['旅館名稱'],
                 row['商家'],
                 row['房型'],
                 row['內容'],
                 row['每晚價錢'],
                 row['旅館地址'],
                 row['旅館ID'],
                 row['地區']
                 row['url']
                 )
                )
    conn.commit()
    cur.close()

def url_request(url):
    resp = requests.get(url, headers={'Connection': 'close'})
    soup = BeautifulSoup(resp.text, 'lxml')

    return soup


def querycontent(area, checkin, checkout):
    HOST = 'https://www.funtime.com.tw/domhotel/'
    query = 'result.php?city={0}&district=&viewspot=&h_name=&checkin={1}&checkout={2}' \
            '&sk=&per_page=60&sort=hot_h&search=m&page='.format(area, checkin, checkout)
    queryurl = HOST + query
    soup = url_request(queryurl)
    try:
        totalpages = int(soup.select('span.pagingAct > a')[-2].text.strip())
    except IndexError:
        totalpages = 1
    print('搜尋頁數' + str(totalpages) + '頁')

    return queryurl, totalpages


def get_hotel_pages(url):
    HOST = 'https://www.funtime.com.tw/domhotel/'
    soup = url_request(url)
    hotellist = [HOST + g['data-to_detail'] for g in
                 soup.select('#result_table > div.result_row > div.result_center > div.hotel_name > a')]
    return hotellist


def get_hotel_content(queue, list, area):
    while not queue.empty():
        url = queue.get()

        detail_url = url.replace('dom_detail', 'ajax_detail_content')

        soup = url_request(url)
        detail_soup = url_request(detail_url)
        listcontent = detail_soup.select('div.result_hover > div.result_source  > a  ')  # 所有商家內容

        for i in range(0, len(listcontent)):
            content = {}

            content['旅館名稱'] = soup.select_one('div.hotel_name').text.strip()

            content['旅館地址'] = soup.select_one('div.hotel_address').text.strip().split('\t')[0].replace('地址：', '')
            content['商家'] = listcontent[i]['data-source']  # 代訂商家名稱
            content['內容'] = listcontent[i]['data-title']  # 房間描述
            content['每晚價錢'] = int(listcontent[i]['data-total_price'])  # 房間價錢
            content['房型'] = listcontent[i]['data-type_id']  # 房間型號
            content['旅館ID'] = listcontent[i]['data-h_id']  # 旅館ID
            content['地區'] = area
            content['url'] = url
            to_mysql(content)

            list.append(content)


def savetocsv(list, path, area):
    if not os.path.exists(path):
        os.makedirs(path)

    df = pd.DataFrame(list)
    df.reindex(columns=['旅館名稱', '商家', '內容', '房型', '價錢', '旅館地址'])
    df.to_csv(path + '/{}.csv'.format(area), index=False, encoding='utf-8-sig')


def main():
    parser = argparse.ArgumentParser(description='Funtime Crawler')
    parser.add_argument('-i', '--checkin', type=str,
                        default=(datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
                        help='CheckIn Date')
    parser.add_argument('-o', '--checkout', type=str,
                        default=(datetime.date.today() + datetime.timedelta(days=2)).strftime("%Y-%m-%d"),
                        help='CheckOut Date')

    args = parser.parse_args()

    datedir = datetime.date.today().strftime("%Y-%m-%d")
    if not os.path.exists(datedir):
        os.makedirs(datedir)


    checkin = args.checkin
    checkout = args.checkout

    create_mysql(checkin,checkout)
    
    initial = time.time()
    with open('AreaInTaiwan.csv', 'r') as f:
        for n in f.readlines()[1:]:

            area, query = n.replace('\n', '').split(',')
            hotellists = []
            csvlist = []
            page = queue.Queue()  # 建立queue物件

            start = time.time()

            print('\n搜尋條件 \n\t地點: ' + area, '\n\t入住時間: ' + checkin, '\n\t離開時間: ' + checkout)
            print('\n現在時間 ' + time.strftime('%H:%M:%S', time.localtime(start)))
            print('\n........ 搜尋中 .......')

            queryurl, totalpages = querycontent(query, checkin, checkout)
            for p in range(1, totalpages + 1):
                hotellists.extend(get_hotel_pages(queryurl + str(p)))

            for url in hotellists:
                page.put(url)

            threads = []
            for i in range(10):  # 開thread
                t = threading.Thread(target=get_hotel_content, args=(page, csvlist,area))
                t.start()
                threads.append(t)
            for thread in threads:
                thread.join()

            csvpath = datedir + '/台灣比價'

            savetocsv(csvlist, csvpath, area)
            end = time.time()
            print('Querytime : ' + str(round((end - start) / 60, 2)) + ' minutes\n')
            print('\n搜尋完成時間 ' + time.strftime('%H:%M:%S', time.localtime(time.time())))
    finaltime = time.time()

    print('總搜尋時間: ' + str(round((finaltime - initial) / 60, 2)) + ' minutes\n')

if __name__ == '__main__':
    main()

