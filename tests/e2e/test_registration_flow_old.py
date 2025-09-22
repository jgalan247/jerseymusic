"""
Selenium E2E tests for user registration with email verification
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
import requests
import time
import re


class RegistrationE2ETest(StaticLiveServerTestCase):
    """Test complete registration flow with email verification"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Setup Chrome in headless mode
        from selenium.webdriver.chrome.options import Options
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        cls.driver = webdriver.Chrome(options=chrome_options)
        cls.driver.implicitly_wait(10)
        
        # Clear MailHog messages
        requests.delete('http://localhost:8025/api/v1/messages')
    
    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super().tearDownClass()
    
    def test_customer_registration_with_email_verification(self):
        """Test: Register → Receive Email → Verify → Login"""
        # Step 1: Navigate to registration page
        self.driver.get(f'{self.live_server_url}/accounts/register/customer/')
        
        # Step 2: Fill registration form
        self.driver.find_element(By.NAME, 'email').send_keys('testcustomer@example.com')
        self.driver.find_element(By.NAME, 'first_name').send_keys('Test')
        self.driver.find_element(By.NAME, 'last_name').send_keys('Customer')
        self.driver.find_element(By.NAME, 'password1').send_keys('TestPass123!')
        self.driver.find_element(By.NAME, 'password2').send_keys('TestPass123!')
        
        # Step 3: Submit form
        submit_button = self.driver.find_element(By.XPATH, '//button[@type="submit"]')
        submit_button.click()
        
        # Step 4: Check for success message
        time.sleep(2)  # Wait for email to be sent
        
        # Step 5: Get verification email from MailHog
        response = requests.get('http://localhost:8025/api/v2/messages')
        messages = response.json()['items']
        
        # Find email for our test user
        verification_email = None
        for msg in messages:
            if 'testcustomer@example.com' in str(msg['To']):
                verification_email = msg
                break
        
        self.assertIsNotNone(verification_email, "Verification email not found")
        
        # Step 6: Extract verification link from email
        email_body = verification_email['Content']['Body']
        # Pattern for verification link
        link_pattern = r'http://[^/]+/accounts/verify/([^/]+)/([^/]+)/'
        match = re.search(link_pattern, email_body)
        
        self.assertIsNotNone(match, "Verification link not found in email")
        
        # Step 7: Visit verification link
        verification_url = match.group(0)
        self.driver.get(verification_url)
        
        # Step 8: Check for verification success
        success_element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'alert-success'))
        )
        self.assertIn('verified', success_element.text.lower())
        
        # Step 9: Try to login with verified account
        self.driver.get(f'{self.live_server_url}/accounts/login/')
        self.driver.find_element(By.NAME, 'email').send_keys('testcustomer@example.com')
        self.driver.find_element(By.NAME, 'password').send_keys('TestPass123!')
        self.driver.find_element(By.XPATH, '//button[@type="submit"]').click()
        
        # Step 10: Verify logged in (should redirect to gallery or home)
        self.assertNotIn('/login/', self.driver.current_url)


class PurchaseFlowE2ETest(StaticLiveServerTestCase):
    """Test complete purchase flow in browser"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from selenium.webdriver.chrome.options import Options
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        cls.driver = webdriver.Chrome(options=chrome_options)
        cls.driver.implicitly_wait(10)
        
        # Create test data
        from django.contrib.auth import get_user_model
        from artworks.models import Artwork
        User = get_user_model()
        
        cls.artist = User.objects.create_user(
            username='artist@test.com',
            email='artist@test.com',
            password='pass123',
            user_type='artist'
        )
        
        cls.customer = User.objects.create_user(
            username='customer@test.com',
            email='customer@test.com',
            password='pass123',
            user_type='customer',
            email_verified=True
        )
        
        cls.artwork = Artwork.objects.create(
            title='Test Artwork',
            slug='test-artwork',
            artist=cls.artist,
            description='Test description',
            price=100.00,
            status='active',
            is_available=True
        )
    
    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super().tearDownClass()
    
    def test_add_to_cart_and_checkout(self):
        """Test: Login → Browse → Add to Cart → View Cart"""
        # Step 1: Login
        self.driver.get(f'{self.live_server_url}/accounts/login/')
        self.driver.find_element(By.NAME, 'email').send_keys('customer@test.com')
        self.driver.find_element(By.NAME, 'password').send_keys('pass123')
        self.driver.find_element(By.XPATH, '//button[@type="submit"]').click()
        
        # Step 2: Browse gallery
        self.driver.get(f'{self.live_server_url}/gallery/')
        
        # Step 3: Click on artwork
        artwork_link = self.driver.find_element(
            By.XPATH, 
            f'//a[contains(@href, "/artwork/{self.artwork.pk}/")]'
        )
        artwork_link.click()
        
        # Step 4: Add to cart
        add_to_cart_button = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//button[contains(text(), "Add to Cart")]'))
        )
        add_to_cart_button.click()
        
        # Step 5: View cart
        time.sleep(1)  # Wait for cart update
        self.driver.get(f'{self.live_server_url}/cart/')
        
        # Step 6: Verify item in cart
        cart_item = self.driver.find_element(By.CLASS_NAME, 'cart-item')
        self.assertIn('Test Artwork', cart_item.text)
