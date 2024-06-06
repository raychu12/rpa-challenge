import calendar
import logging
import re
import requests
from datetime import datetime, timedelta

import pandas as pd
from RPA.Browser.Selenium import Selenium
from RPA.Robocorp.WorkItems import WorkItems
class ProcessLogic:
    def __init__(self):
        logging.basicConfig(level=logging.INFO)
        self.browser = Selenium()
        work_items = WorkItems()
        work_items.get_input_work_item()
        self.search_phrase = work_items.get_work_item_variable('search_phrase')
        self.news_category = work_items.get_work_item_variable('news_category')
        self.num_months = int(work_items.get_work_item_variable('number_of_months'))
        news_columns = [
            'Title', 'Date', 'Description', 'Filename',
            'Count of Search Phrases', 'Contains Money?'
        ]
        self.news_df = pd.DataFrame(columns=news_columns)
        self.start_automation()
    
    def start_automation(self):
        """
        Initiates the automation process.
        """      
        self.get_news_information()

    def get_selected_months_range(self):
        """
        Retrieve a range of selected months for the search.
        Returns:
            list: A list of month names within the calculated range.
        """
        current_date = datetime.now()
        start_date = current_date - timedelta(days=30 * self.num_months)
        current_month = current_date.month
        start_month = start_date.month

        if start_month <= current_month:
            months = [calendar.month_name[i] for i in range(start_month, current_month + 1)]
        else:
            months = [calendar.month_name[i] for i in range(start_month, 13)] + \
                     [calendar.month_name[i] for i in range(1, current_month + 1)]

        return months

    def open_browser(self):
        """
        Open a web browser and navigate to a specific URL.
        Raises:
            Exception: If there's an error while opening the browser or waiting for the element to be visible.
        """
        try:
            self.browser.open_available_browser("https://gothamist.com/")
            self.browser.wait_until_element_is_visible("//span[text()='Donate']", timeout=200)
        except Exception as error:
            logging.error("Failed to open browser or wait for element: %s", error)

    def extract_count_search_phrases(self, title, text):
        """
        Extract the count of occurrences of a given title phrase in a text.
        Args:
            title (str): The title phrase to search for.
            text (str): The text to search within.
        Returns:
            int: The count of occurrences of the title phrase in the text.
        """
        pattern = re.escape(title)
        matches = re.findall(pattern, text)
        return len(matches)
    
    def title_contains_money(self, text):
        """
        Check if the title contains a monetary amount.
        Args:
            text (str): The text to search within.
        Returns:
            bool: True if the title contains a monetary amount, False otherwise.
        """
        pattern = r'\$\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|\d+\s(?:dollars|USD)'
        matches = re.findall(pattern, text)
        return bool(matches)
    
    def extract_date(self, text):
        """
        Extract the date from a text.
        Args:
            text (str): The text containing the date information.
        Returns:
            datetime: The extracted date object, or None if not found.
        """
        match = re.search(r'Published (\w+ \d{1,2}, \d{4})', text)
        if match:
            date_str = match.group(1)
            return datetime.strptime(date_str, '%b %d, %Y')
        return None
    
    def download_image(self, position):
        """
        Download an image from a specified position.
        Args:
            position (int): The position of the image to download.
        Returns:
            str: The filename of the downloaded image, or an error message if the download fails.
        """
        image_src = self.browser.get_element_attribute(
            "//section[@class='top-section']/child::div/child::div[2]/child::div[2]/descendant::img", "src"
        )
        response = requests.get(image_src)
        if response.status_code == 200:
            filename = f"new_{self.search_phrase}_{position}.jpg"
            with open(f"output/{filename}", "wb") as f:
                f.write(response.content)
            return filename
        else:
            logging.error("Failed to download image from %s", image_src)
            return "Failed to download image"

    def get_news_information(self):
        """
        Retrieve and process news information.
        """
        months = self.get_selected_months_range()
        self.open_browser()
        self.browser.click_button("//button[@aria-label='Go to search page']")
        self.browser.wait_until_element_is_visible("//form[@id='search']", timeout=100)
        self.browser.input_text("//form[@id='search']/child::input", self.search_phrase)
        self.browser.click_button("//form[@id='search']/child::button")
        self.browser.wait_until_element_is_visible("//span[@class='pi pi-arrow-right p-button-icon']", timeout=60)
        num_news_items = int(self.browser.get_text("//div[@class='search-page-results pt-2']/child::span/child::strong"))

        try:
            if self.browser.is_element_visible("//button[@title='Close']"):
                self.browser.click_button("//button[@title='Close']")

            for position in range(1, num_news_items + 1):
                self.load_more_news(position)
                title, description, news_date = self.extract_news_details(position)
                if news_date and news_date.strftime("%B") in months:
                    self.process_news_item(title, description, position, news_date)

            self.news_df.to_excel(f"output/{self.search_phrase}_news.xlsx")

        except Exception as error:
            logging.error("Error while processing news information: %s", error)

    def load_more_news(self, position):
        """
        Load more news items if needed.
        Args:
            position (int): The current position in the news items list.
        """
        clicks_needed = position // 10
        if clicks_needed > 0:
            self.browser.wait_until_element_is_visible("//button[@aria-label='Load More']", timeout=120)
            for _ in range(clicks_needed):
                self.browser.click_button("//button[@aria-label='Load More']")

    def extract_news_details(self, position):
        """
        Extract details of a news item.
        Args:
            position (int): The position of the news item.
        Returns:
            tuple: A tuple containing the title, description, and date of the news item.
        """
        position_str = str(position)
        self.browser.wait_until_element_is_visible(
            f"//div[@trackingcomponentposition='{position_str}']/descendant::div[@class='h2']", timeout=120
        )
        title = self.browser.get_text(f"//div[@trackingcomponentposition='{position_str}']/descendant::div[@class='h2']")
        self.browser.wait_until_element_is_visible(
            f"//div[@trackingcomponentposition='{position_str}']/descendant::p", timeout=120
        )
        description = self.browser.get_text(f"//div[@trackingcomponentposition='{position_str}']/descendant::p")
        self.browser.wait_until_element_is_visible(
            f"//div[@trackingcomponentposition='{position_str}']/descendant::div[@class='card-title']/child::a",
            timeout=120
        )
        self.browser.click_element_when_clickable(
            f"//div[@trackingcomponentposition='{position_str}']/descendant::div[@class='card-title']/child::a",
            timeout=120
        )
        self.browser.wait_until_element_is_visible(
            "//section[@class='top-section']/child::div/child::div[2]/child::div[2]/descendant::p[@class='type-caption']",
            timeout=60
        )
        news_date_raw = self.browser.get_text(
            "//section[@class='top-section']/child::div/child::div[2]/child::div[2]/descendant::p[@class='type-caption']"
        )
        news_date = self.extract_date(news_date_raw)
        return title, description, news_date

    def process_news_item(self, title, description, position, news_date):
        """
        Process a single news item.
        Args:
            title (str): The title of the news item.
            description (str): The description of the news item.
            position (int): The position of the news item.
            news_date (datetime): The date of the news item.
        """
        count_phrases = self.extract_count_search_phrases((title + " " + description), self.search_phrase)
        contains_money = self.title_contains_money((title + " " + description))
        filename = self.download_image(position)
        new_data = pd.DataFrame({
            'Title': [title],
            'Date': [news_date],
            'Description': [description],
            'Filename': [filename],
            'Count of Search Phrases': [count_phrases],
            'Contains Money?': [contains_money]
        })
        self.news_df = pd.concat([self.news_df, new_data], ignore_index=True)
        self.browser.go_back()
