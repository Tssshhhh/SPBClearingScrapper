import os.path

import selenium.webdriver.remote.webelement
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException

import logging
import pandas as pd
from datetime import datetime


def set_logger(name, log_file, level=logging.INFO):
    handler = logging.FileHandler(log_file)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    return logger


selen_logs = set_logger('selenium_logger', 'logs/selen_logs.log')
table_logs = set_logger('pandas_logger', 'logs/table_logs.log')
warning_logs = set_logger('warnging_logger', 'logs/warnings.log', level=logging.WARNING)


def start_wd() -> webdriver.Firefox:
    s = Service(r'geckodriver.exe')
    options = Options()
    options.set_preference("browser.download.folderList", 2)
    options.set_preference("browser.helperApps.alwaysAsk.force", False)
    options.add_argument("--enable-javascript")

    browser = webdriver.Firefox(service=s, options=options)
    browser.maximize_window()
    browser.implicitly_wait(10)
    browser.set_page_load_timeout(10)
    return browser


def prepare_site(browser: webdriver.Firefox, url):
    browser.get(url)
    a = input('Continue? y/n\n')
    if a != 'y':
        browser.clost()
        browser.quit()
        quit()


def get_hrefs_from_span(span_elem: selenium.webdriver.remote.webelement.WebElement):
    outer_html = span_elem.get_attribute("outerHTML")
    href_raw = outer_html.split("javascript")
    href_end = []
    for href in href_raw:
        if 'doPostBack' in href:
            link = 'javascript' + href.split('"')[0]
            href_end.append(link)
    return href_end


def get_table_from_site(start_time, browser: webdriver.Firefox):
    ctl_list = ["$ctl01'", "$ctl02'", "$ctl03'", "$ctl04'", "$ctl05'", "$ctl05'", "$ctl06'"]
    table_list = []
    browser.implicitly_wait(5)
    wait = WebDriverWait(browser, 20)
    counter = 0
    for pages_list in range(50):
        while True:
            span_elem = browser.find_element("xpath", '//*[@id="ctl00_BXContent_val1_dp"]')
            href_list = get_hrefs_from_span(span_elem)
            try:
                for href in href_list:
                    if any(ctl in href for ctl in ctl_list):
                        link = href.split("Back('")[1].split("'")[0]
                        table = wait.until(
                            EC.visibility_of_element_located((By.XPATH, "/html/body/form/div[3]/div/div/div/div[3]/table"))).\
                            get_attribute("outerHTML")
                        next_page = browser.find_element("xpath", f"//a[contains(@href,'{link}')]")
                        if next_page.text.isdigit() or next_page.text == "...":
                            pass
                        else:
                            warning_logs.warning(f'bug? {next_page.text}')
                            break
                        selen_logs.info(f'PAGE {next_page.text}')
                        table_list.append(table)
                        table_logs.info(table)
                        next_page.click()
                        counter += 1
            except (NoSuchElementException, StaleElementReferenceException):
                warning_logs.warning(f"WARN: DIDN'T GOT {counter+1} PAGE.")
                continue
            break
    with open(f'table_list{start_time.strftime("%m-%d-%M")}', 'w+', errors='ignore') as f:
        f.write('\n'.join(table_list))
    browser.close()
    browser.quit()


def df_to_excel(start_time):
    if os.path.exists('table_list.txt'):
        with open('table_list.txt', 'r') as l:
            tables = l.read()
    else:
        with open('logs/table_logs.log', 'r') as l:
            tables = l.read()
    df_list = pd.read_html(tables, decimal=',', thousands='.')
    df_export = pd.DataFrame(columns=['Код ценной бумаги', 'Наименование', 'ISIN', 'Минимальное базовое ГО, %',
                                      'Минимальное базовое ГО в дни ожидаемой повышенной волатильности, %',
                                      'MR_stress, %', 'ch_fine_short, %', 'ch_fine_long, %', 'fine_short, %',
                                      'fine_long, %', 'ch_fine_borrow money, %', 'ch_fine_borrow sercurity, %',
                                      'Group_name'])
    for df in df_list:
        df_export = pd.concat([df_export, df])
    df_export = df_export.drop_duplicates()
    df_export.to_excel(f'SPB_Risk_Params{start_time.strftime("%m-%d-%M")}.xlsx', index=None)


if __name__ == "__main__":
    start_time = datetime.now()
    # URL = 'https://spbclearing.ru/ru/risk_managemen/riskpar/rcenbum/values1/'
    # browser = start_wd()
    # prepare_site(browser, url=URL)
    # get_table_from_site(start_time, browser=browser)
    # selen_logs.info(f'SCRIPT WORKED FOR {str(start_time - datetime.now())}')
    df_to_excel(start_time)
