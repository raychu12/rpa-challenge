from datetime import datetime, timedelta
import calendar
import re
import time
import requests
import pandas as pd
from RPA.Robocorp.WorkItems import WorkItems
from RPA.Browser.Selenium import Selenium


class process_logic:
    def __init__(self):
        self.browser = Selenium()
        wi = WorkItems()
        wi.get_input_work_item()
        self.search_phrase = wi.get_work_item_variable('search_phrase')
        self.news_category = wi.get_work_item_variable('news_category')
        self.number_of_months = int(wi.get_work_item_variable('number_of_months'))
        news = {'Title','Date','Description','Filename','Count of Search Phrases','Contains Money?'}
        self.news_df = pd.DataFrame(news)
        self.start_automation()
    
    def start_automation(self):
         "main method to run the logic"
         self.get_news_information()

    def get_months_selected(self):
        "method to get range of months"
        today = datetime.now()
        start_date = today - timedelta(days=30 * self.number_of_months)
        current_month = today.month
        start_month = start_date.month
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
        image_element = self.browser.get_element_attribute("//section[@class='top-section']/child::div/child::div[2]/child::div[2]/descendant::img","src")
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
        position = 1
        months = self.get_months_selected()
        self.open_browser()
        self.browser.click_button("//button[@aria-label='Go to search page']")
        self.browser.wait_until_element_is_visible("//form[@id='search']", timeout= 60)
        self.browser.input_text("//form[@id='search']/child::input",self.search_phrase)
        self.browser.click_button("//form[@id='search']/child::button")
        self.browser.wait_until_element_is_visible("//span[@class='pi pi-arrow-right p-button-icon']", timeout= 60)
        quantity_of_news = self.browser.get_text("//div[@class='search-page-results pt-2']/child::span/child::strong")
        quantity_of_news = int(quantity_of_news)
        try:
            popup = self.browser.is_element_visible("//button[@title='Close']")
            if popup:
                self.browser.click_button("//button[@title='Close']")
            #for should start in 1
            for position in range(1,quantity_of_news+1):
                clicks_needed = position // 10
                if clicks_needed > 0:
                    self.browser.wait_until_element_is_visible("//button[@aria-label='Load More']", timeout=120)
                    for _ in range(clicks_needed):
                        self.browser.click_button("//button[@aria-label='Load More']")
                position_str = str(position)
                self.browser.wait_until_element_is_visible("//div[@trackingcomponentposition='"+position_str+"']/descendant::div[@class='h2']", timeout= 120)
                title = self.browser.get_text("//div[@trackingcomponentposition='"+position_str+"']/descendant::div[@class='h2']")
                self.browser.wait_until_element_is_visible("//div[@trackingcomponentposition='"+position_str+"']/descendant::p", timeout= 120)
                description = self.browser.get_text("//div[@trackingcomponentposition='"+position_str+"']/descendant::p")
                self.browser.wait_until_element_is_visible("//div[@trackingcomponentposition='"+position_str+"']/descendant::div[@class='card-title']/child::a", timeout= 120)
                self.browser.click_element_when_clickable("//div[@trackingcomponentposition='"+position_str+"']/descendant::div[@class='card-title']/child::a", timeout= 120)
                self.browser.wait_until_element_is_visible("//section[@class='top-section']/child::div/child::div[2]/child::div[2]/descendant::p[@class='type-caption']", timeout= 60)
                news_date_raw = self.browser.get_text("//section[@class='top-section']/child::div/child::div[2]/child::div[2]/descendant::p[@class='type-caption']")
                news_date = self.extract_date(news_date_raw) 
                news_month = news_date.strftime("%B")
                if news_month in months:
                            count_phrases = self.extract_count_search_phrases((title+" "+description),self.search_phrase)
                            contains_money = self.title_contains_money((title+" "+description))
                            filename = self.download_image(position_str)
                            new_data = pd.DataFrame({'Title':[title],'Date':[news_date],'Description':[description],'Filename':[filename],'Count of Search Phrases':[count_phrases],'Contains Money?':[contains_money]})
                            self.news_df = pd.concat([self.news_df, new_data], ignore_index=True)
                            self.browser.go_back()
                position+=1
            self.news_df.to_excel("output/"+self.search_phrase+" news.xlsx")
        except Exception as error:
                        print(error)
