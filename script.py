from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.by import By
from pandas import DataFrame, read_csv
from pandas.core.common import flatten
from urllib.parse import urlparse
from googletrans import Translator
from datetime import datetime, timedelta
import time
import requests
from joblib import Parallel, delayed
from itertools import chain
import sys, os
import json
from time import sleep

capabilities = DesiredCapabilities.CHROME
options = webdriver.ChromeOptions()
user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.50 Safari/537.36'
options.add_argument(f'user-agent={user_agent}')
options.add_argument("headless")
capabilities["goog:loggingPrefs"] = {"performance": "ALL"}


cookie_identifiers = {
    '_sp_ses.',
    '_sp_',
    '_gat_eborganizer',
    '_gat_gatracker',
    '_gat_gtag_UA',
    '_gat_UA-',
    '_gat_',
    '_ga_',
    '__utmt_',
    '__utma',
    '_dc_gtm_UA-',
    'dpm_segs_',
    'dids',
    '_et_panels',
    '_et_ses',
    '_et_id',
    '_cs_.',
    'AMCV_',
    'AMCVS_',
    'visitor_id',
    'BEX-bv-',
    'ads__rtgt_Criteo',
    'hsk_',
    'orionSession',
    'h_tagging_',
    'hbc_',
    '__im__',
    'fbm_',
    'Prtim',
    'ssdspallvtc-',
    'ssdspck-',
    'PUB',
    'cmp',
    '__bm2_',
    '__bmp_',
    '_custrack1_identified.',
    '_custrack1_ses.',
    'gs_p_GSN-',
    'etcnt_',
    'igodigitalst',
    'IXAI',
    'crn',
    's_vi_',
    '_sfkcs2_',
    'adm_',
    '_hp2_id.',
    'apiDomain_2_',
    'apiDomain_3_'
}

def calcula_exp(t):

    now = datetime.utcnow()
    later = datetime.utcfromtimestamp(t)

    diff = later - now

    monday1 = (now - timedelta(days=now.weekday()))
    monday2 = (later - timedelta(days=later.weekday()))

    duration_in_s = diff.total_seconds()

    year = int(divmod(duration_in_s, 31536000)[0])
    month = (later.year - now.year) * 12 + later.month - now.month
    weeks = int((monday2 - monday1).days / 7)
    day  = diff.days
    hours = divmod(duration_in_s, 3600)[0]
    minutes = divmod(duration_in_s, 60)[0]
    seconds = duration_in_s

    if day < 28:
        month = 0
    else:
        month = int(month%12) if (month > 12) else int(month)


    date_v = ""

    if year > 0:
        if month > 0 and month < 12:
            date_v = f'{year} year(s) and {month} month(s)' 
            day = 0
            weeks = 0
            minutes = 0
            hours = 0
            year = 0
        else:
            date_v = f'{year} year(s)'
            year = 0
            month = 0
            day = 0
            weeks = 0
            minutes = 0
            hours = 0
            
    elif (month > 0 ):
        date_v = f'{month} month(s)'
        year = 0
        month = 0
        day = 0
        weeks = 0
        minutes = 0
        hours = 0
        
    elif (weeks > 0):
        date_v = f'{weeks} week(s)'
        year = 0
        month = 0
        day = 0
        weeks = 0
        minutes = 0
        hours = 0
        date_v
    elif (day > 0):
        date_v = f'{day} day(s)'
        year = 0
        month = 0
        day = 0
        weeks = 0
        minutes = 0
        hours = 0
        
    elif hours > 0:
        date_v = f'{hours} hour(s)'
        year = 0
        month = 0
        day = 0
        weeks = 0
        minutes = 0
        hours = 0
        
    elif minutes > 0:
        date_v = f'{minutes} minute(s)'
        year = 0
        month = 0
        day = 0
        weeks = 0
        minutes = 0
        hours = 0
    elif (minutes == 0) and (seconds == 0):
        date_v = '1 minute'
    return date_v


def capture_cookies(link):

    nav = webdriver.Chrome(options=options, desired_capabilities=capabilities)
    # try:
    nav.get(link)
    sleep(10)
    cookies = []
    logs = nav.get_log("performance")
    cookies_names = set()
    for log in logs:
        message = json.loads(log["message"])
        if message["message"]["method"] == "Network.requestWillBeSentExtraInfo":
            for associatedCookie in message["message"]["params"]["associatedCookies"]:
                if associatedCookie["cookie"]["name"] not in cookies_names:
                    cookies_names.add(associatedCookie["cookie"]["name"])
                    cookies.append(associatedCookie["cookie"])
    for cookie in nav.get_cookies():
       if cookie["name"] not in cookies_names:
            if "expires" in cookie:
                cookie['Retention'] = calcula_exp(cookie['expires'])
            elif "expiry" in cookie:
                cookie['Retention'] = calcula_exp(cookie['expiry'])
            else:
                cookie['expires'] = None
                cookie['Retention'] = None
            cookies.append(cookie)
            cookies_names.add(cookie["name"])

    print(f"found {len(cookies)} cookies on {link}")
    nav.close()

    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(cookies, f, ensure_ascii=False, indent=4)

    return cookies

    # except:
    #     with open('temp_links.txt', 'a') as temFile:
    #         temFile.write(f"\n{link}")
    

def scan_cookies(site, page_limit):
    domain = urlparse(site).netloc
    scheme = urlparse(site).scheme

    driver = webdriver.Chrome(options=options, desired_capabilities=capabilities)
    driver.get(site)

    cookies = []
    page_data = []
    error_data = []
    home_cookies = []

    try:
        home_cookies = capture_cookies(site)
    except:
        error_data.append("Link capture cookies error - " + site)

    cookies.extend(home_cookies)
    page_data.append([site, len(home_cookies)])

    links = []

    if len(links) < page_limit - 1:
        try:
            for i in driver.find_elements(By.TAG_NAME, 'a'):
                this_url = i.get_attribute('href')
                this_url = this_url.split("#", 1)[0]
                this_url = this_url.rstrip("/")

                if (this_url != None) and (this_url != '') and (scheme in this_url) and (
                        this_url.endswith('pdf') == False) and (this_url.endswith('jpg') == False) and (
                        this_url.endswith('odt') == False) and (this_url.endswith('png') == False) and (
                        this_url.endswith('xlsx') == False) and (this_url.endswith('docx') == False) and (
                        this_url.endswith('pptx') == False) and (this_url.endswith('txt') == False) and (
                        'editais' not in this_url) and this_url not in links and urlparse(this_url).netloc == domain:
                    links.append(this_url)

                if len(links) >= page_limit - 1:
                    break

        except:
            error_data.append("Link scrape issue - " + site)

    links = list(flatten(links))
    links = list(set(links))

    for i in links:
        try:
            page_cookies = capture_cookies(i)
            page_data.append([i, len(page_cookies)])
            cookies.extend(page_cookies)
        except:
            error_data.append("Link capture cookies error - " + site)
    # try:
    for cookie in cookies:
        cname = cookie['name']
        cookie['iden'] = cname
        for iden in cookie_identifiers:
            if(cookie['name'].startswith(iden)):
                cookie['iden'] = iden
                break


    df = DataFrame(cookies).drop_duplicates(['domain','iden']).reset_index(drop=True)\
        .merge(read_csv('updated_cookies.csv', encoding="ISO-8859-1",
    usecols=['Platform','Category', 'Domain', 'Description','Cookie / Data Key name']),
    how='left', left_on='iden', right_on='Cookie / Data Key name')

    cookie_type = []
    try:
        for d in df.domain:
            if (domain in d) or (d in domain):
                cookie_type.append('First-party')
            else:
                cookie_type.append('Third-party')
    except:
        error_data.append("Cookie type error - " + site)

    df['Cookie type'] = cookie_type
    expiration = []
    for d in df.expires:
        try:
            expiration.append(time.strftime(r'%d/%m/%Y %H:%M:%S', time.localtime(d)))
        except:
            expiration.append('Session')

    df['Expiration'] = expiration
    df['Retention'] = df['Expiration'].fillna('Session')
    df = df[['name', 'iden', 'domain', 'httpOnly', 'path', 'Domain', 'Platform', 'Cookie type','Retention','Expiration','Category','Description']]
    df = df.fillna('').replace('Nan', '').replace('Nan.', '')
    # cookies_op = json.loads(df.to_json(orient='records'))
    cookies_op = df.to_dict(orient='records')
    # except:
    #     cookies_op = json.dumps([])
    #     error_data.append("DF issue - " + site)

    # with open('cookies.json', 'w', encoding='utf-8') as f:
    #     json.dump([cookies_op, page_data], f, ensure_ascii=False, indent=4)

    # with open('cookies.json', 'w', encoding='utf-8') as f:
    #     json.dump(df, f, ensure_ascii=False, indent=4)

    op = {
        "cookies": cookies_op,
        "page_data": page_data,
        "error_data": error_data
    }

    return op

# op = scan_cookies("https://best4software.de/",10)
# send_data = {
#     "scan_id": "scan_id",
#     "scan_data": op
# }

# print(json.dumps(send_data))

import urllib
website = "best4software.de"
p = urllib.parse.urlparse(website, 'https')
netloc = p.netloc or p.path
path = p.path if p.netloc else ''
p = urllib.parse.ParseResult('https', netloc, path, *p[3:])
url = p.geturl()

print(url);
# import csv
# data = {}
# file = open("cookie_data.csv", "r")
# reader = csv.reader(file, delimiter=',')
# for row in reader:
#     data[row[0]] = row


# with open('cookie_data.json', 'w', encoding='utf-8') as f:
#     json.dump(data, f, ensure_ascii=False, indent=4)
