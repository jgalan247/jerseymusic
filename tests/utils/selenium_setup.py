"""
Selenium setup and configuration for E2E testing
"""
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.conf import settings
import time
import requests


class SeleniumTestCase(StaticLiveServerTestCase):
    """Base class for Selenium tests"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.driver = cls.create_driver()
        cls.driver.implicitly_wait(10)
        cls.driver.set_window_size(1920, 1080)
    
    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super().tearDownClass()
    
    @classmethod
    def create_driver(cls):
        """Create and configure the Selenium WebDriver"""
        browser = getattr(settings, 'SELENIUM_WEBDRIVER', 'chrome').lower()
        headless = getattr(settings, 'SELENIUM_HEADLESS', True)
        
        if browser == 'chrome':
            return cls.create_chrome_driver(headless)
        elif browser == 'firefox':
            return cls.create_firefox_driver(headless)
        else:
            raise ValueError(f"Unsupported browser: {browser}")
    
    @classmethod
    def create_chrome_driver(cls, headless=True):
        """Create Chrome WebDriver"""
        options = ChromeOptions()
        
        if headless:
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
        
        # Additional Chrome options for stability
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-logging')
        options.add_argument('--log-level=3')
        
        # Download directory for testing file downloads
        prefs = {
            'download.default_directory': '/tmp/test_downloads',
            'download.prompt_for_download': False,
            'download.directory_upgrade': True,
            'safebrowsing.enabled': False
        }
        options.add_experimental_option('prefs', prefs)
        
        service = ChromeService(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)
    
    @classmethod
    def create_firefox_driver(cls, headless=True):
        """Create Firefox WebDriver"""
        options = FirefoxOptions()
        
        if headless:
            options.add_argument('--headless')
        
        options.add_argument('--width=1920')
        options.add_argument('--height=1080')
        
        # Firefox profile settings
        options.set_preference('browser.download.folderList', 2)
        options.set_preference('browser.download.dir', '/tmp/test_downloads')
        options.set_preference('browser.helperApps.neverAsk.saveToDisk', 'application/pdf')
        
        service = FirefoxService(GeckoDriverManager().install())
        return webdriver.Firefox(service=service, options=options)
    
    def wait_for_element(self, by, value, timeout=10):
        """Wait for an element to be present"""
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
    
    def wait_for_clickable(self, by, value, timeout=10):
        """Wait for an element to be clickable"""
        return WebDriverWait(self.driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )
    
    def wait_for_text(self, text, timeout=10):
        """Wait for text to appear on the page"""
        return WebDriverWait(self.driver, timeout).until(
            EC.text_to_be_present_in_element((By.TAG_NAME, 'body'), text)
        )
    
    def login_user(self, username, password):
        """Helper to login a user via Selenium"""
        self.driver.get(f'{self.live_server_url}/accounts/login/')
        
        username_input = self.wait_for_element(By.NAME, 'username')
        password_input = self.driver.find_element(By.NAME, 'password')
        submit_button = self.driver.find_element(By.XPATH, '//button[@type="submit"]')
        
        username_input.send_keys(username)
        password_input.send_keys(password)
        submit_button.click()
        
        # Wait for redirect after login
        self.wait_for_element(By.CLASS_NAME, 'user-menu')
    
    def logout_user(self):
        """Helper to logout a user via Selenium"""
        self.driver.get(f'{self.live_server_url}/accounts/logout/')
    
    def take_screenshot(self, name):
        """Take a screenshot for debugging"""
        screenshot_dir = '/tmp/test_screenshots'
        os.makedirs(screenshot_dir, exist_ok=True)
        
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        filename = f'{screenshot_dir}/{name}_{timestamp}.png'
        self.driver.save_screenshot(filename)
        print(f"Screenshot saved: {filename}")
    
    def assert_element_text(self, by, value, expected_text):
        """Assert element contains expected text"""
        element = self.wait_for_element(by, value)
        self.assertEqual(element.text, expected_text)
    
    def assert_url_contains(self, expected_path):
        """Assert current URL contains expected path"""
        self.assertIn(expected_path, self.driver.current_url)
    
    def fill_form(self, form_data):
        """Fill a form with provided data"""
        for field_name, value in form_data.items():
            element = self.driver.find_element(By.NAME, field_name)
            element.clear()
            element.send_keys(value)
    
    def submit_form(self, form_id=None):
        """Submit a form"""
        if form_id:
            form = self.driver.find_element(By.ID, form_id)
            form.submit()
        else:
            submit_button = self.driver.find_element(By.XPATH, '//button[@type="submit"]')
            submit_button.click()


class MailHogTestMixin:
    """Mixin for testing with MailHog"""
    
    MAILHOG_API_URL = 'http://localhost:8025/api/v2'
    
    def get_mailhog_messages(self):
        """Get all messages from MailHog"""
        response = requests.get(f'{self.MAILHOG_API_URL}/messages')
        if response.status_code == 200:
            return response.json()['items']
        return []
    
    def clear_mailhog(self):
        """Clear all messages in MailHog"""
        requests.delete(f'{self.MAILHOG_API_URL}/messages')
    
    def get_latest_email(self, to_address=None):
        """Get the latest email, optionally filtered by recipient"""
        messages = self.get_mailhog_messages()
        
        if to_address:
            messages = [
                msg for msg in messages 
                if any(to_address in recipient['Mailbox'] + '@' + recipient['Domain']
                      for recipient in msg['To'])
            ]
        
        return messages[0] if messages else None
    
    def assert_email_received(self, to_address, subject=None, timeout=5):
        """Assert that an email was received"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            email = self.get_latest_email(to_address)
            if email:
                if subject:
                    self.assertEqual(email['Content']['Headers']['Subject'][0], subject)
                return email
            time.sleep(0.5)
        
        self.fail(f"No email received for {to_address} within {timeout} seconds")
    
    def extract_confirmation_link(self, email):
        """Extract confirmation link from email"""
        import re
        body = email['Content']['Body']
        
        # Adjust regex based on your email template
        pattern = r'http[s]?://[^\\s\\r\\n]+'
        links = re.findall(pattern, body)
        
        # Filter for confirmation links
        confirmation_links = [
            link for link in links 
            if 'confirm' in link or 'activate' in link or 'verify' in link
        ]
        
        return confirmation_links[0] if confirmation_links else None
    
    def verify_email_via_mailhog(self, driver, to_address):
        """Complete email verification using MailHog web interface"""
        # Open MailHog web interface
        original_window = driver.current_window_handle
        driver.execute_script("window.open('http://localhost:8025', '_blank');")
        driver.switch_to.window(driver.window_handles[-1])
        
        # Wait for MailHog to load
        time.sleep(2)
        
        # Find and click the email
        email_element = driver.find_element(
            By.XPATH, 
            f"//div[contains(text(), '{to_address}')]"
        )
        email_element.click()
        
        # Extract and visit confirmation link
        # This depends on your MailHog UI structure
        iframe = driver.find_element(By.TAG_NAME, 'iframe')
        driver.switch_to.frame(iframe)
        
        confirmation_link = driver.find_element(
            By.PARTIAL_LINK_TEXT, 
            'Confirm'
        )
        confirmation_url = confirmation_link.get_attribute('href')
        
        # Close MailHog tab and return to original
        driver.close()
        driver.switch_to.window(original_window)
        
        # Visit confirmation URL
        driver.get(confirmation_url)
        
        return confirmation_url


class E2ETestCase(SeleniumTestCase, MailHogTestMixin):
    """Combined base class for E2E tests with Selenium and MailHog"""
    
    def setUp(self):
        super().setUp()
        self.clear_mailhog()
    
    def register_user(self, username='testuser', email='test@example.com',
                     password='testpass123', confirm_email=True):
        """Complete user registration flow"""
        # Navigate to registration page
        self.driver.get(f'{self.live_server_url}/accounts/register/')
        
        # Fill registration form
        self.fill_form({
            'username': username,
            'email': email,
            'password1': password,
            'password2': password,
        })
        
        # Submit form
        self.submit_form()
        
        # Confirm email if requested
        if confirm_email:
            time.sleep(1)  # Wait for email to be sent
            email_msg = self.assert_email_received(email)
            confirmation_link = self.extract_confirmation_link(email_msg)
            
            if confirmation_link:
                self.driver.get(confirmation_link)
                self.wait_for_text('Your email has been confirmed')
        
        return username, password