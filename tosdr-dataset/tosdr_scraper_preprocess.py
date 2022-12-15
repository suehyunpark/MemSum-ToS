from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from tqdm import tqdm
import html
import re
from random import sample, randint
import logging
import pickle
from time import sleep
from ftlangdetect import detect  
# fasttext is the fastest & most accurate library for language detection, but requires manual downloading of a pre-trained model; 
# this library is a wrapper of fasttext and gets rid of the need of it


def set_chrome_driver():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36')
    # chrome_options.add_argument('--disable-gpu')
    # chrome_options.add_argument('headless')
    # chrome_options.add_argument('window-size=1920x1080')
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    # driver = webdriver.Chrome('/Users/suepark/.wdm/drivers/chromedriver/mac_arm64/107.0.5304/chromedriver', options=chrome_options)
    return driver

class BlockedError(Exception):
    pass

class ToSDRScraper():
    def __init__(self, pickle_name='tosdr_block', log_file='./incomplete_docs_log.log'):
        self.driver = set_chrome_driver()
        self.base_url = 'https://edit.tosdr.org'
        self.pickle_name = pickle_name
        
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - [%(funcName)s] - %(message)s',
            handlers=[logging.FileHandler(log_file), logging.StreamHandler()]
        )
        self.logger = logging.getLogger('tosdr_logger')
        
        self.has_letter = re.compile("^(?=.*[a-zA-Z])")

        self.data = []

        
    def login(self, email='shparksue@gmail.com', password='2022-2NLPproject'):
        """Activates authenticated session"""
        self.driver.get('https://edit.tosdr.org/users/sign_in')
        
        self.driver.find_element(By.ID, 'user_email').send_keys(email)
        self.driver.find_element(By.ID, 'user_password').send_keys(password)
        self.driver.find_element(By.XPATH, '//*[@id="new_user"]/div[2]/input').click()
    
    
    def get_soup(self, url: str, timeout=0, wait_to_load=0):
        """Get the HTML source to directly instantiate a new BeautifulSoup object (possibly for debugging purposes)"""
        sleep(randint(3, 10))  # mimic human requests
        if timeout:
            title = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, 'h2'))
            )
            print(f"{title} is found, page is now visible")
        self.driver.get(url)
        if wait_to_load:
            element = WebDriverWait(self.driver, wait_to_load).until(
                EC.presence_of_element_located((By.TAG_NAME, 'table'))
            )
            print(f"{element} is found, page is now visible")
        html_source = self.driver.page_source
        return BeautifulSoup(html_source, 'html.parser')
    
    
    def scrape_services(self):
        """Get urls for the annotated documents of each service and process each document"""
        services_soup = self.get_soup(url='https://edit.tosdr.org/services', wait_to_load=10)  # takes some time to load the full page
        table = services_soup.select_one('table.table.table-striped')
        all_services = table.find_all('tr', {'data-classification': ['A', 'B', 'C', 'D', 'E']})
        print("Total number of services:", len(all_services))
        block_num = 0
        # print(all_services[1201:])
        
        for i, row in enumerate(tqdm(all_services)):
            columns = row.find_all('td')
            service = columns[1].text.strip()
            url = self.base_url + columns[4].find('a', href=True)['href']
            self.scrape_documents_per_service(service, url)
            # if i == 10:
                # print(self.data)
                
            if i > 0 and i % 100 == 0:
                self._dump_pickle(f'./pickles/{self.pickle_name}_{block_num}.pickle', self.data)
                self.data = []  # renew
                block_num += 1
                
        self._dump_pickle(f'./pickles/{self.pickle_name}_{block_num}.pickle', self.data)
            
            
    def scrape_documents_per_service(self, service_name, url):
        """Scrape each ToS document of each service and write the data into .jsonl format"""
        try:
            documents_soup = self.get_soup(url)
            if not documents_soup.select('h2'):  # has service title
                raise BlockedError
        except BlockedError:
            print('The website has detected abusive requests. Waiting to try again after 10 minutes...')
            documents_soup = self.get_soup(url, timeout=620)  # wait for 10 minutes and 20+ seconds
        finally:
            documents = documents_soup.select('div.panel.panel-default')
            if not documents:
                self.logger.info(f"No document for (service: {service_name})! {url}")
                return
            
            for document_elements in documents:
                document_data = self._parse_document(service_name, url, document_elements)
                if not document_data:
                    continue
                self.data.append(document_data)
         
    
    def _parse_document(self, service_name, url, document_elements):
        """Parse each document return a dictionary of the structured information"""
        title = document_elements.select_one('h3').text
        original_text, summary = self._generate_document_data(document_elements)
        if not original_text:
            self.logger.info(f"No content inside (service: {service_name}, document: {title})! {url}")
            return None
        if not summary:
            self.logger.info(f"No annotation for (service: {service_name}, document: {title})! {url}")
            return None
        if not self._detect_english(original_text):
            self.logger.info(f"Not English or document is too short (service: {service_name}, document: {title})! {url}")
            return None
        
        return {'text': original_text,
                'summary': summary}
        
    def _generate_document_data(self, document_elements):
        """Iterate through the sections and divide the parsed sections of the documents into the original text and summary"""
        # NOTE: the first or last sentence in the annotated section, and the sentences before and after it can contain incomplete phrases
        full_doc = []
        summary = []
        ptr = document_elements.select_one('.panel-body.documentContent > p')
        for section in ptr.next_siblings:  # iterate through the contents
            if section.text.strip():  # tag content is not empty
                sentences = self._parse_section(section.text)
                if section.select('a'):  # is hyperlinked, i.e., annotated by users
                    summary.extend(sentences)
                full_doc.extend(sentences)
        return full_doc, summary
    
    
    def _parse_section(self, text):
        """Break down each section into sentences"""
        sentences = []
        for segments in re.split('<.+?>', text):
            sentences.extend(self._clean_segments([segment.strip() for segment in segments.split('\n') if segment.strip()]))
        return sentences
    
    def _clean_segments(self, segments):
        """Clean segments more robustly"""
        cleaned_segments = []
        for segment in segments:
            decoded = html.unescape(segment)  # convert html entities into unicode
            decoded = BeautifulSoup(decoded, 'lxml').get_text(strip=True)  # get only text from html string
            decoded = decoded.replace(u'\xa0', u' ')
            if self.has_letter.match(decoded):  # the segment string must have at least one letter
                cleaned_segments.append(decoded)
        return cleaned_segments
    
    def _detect_english(self, original_text):
        """Returns True if the text is in English, otherwise False"""
        # NOTE: At first try, it takes about 30s to download the pre-trained FastText model
        result = set()
        try:
            sentences = sample(original_text, 3)
        except ValueError as e:
            print(e)
            return False
        
        for sentence in sentences:
            result.add(detect(text=sentence)['lang'])
        return True if 'en' in result else False
    
    def _dump_pickle(self, file_path, object):
        with open(file_path, 'wb') as handle:
            pickle.dump(object, handle)
    

if __name__== '__main__':
    # scraper = ToSDRScraper()
    scraper = ToSDRScraper()
    scraper.login()
    scraper.scrape_services()