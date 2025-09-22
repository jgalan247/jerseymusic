from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import time

class SimpleRegistrationE2ETest(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        service = Service(ChromeDriverManager().install())
        from selenium.webdriver.chrome.options import Options
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--window-size=1920,1080')
        cls.driver = webdriver.Chrome(service=service, options=chrome_options)
        cls.driver.implicitly_wait(10)
    
    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super().tearDownClass()
    
    def test_registration_form_submission(self):
        """Test basic registration form submission"""
        self.driver.get(f'{self.live_server_url}/accounts/register/customer/')
        
        # Check what fields actually exist on the form
        form_fields = self.driver.find_elements(By.TAG_NAME, 'input')
        print(f"Form fields found: {[f.get_attribute('name') for f in form_fields]}")
        
        # Fill form with CORRECT field names
        try:
            # USERNAME is required!
            self.driver.find_element(By.NAME, 'username').send_keys('testuser123')
            self.driver.find_element(By.NAME, 'email').send_keys('test@example.com')
            self.driver.find_element(By.NAME, 'first_name').send_keys('Test')
            self.driver.find_element(By.NAME, 'last_name').send_keys('User')
            self.driver.find_element(By.NAME, 'password1').send_keys('TestPass123!')
            self.driver.find_element(By.NAME, 'password2').send_keys('TestPass123!')
            
            # Correct field name: phone_number not phone
            self.driver.find_element(By.NAME, 'phone_number').send_keys('01534123456')
            self.driver.find_element(By.NAME, 'address_line_1').send_keys('123 Test St')
            self.driver.find_element(By.NAME, 'postcode').send_keys('JE2 3AB')
            
            # Check if parish is a select field
            parish_selects = self.driver.find_elements(By.TAG_NAME, 'select')
            if parish_selects:
                print(f"Select fields: {[s.get_attribute('name') for s in parish_selects]}")
                parish = Select(self.driver.find_element(By.NAME, 'parish'))
                parish.select_by_value('st_helier')
        except Exception as e:
            print(f"Field error: {e}")
        
        # Scroll to submit button and click with JavaScript
        submit_button = self.driver.find_element(By.XPATH, '//button[@type="submit"]')
        self.driver.execute_script("arguments[0].scrollIntoView(true);", submit_button)
        time.sleep(0.5)  # Wait for scroll
        self.driver.execute_script("arguments[0].click();", submit_button)
        
        # Wait and check for errors
        time.sleep(2)
        
        # Debug output
        print(f"Current URL: {self.driver.current_url}")
        
        # Check for Django form errors
        errors = self.driver.find_elements(By.CLASS_NAME, 'errorlist')
        if errors:
            print(f"Form errors: {[e.text for e in errors]}")
        
        # Check for Bootstrap alerts
        alerts = self.driver.find_elements(By.CLASS_NAME, 'alert')
        if alerts:
            print(f"Alerts: {[a.text for a in alerts]}")
        
        # Success could be redirect or message
        self.assertTrue(
            '/register/customer/' not in self.driver.current_url or
            'verification' in self.driver.page_source.lower() or
            'success' in self.driver.page_source.lower()
        )