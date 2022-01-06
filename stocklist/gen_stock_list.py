import os
import json
import codecs
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import logging
import logging.handlers

LOG_DIR      = './'
LOG_FILENAME = 'gen_stock_list.log'
LOG_FORMAT   = '%(asctime)s [%(process)d] %(levelname)s %(name)s: %(message)s'

HEADER_ROW_CNT = 2

logger = logging.getLogger(__name__)

TWC_ATTRIBUTES = (
    '有價證券代號及名稱',
    '國際證券辨識號碼(ISIN Code)',
    '上市日',
    '市場別',
    '產業別',
    'CFICode',
    '備註'
)

class TWC_ROW:
    def __init__(self, tr_nodes):
        self.tr_nodes = tr_nodes
        self.col_stock_symbol    = col_to_idx('有價證券代號及名稱')
        self.col_isin_code       = col_to_idx('國際證券辨識號碼(ISIN Code)')
        self.col_date_of_listing = col_to_idx('上市日')
        self.col_category        = col_to_idx('市場別')
        self.col_industry        = col_to_idx('產業別')
        self.col_cfi_code        = col_to_idx('CFICode')
        self.col_note            = col_to_idx('備註')

    @property
    def stock_symbol(self):
        text  = self.tr_nodes.select('td')[self.col_stock_symbol].text.strip()
        return text
    
    @property
    def isin_code(self):
        text  = self.tr_nodes.select('td')[self.col_isin_code].text.strip()
        return text
    
    @property
    def date_of_listing(self):
        text  = self.tr_nodes.select('td')[self.col_date_of_listing].text.strip()
        return text
    
    @property
    def category(self):
        text  = self.tr_nodes.select('td')[self.col_category].text.strip()
        return text

    @property
    def industry(self):
        text  = self.tr_nodes.select('td')[self.col_industry].text.strip()
        return text

    @property
    def cfi_code(self):
        text  = self.tr_nodes.select('td')[self.col_cfi_code].text.strip()
        return text

class TWC_URL_PARSER:
    UA = UserAgent()
    user_agent = UA.random
    headers = {'user-agent': user_agent}

    def __init__(self, url):
        self.url = url    
        self.req = requests.get(url, headers=self.headers)
        self.data = self._gen_data()
 
    
    @property
    def content(self):
        return self.req.content.decode(self.req.encoding)

    @property
    def status_code(self):
        return self.req.status_code
    
    @property
    def parse(self):
        return BeautifulSoup(self.content, "lxml")

    def _gen_data(self):
        self.row = self.parse.select('tr')[HEADER_ROW_CNT:]
        self.row_count = len(self.row)
        if self.row_count != 0:
            return { i+1: TWC_ROW(self.row[i]) for i in range(self.row_count)}


def col_to_idx(col):
    return TWC_ATTRIBUTES.index(col)

def idx_to_col(idx):
    return TWC_ATTRIBUTES[idx]


def main():
    #=====================================================================
    # Logging setup
    #=====================================================================
    # Set the logging level of the root logger
    # logging.getLogger().setLevel(logging.DEBUG)
    logging.getLogger().setLevel(logging.INFO)

    # This sets timestamp for logging to UTC, otherwise it is local
    # logging.Formatter.converter = time.gmtime

    # Set up the console logger
    stream_handler = logging.StreamHandler()
    stream_formatter = logging.Formatter(LOG_FORMAT)
    stream_handler.setFormatter(stream_formatter)
    logging.getLogger().addHandler(stream_handler)

    # Set up the file logger
    log_filename   = os.path.abspath(os.path.join(LOG_DIR, LOG_FILENAME))
    max_bytes      = 10 * 1024 * 1024  # 1 MB
    file_handler   = logging.handlers.RotatingFileHandler(log_filename, maxBytes=max_bytes, backupCount=1)
    file_formatter = logging.Formatter(LOG_FORMAT)
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)
    logging.getLogger().addHandler(file_handler)


    url_twse = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
    url_otc  = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=4"
    
    logger.info("Start Parsing TWSE")
    DATA_TWSE = TWC_URL_PARSER(url_twse)
    logger.info("Finish Parsing TWSE")
    logger.info("Start Parsing OTC")
    DATA_OTC = TWC_URL_PARSER(url_otc)
    logger.info("Finish Parsing OTC")

    TWStock = dict()
    TWStock["TWSE"] = dict()
    TWStock["OTC"] = dict()
    
    fp = open('TWStockList.json', 'w',encoding='utf-8')

    logger.info("Start Generating TWSE List")
    for d in DATA_TWSE.data:
        try:
            stock_symbol = DATA_TWSE.data[d].stock_symbol
            industry     = DATA_TWSE.data[d].industry
            if industry:
                if industry not in TWStock["TWSE"].keys():
                    TWStock["TWSE"][industry] = list()
                stock_symbol = stock_symbol.split('\u3000')
                TWStock["TWSE"][industry].append({stock_symbol[0] : stock_symbol[1]})
        except:
            pass
            # print("上市認購(售)權證")
    logger.info("Finish Generating TWSE List")

    logger.info("Start Generating OTC List")
    for d in DATA_OTC.data:
        try:
            stock_symbol = DATA_OTC.data[d].stock_symbol
            industry     = DATA_OTC.data[d].industry
            if industry:
                if industry not in TWStock["OTC"].keys():
                    TWStock["OTC"][industry] = list()
                stock_symbol = stock_symbol.split('\u3000')
                TWStock["OTC"][industry].append({stock_symbol[0] : stock_symbol[1]})
        except:
            pass
            # print("上櫃認購(售)權證")
    logger.info("Finish Generating OTC List")
    
    logger.info("Start Writing The File")
    fp.write(json.dumps(TWStock, ensure_ascii=False))
    fp.close()
    logger.info("Finish Writing The File")

if __name__ == '__main__':
    main()
