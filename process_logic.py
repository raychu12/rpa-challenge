import datetime
import calendar
import re
import requests
import pandas as pd
from RPA.Robocorp.WorkItems import WorkItems
from RPA.Browser.Selenium import Selenium

class process_logic:
    def __init__(self):
        self.browser = Selenium()
        wi = WorkItems()
        wi.get_input_work_item()
        self.search_phrase = wi.get_work_item_variable('politics')
        self.news_category = wi.get_work_item_variable('politics')
        self.number_of_months = int(wi.get_work_item_variable('0'))
        news = {'Title','Date','Description','Filename','Count of Search Phrases','Contains Money?'}
        self.news_df = pd.DataFrame(news)
        self.start_automation()
    
    def start_automation(self):
         "main method to run the logic"
         self.get_news_information()

    def get_months_selected(self):
        "method to get range of months"
        start_month = datetime.now() - datetime.timedelta(days=30 * self.number_of_months)
        current_month = datetime.now().month
        if start_month <= current_month:
            months = [calendar.month_name[i] for i in range(start_month, current_month+1)]
        else:
            months = [calendar.month_name[i] for i in range(start_month+13)] + [calendar.month_name[i] for i in range(1,current_month+1)]
        return months

    def open_browser(self):
        "method to open browser"
        try:
            self.browser.open_available_browser("https://gothamist.com/")
            self.browser.wait_until_element_is_visible("//span[text()='Donate']")
        except Exception as error:
            print("failed opening browser")

    def extract_count_search_phrases(self,title,text):
        "method to get the Count of Search Phrases of the news"
        pattern = re.escape(title)
        matches = re.findall(pattern, text)
        count = len(matches)
        return count
    
    def title_contains_money(self,text):
        "method to get if title of the news contains money"
        pattern = r'\$\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|\d+\s(?:dollars|USD)'
        matches = re.findall(pattern, text)
        if matches:
            return True
        return False
    
    def extract_date(self,text):
        "method to get the date of the news"
        match = re.search(r'Published (\w+ \d{1,2}, \d{4})', text)
        if match:
            date_str = match.group(1)
            date_obj = datetime.strptime(date_str, '%b %d, %Y')
            return date_obj
        return None
    
    def download_image(self,position):
        image_element = self.browser.get_element_attribute("//section[@class='top-section']/child::div/child::div[2]/child::div[1]/descendant::img","src")
        response = requests.get(image_element)
        if response.status_code == 200:
            filename ="new_"+self.search_phrase+"_"+position+".jpg"
            with open("output/"+filename, "wb") as f:
                    f.write(response.content)
            return filename
        else:
            return "Failed to download image"

    def get_news_information(self):
        "method to get the information of the news"
        months = self.get_months_selected()
        self.open_browser()
        self.browser.click_button("//button[@aria-label='Go to search page']")
        self.browser.wait_until_element_is_visible("//form[@id='search']")
        self.browser.input_text("//form[@id='search']/child::input",self.search_phrase)
        self.browser.click_button("//form[@id='search']/child::button")
        self.browser.wait_until_element_is_visible("//div[@class='search-page-results pt-2']/child::span/child::strong")
        quantity_of_news = self.browser.get_text("//div[@class='search-page-results pt-2']/child::span/child::strong")
        try:
            for position in quantity_of_news:
                while(True):
                    load_more_button = self.browser.is_element_visible("//span[text()='Load More']")
                    if load_more_button:
                         self.browser.click_button("//span[text()='Load More']")
                    else:
                         break
                title = self.browser.get_text("//div[@trackingcomponentposition='{}']/descendant::div[@class='h2']").format(position)
                description = self.browser.get_text("//div[@trackingcomponentposition='{}']/descendant::p").format(position)
                self.browser.click_button("//div[@trackingcomponentposition='{}']").format(position)
                news_date_raw = self.browser.get_text("//section[@class='top-section']/child::div/child::div[2]/child::div[1]/descendant::p[@class='type-caption']")
                news_date = self.extract_date(news_date_raw)  
                news_month = news_date.strftime("%B")
                if news_month in months:
                        count_phrases = self.extract_count_search_phrases((title+" "+description),self.search_phrase)
                        contains_money = self.title_contains_money((title+" "+description))
                        filename = self.download_image(position)
                        news_df = news_df.append({'Title':title,'Date':news_date,'Description':description,'Filename':filename,'Count of Search Phrases':count_phrases,'Contains Money?':contains_money}, ignore_index=True)
            news_df.to_excel("output/"+self.search_phrase+" news.xlsx")
        except Exception as error:
                        print("failed getting news")
