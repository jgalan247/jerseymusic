# tests/e2e/test_registration_flow.py

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from django.test import LiveServerTestCase
from django.contrib.auth import get_user_model
import time
import requests

User = get_user_model()


class TestCustomerRegistrationE2E(LiveServerTestCase):
    """End-to-end test for customer registration flow."""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Setup Chrome options for headless testing
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')  # Run in headless mode for CI
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1920,1080')
        
        cls.selenium = webdriver.Chrome(options=chrome_options)
        cls.selenium.implicitly_wait(10)
        cls.wait = WebDriverWait(cls.selenium, 10)
    
    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()
    
    def test_customer_registration_with_email_verification(self):
        """Test complete customer registration including email verification."""
        
        # 1. Navigate to homepage
        self.selenium.get(self.live_server_url)
        
        # 2. Click on Register link
        register_link = self.wait.until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Register"))
        )
        register_link.click()
        
        # 3. Choose Customer registration
        customer_option = self.wait.until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Register as Customer"))
        )
        customer_option.click()
        
        # 4. Fill registration form
        # Wait for form to load
        self.wait.until(EC.presence_of_element_located((By.NAME, "email")))
        
        # Fill in form fields
        self.selenium.find_element(By.NAME, "email").send_keys("e2e_customer@test.com")
        self.selenium.find_element(By.NAME, "first_name").send_keys("E2E")
        self.selenium.find_element(By.NAME, "last_name").send_keys("Customer")
        self.selenium.find_element(By.NAME, "password1").send_keys("SecureE2EPass123!")
        self.selenium.find_element(By.NAME, "password2").send_keys("SecureE2EPass123!")
        
        # Address fields
        self.selenium.find_element(By.NAME, "phone_number").send_keys("+44 7797 123456")
        self.selenium.find_element(By.NAME, "address_line_1").send_keys("123 E2E Street")
        
        # Select parish
        parish_select = Select(self.selenium.find_element(By.NAME, "parish"))
        parish_select.select_by_value("st_helier")
        
        # Postcode
        self.selenium.find_element(By.NAME, "postcode").send_keys("JE2 3AB")
        
        # 5. Submit form
        submit_button = self.selenium.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_button.click()
        
        # 6. Check for success message
        success_message = self.wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "alert-success"))
        )
        assert "check your email" in success_message.text.lower()
        
        # 7. Simulate email verification (check MailHog if running)
        if self.check_mailhog_running():
            verification_link = self.get_verification_link_from_mailhog("e2e_customer@test.com")
            if verification_link:
                self.selenium.get(verification_link)
                
                # Check for verification success
                success = self.wait.until(
                    EC.presence_of_element_located((By.CLASS_NAME, "alert-success"))
                )
                assert "verified successfully" in success.text.lower()
    
    def check_mailhog_running(self):
        """Check if MailHog is running for email testing."""
        try:
            response = requests.get('http://localhost:8025/api/v2/messages', timeout=1)
            return response.status_code == 200
        except:
            return False
    
    def get_verification_link_from_mailhog(self, email):
        """Extract verification link from MailHog."""
        try:
            response = requests.get('http://localhost:8025/api/v2/messages')
            messages = response.json()
            
            for msg in messages['items']:
                if email in str(msg.get('To', [])):
                    # Extract link from email body
                    body = msg['Content']['Body']
                    import re
                    links = re.findall(r'http[s]?://[^\s<>"{}\\|^`\[\]]+verify/[^\s<>"{}\\|^`\[\]]+', body)
                    if links:
                        return links[0]
        except:
            pass
        return None


# tests/e2e/test_artist_journey.py

class TestArtistJourneyE2E(LiveServerTestCase):
    """End-to-end test for artist journey from registration to artwork sale."""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        cls.selenium = webdriver.Chrome(options=chrome_options)
        cls.selenium.implicitly_wait(10)
        cls.wait = WebDriverWait(cls.selenium, 10)
    
    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()
    
    def setUp(self):
        """Create verified artist for testing."""
        self.artist = User.objects.create_user(
            username='e2e_artist',
            email='e2e_artist@test.com',
            password='ArtistPass123!',
            user_type='artist',
            email_verified=True
        )
        from accounts.models import ArtistProfile
        ArtistProfile.objects.create(
            user=self.artist,
            display_name='E2E Artist',
            bio='Test artist for E2E'
        )
    
    def test_artist_upload_artwork_flow(self):
        """Test artist uploading artwork."""
        
        # 1. Login as artist
        self.selenium.get(f"{self.live_server_url}/accounts/login/")
        
        self.selenium.find_element(By.NAME, "email").send_keys("e2e_artist@test.com")
        self.selenium.find_element(By.NAME, "password").send_keys("ArtistPass123!")
        self.selenium.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        
        # 2. Navigate to artist dashboard
        self.wait.until(EC.presence_of_element_located((By.LINK_TEXT, "Dashboard")))
        self.selenium.find_element(By.LINK_TEXT, "Dashboard").click()
        
        # 3. Click upload artwork
        upload_link = self.wait.until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Upload Artwork"))
        )
        upload_link.click()
        
        # 4. Fill artwork form
        self.selenium.find_element(By.NAME, "title").send_keys("E2E Test Painting")
        self.selenium.find_element(By.NAME, "description").send_keys(
            "Beautiful test painting created for E2E testing"
        )
        self.selenium.find_element(By.NAME, "price").send_keys("299.99")
        
        # Select category if present
        try:
            category_select = Select(self.selenium.find_element(By.NAME, "category"))
            category_select.select_by_index(1)  # Select first available category
        except:
            pass
        
        # 5. Submit form (without file upload in test)
        submit_button = self.selenium.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_button.click()
        
        # 6. Check for success
        try:
            success = self.wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "alert-success"))
            )
            assert "uploaded" in success.text.lower()
        except TimeoutException:
            # Check if redirected to artwork list
            assert "/my-artworks/" in self.selenium.current_url
    
    def test_artist_view_sales_dashboard(self):
        """Test artist viewing sales dashboard."""
        
        # Login as artist
        self.selenium.get(f"{self.live_server_url}/accounts/login/")
        self.selenium.find_element(By.NAME, "email").send_keys("e2e_artist@test.com")
        self.selenium.find_element(By.NAME, "password").send_keys("ArtistPass123!")
        self.selenium.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        
        # Navigate to sales dashboard
        self.selenium.get(f"{self.live_server_url}/orders/artist/dashboard/")
        
        # Check dashboard elements
        self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "dashboard-stats")))
        
        # Verify key metrics are displayed
        assert self.selenium.find_element(By.ID, "total-revenue")
        assert self.selenium.find_element(By.ID, "this-month-revenue")
        assert self.selenium.find_element(By.ID, "pending-refunds")


# tests/e2e/test_purchase_e2e.py

class TestPurchaseFlowE2E(LiveServerTestCase):
    """End-to-end test for complete purchase flow."""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        cls.selenium = webdriver.Chrome(options=chrome_options)
        cls.selenium.implicitly_wait(10)
        cls.wait = WebDriverWait(cls.selenium, 10)
    
    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()
    
    def setUp(self):
        """Create test data."""
        # Create artist with artwork
        from accounts.models import ArtistProfile
        from artworks.models import Artwork, Category
        from decimal import Decimal
        
        self.artist = User.objects.create_user(
            username='seller',
            email='seller@test.com',
            password='SellerPass123!',
            user_type='artist'
        )
        self.artist_profile = ArtistProfile.objects.create(
            user=self.artist,
            display_name='Test Seller'
        )
        
        self.category = Category.objects.create(
            name='Paintings',
            slug='paintings'
        )
        
        self.artwork = Artwork.objects.create(
            title='E2E Test Art',
            artist=self.artist,
            category=self.category,
            description='Test artwork for E2E',
            price=Decimal('150.00'),
            status='active',
            is_available=True,
            stock_quantity=5
        )
        
        # Create customer
        self.customer = User.objects.create_user(
            username='buyer',
            email='buyer@test.com',
            password='BuyerPass123!',
            user_type='customer',
            email_verified=True
        )
    
    def test_browse_add_to_cart_checkout(self):
        """Test browsing, adding to cart, and checkout flow."""
        
        # 1. Browse gallery
        self.selenium.get(f"{self.live_server_url}/gallery/")
        
        # 2. Find and click on artwork
        artwork_element = self.wait.until(
            EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "E2E Test Art"))
        )
        artwork_element.click()
        
        # 3. Add to cart
        add_to_cart_button = self.wait.until(
            EC.element_to_be_clickable((By.ID, "add-to-cart"))
        )
        add_to_cart_button.click()
        
        # 4. View cart
        self.selenium.get(f"{self.live_server_url}/cart/")
        
        # Verify item in cart
        cart_item = self.wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "cart-item"))
        )
        assert "E2E Test Art" in cart_item.text
        assert "150.00" in cart_item.text
        
        # 5. Proceed to checkout (login required)
        checkout_button = self.selenium.find_element(By.ID, "proceed-to-checkout")
        checkout_button.click()
        
        # 6. Login
        self.selenium.find_element(By.NAME, "email").send_keys("buyer@test.com")
        self.selenium.find_element(By.NAME, "password").send_keys("BuyerPass123!")
        self.selenium.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        
        # 7. Fill checkout form
        self.wait.until(EC.presence_of_element_located((By.NAME, "first_name")))
        
        self.selenium.find_element(By.NAME, "first_name").send_keys("Test")
        self.selenium.find_element(By.NAME, "last_name").send_keys("Buyer")
        self.selenium.find_element(By.NAME, "email").clear()
        self.selenium.find_element(By.NAME, "email").send_keys("buyer@test.com")
        self.selenium.find_element(By.NAME, "phone_number").send_keys("+44 7797 123456")
        self.selenium.find_element(By.NAME, "address_line_1").send_keys("456 Buyer Street")
        
        parish_select = Select(self.selenium.find_element(By.NAME, "parish"))
        parish_select.select_by_value("st_brelade")
        
        self.selenium.find_element(By.NAME, "postcode").send_keys("JE3 4CD")
        
        # 8. Submit order
        submit_order = self.selenium.find_element(By.ID, "submit-order")
        submit_order.click()
        
        # 9. Check for order confirmation or payment page
        time.sleep(2)  # Wait for redirect
        
        # Should be on payment or confirmation page
        assert "/payment/" in self.selenium.current_url or "/order-confirmation/" in self.selenium.current_url
    
    def test_guest_checkout_redirect(self):
        """Test that guest users are redirected to login for checkout."""
        
        # Add item to cart as guest
        self.selenium.get(f"{self.live_server_url}/gallery/")
        
        # Click on artwork
        self.selenium.find_element(By.PARTIAL_LINK_TEXT, "E2E Test Art").click()
        
        # Add to cart
        self.selenium.find_element(By.ID, "add-to-cart").click()
        
        # Try to checkout
        self.selenium.get(f"{self.live_server_url}/cart/")
        self.selenium.find_element(By.ID, "proceed-to-checkout").click()
        
        # Should be redirected to login
        self.wait.until(EC.presence_of_element_located((By.NAME, "email")))
        assert "/login/" in self.selenium.current_url


# tests/e2e/conftest.py

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


@pytest.fixture(scope="class")
def chrome_driver():
    """Provide Chrome WebDriver for E2E tests."""
    # Setup Chrome options
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--headless')  # Run in headless mode
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    
    # Use webdriver-manager to handle driver installation
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    yield driver
    
    driver.quit()


@pytest.fixture
def live_server_url(live_server):
    """Provide the live server URL for tests."""
    return live_server.url


# tests/e2e/test_helpers.py

class E2ETestHelpers:
    """Helper functions for E2E tests."""
    
    @staticmethod
    def wait_for_element(driver, by, value, timeout=10):
        """Wait for element to be present."""
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        wait = WebDriverWait(driver, timeout)
        return wait.until(EC.presence_of_element_located((by, value)))
    
    @staticmethod
    def login_user(driver, url, email, password):
        """Helper to login a user."""
        driver.get(f"{url}/accounts/login/")
        driver.find_element(By.NAME, "email").send_keys(email)
        driver.find_element(By.NAME, "password").send_keys(password)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        
        # Wait for redirect
        time.sleep(2)
    
    @staticmethod
    def add_to_cart(driver, artwork_id):
        """Helper to add item to cart."""
        driver.find_element(By.ID, "add-to-cart").click()
        
        # Wait for cart update
        time.sleep(1)
    
    @staticmethod
    def fill_jersey_address(driver, address_data):
        """Helper to fill Jersey address fields."""
        driver.find_element(By.NAME, "address_line_1").send_keys(
            address_data.get('line1', '123 Test Street')
        )
        
        if address_data.get('line2'):
            driver.find_element(By.NAME, "address_line_2").send_keys(address_data['line2'])
        
        parish_select = Select(driver.find_element(By.NAME, "parish"))
        parish_select.select_by_value(address_data.get('parish', 'st_helier'))
        
        driver.find_element(By.NAME, "postcode").send_keys(
            address_data.get('postcode', 'JE2 3AB')
        )