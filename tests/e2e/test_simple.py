from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

class SimpleE2ETest(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # This automatically downloads and manages ChromeDriver
        service = Service(ChromeDriverManager().install())
        
        from selenium.webdriver.chrome.options import Options
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Run without opening browser
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        cls.driver = webdriver.Chrome(service=service, options=chrome_options)
    
    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        super().tearDownClass()
    
    def test_homepage_loads(self):
        """Test that homepage loads"""
        self.driver.get(f'{self.live_server_url}/')
        self.assertIn('Jersey Artwork', self.driver.title)
