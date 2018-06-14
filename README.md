# FuntimeWebCrawler
旅遊比價網爬蟲

<br>python 3.6 version
<br>pip install -r requirement.txt

<br>mysql root 登入設定後，才可寫入mysql
<br> ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '1234';    
<br> FLUSH PRIVILEGES;  

<br>#How to use
<br>python hotelcrawler.py -i 2018-06-27 -o 2018-07-02
<br> -i --checkin : 輸入checkin日期 格式為 yyyy-mm-dd
<br> -o --checkout: 輸入checkout日期 格式為 yyyy-mm-dd
<br> checkin日期不能為今天
<br> checkin日期和checkout日期 要同時輸入
<br> 不輸入日期，預設爬明天


<br>#結果
<br>Input: AreaInTaiwan.csv
<br>Output: DateTimeFolder with area's csv and 輸入mysql

