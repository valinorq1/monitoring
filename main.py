# -*- coding: utf-8 -*-
import time
import configparser
import re
import json
import yaml

from requests_futures.sessions import FuturesSession
import requests
from bs4 import BeautifulSoup
import schedule
from pathlib import Path

config = configparser.ConfigParser()
config.read("config.ini")
category_url = config['PARSER']['url']
default_delay = int(config['PARSER']['delay'])
token = str(config['PARSER']['token'])
chat = str(config['PARSER']['chat'])

ALL_ITEMS = []


def parse_item_data(html, url):
    total_item = 0
    soup = BeautifulSoup(html, 'lxml')
    current_page_items = soup.find_all('div', {'class': 'bxr-detail-col-tabs'})
    data = {}
    for i in current_page_items:
        item_name = i.find('td', {'class': 'bxr-offer-name-td'}).find('span').text  # название
        data['product_name'] = item_name.replace('\n', '').replace(' ', '')
        quantity_green = i.find_all('div', {'class': 'bxr-instock-wrap'})
        for t in quantity_green:
            t = str(t)
            soup = BeautifulSoup(t, 'lxml')
            current_tab_all_price = soup.find_all('div', {'class': 'bxr-instock-wrap'})
            for p in current_tab_all_price:
                total_item += int(re.sub(r'\D', '', p.text))

        quantity_blue = i.find_all('div', {'class': 'bxr-outstock-wrap'})
        for a in quantity_blue:
            total_item += int(re.sub(r'\D', '', a.text))

    data['url'] = url
    data['total'] = total_item
    ALL_ITEMS.append(data)


def fetch_product_data(urls):
    with FuturesSession() as session:
        futures = [session.get(url) for url in urls]
        for future in futures:
            parse_item_data(future.result().text, future.result().url)


def parse_all_product_link():
    all_items_links = []
    for i in range(1, 280):
        r = requests.get(f"{category_url}/?PAGEN_2={i}")
        if 'last-current-page' in r.text:
            break
        soup = BeautifulSoup(r.text, 'lxml')
        current_page_items = soup.find_all('td', {'class': 'bxr-element-btn-col'})
        for item in current_page_items:
            all_items_links.append('https://alexstore24.ru' + item.find('a').attrs['href'])
        if 'pagination' not in r.text:
            break
    return all_items_links


def write_pd(data):
    with open('last.txt', 'a', encoding='utf-8') as f:
        for i in data:
            f.write(str(f"{i}\n"))


def compare_data(last_data):
    print()
    updated = []
    last_data_from_file = []
    with open('last.txt', 'r') as data:
        for q in data:
            #json_acceptable_string = q.replace("'", "\"")
            last_data_from_file.append(yaml.load(q,Loader=yaml.FullLoader))

    for i, w in zip(last_data_from_file, last_data):
        if i != w:
            for (k, v), (z, x) in zip(w.items(), i.items()):
                if k == 'total' and z == 'total':
                    if v > x:  # есть завоз товар
                        updated.append(w)

    if updated:
        url_list = []
        for i in updated:
            for k, v in i.items():
                if k == 'url':
                    url_list.append(f"{v}")
        msg = """
        """
        for m in url_list:
            msg += f'\nСсылка на страницу товара:{m}'
        requests.get(f'https://api.telegram.org/bot{token}/sendMessage?chat_id={chat}&parse_mode=html&text={msg}')

    # чистим лист с ссылками, что бы не было проблем
    fl = open("last.txt", "w")
    fl.close()
    write_pd(last_data)
    # чистим ссылки
    ALL_ITEMS.clear()


def main():
    all_products_link = parse_all_product_link()
    fetch_product_data(all_products_link)
    time.sleep(1)
    compare_data(ALL_ITEMS)


def first_parsing():
    all_products_link = parse_all_product_link()
    fetch_product_data(all_products_link)
    write_pd(ALL_ITEMS)
    compare_data(ALL_ITEMS)


if __name__ == '__main__':
    """
        Стартовый запуск и первый парсинг
    """
    my_file = Path("last.txt")  # Если есть файл - то бот настроен.
    if my_file.is_file():
        print('Configured.')
        main()
    else:
        print('Config are running...')
        first_parsing()
        print('Config done.')

    schedule.every(default_delay).minutes.do(main)
    #schedule.every(15).seconds.do(main)
    while True:
        schedule.run_pending()
        time.sleep(1)
