import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
from dotenv import load_dotenv
from loguru import logger

class BitHumenDownloader:
    def __init__(self):
        load_dotenv()
        self.base_url = "https://bithumen.be"
        self.username = os.getenv('BITHUMEN_USERNAME')
        self.password = os.getenv('BITHUMEN_PASSWORD')
        self.download_dir = os.getenv('DOWNLOAD_DIR', os.path.join(os.path.expanduser('~'), 'Downloads'))
        self.headless = os.getenv('HEADLESS', 'true').lower() == 'true'
        logger.info(f"Initializing BitHumenDownloader with download_dir: {self.download_dir}")
        self.setup_driver()

    def setup_driver(self):
        """Initialize the Chrome WebDriver with custom options"""
        chrome_options = webdriver.ChromeOptions()
        
        # Get Chrome flags from environment or use defaults
        chrome_flags = os.getenv('CHROME_FLAGS', '--headless=new --no-sandbox --disable-dev-shm-usage --disable-gpu')
        for flag in chrome_flags.split():
            chrome_options.add_argument(flag)
        logger.debug(f"Chrome flags: {chrome_flags}")
        
        # Set download directory and preferences
        prefs = {
            "download.default_directory": self.download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
            "profile.default_content_settings.popups": 0,
            "profile.default_content_setting_values.automatic_downloads": 1
        }
        chrome_options.add_experimental_option("prefs", prefs)
        chrome_options.binary_location = "/usr/bin/google-chrome-stable"
        
        # Ensure download directory exists and has proper permissions
        os.makedirs(self.download_dir, exist_ok=True)
        logger.info(f"Created download directory: {self.download_dir}")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)
        logger.success("Chrome WebDriver initialized successfully")

    def login(self):
        """Handle the login process"""
        try:
            logger.info("Attempting to login to BitHumen")
            self.driver.get(f"{self.base_url}/login.php")
            
            # Fill in login form
            username_field = self.wait.until(EC.presence_of_element_located((By.NAME, "username")))
            password_field = self.driver.find_element(By.NAME, "password")
            
            username_field.send_keys(self.username)
            password_field.send_keys(self.password)
            logger.debug("Login form filled")
            
            # Check if captcha is present
            captcha_element = self.driver.find_elements(By.CLASS_NAME, "g-recaptcha")
            if captcha_element:
                logger.warning("Captcha detected! Please solve the captcha manually.")
                input("Press Enter after solving the captcha...")
            
            # Submit form
            password_field.submit()
            logger.debug("Login form submitted")
            
            # Wait for successful login
            self.wait.until(EC.url_changes(f"{self.base_url}/login.php"))
            
            # Verify we're logged in by checking if we're redirected to my.php
            if "/my.php" in self.driver.current_url:
                logger.success("Login successful")
                return True
            else:
                logger.error("Login failed - unexpected redirect")
                return False
            
        except TimeoutException:
            logger.error("Login failed - timeout")
            return False
        except Exception as e:
            logger.exception("Login failed with unexpected error")
            return False

    def search(self, query):
        """Perform a search and return results"""
        try:
            logger.info(f"Searching for: {query}")
            # Navigate to search page and wait for it to load
            search_url = f"{self.base_url}/browse.php"
            self.driver.get(search_url)
            self.wait.until(EC.presence_of_element_located((By.NAME, "search")))
            
            # Find and fill search input
            search_input = self.driver.find_element(By.NAME, "search")
            search_input.clear()
            search_input.send_keys(query)
            
            # Find and click the submit button
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "input[type='submit'][value='Keresés']")
            submit_button.click()
            logger.debug("Search form submitted")
            
            # Find the torrent table by its ID
            results_table = self.wait.until(EC.presence_of_element_located((By.ID, "torrenttable")))
            
            # Get all rows except the header row (with colhead class)
            rows = results_table.find_elements(By.CSS_SELECTOR, "tr:not(.colhead)")
            
            results = []
            # Skip the first row just to be safe
            for row in rows[1:]:
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) < 2:  # Need at least 2 cells
                        continue
                    
                    # Get the title and download link from the second cell
                    name_cell = cells[1]
                    links = name_cell.find_elements(By.TAG_NAME, "a")
                    if not links:
                        continue
                        
                    # First link is usually the details link
                    details_link = next((link for link in links if 'details.php' in link.get_attribute('href')), None)
                    if not details_link:
                        continue
                        
                    title = details_link.text.strip()
                    if not title:
                        continue
                        
                    # Store both title and details link
                    results.append({
                        'title': title,
                        'details_url': details_link.get_attribute('href')
                    })
                    logger.debug(f"Found torrent: {title}")
                except Exception as e:
                    logger.warning(f"Error parsing row: {str(e)}")
                    continue
            
            logger.success(f"Found {len(results)} results")
            return results
            
        except TimeoutException:
            logger.error("Search failed - timeout")
            return []
        except Exception as e:
            logger.exception("Search failed with unexpected error")
            return []

    def download_torrent(self, details_url):
        """Download a torrent file from its details page"""
        try:
            # Navigate to the details page
            logger.info(f"Navigating to details page: {details_url}")
            self.driver.get(details_url)
            
            # Verify we're on the correct page
            if "details.php" not in self.driver.current_url:
                error_msg = f"Unexpected URL after navigation: {self.driver.current_url}"
                logger.error(error_msg)
                return False, error_msg
            
            # Try to find download link immediately first
            download_link = None
            try:
                # Try direct find first without waiting
                download_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='download.php'][href*='id=']")
                if download_links:
                    download_link = download_links[0]
                    logger.debug("Found download link immediately")
                else:
                    # Try generic download link
                    download_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='download.php']")
                    if download_links:
                        download_link = download_links[0]
                        logger.debug("Found generic download link immediately")
            except Exception as e:
                logger.debug(f"Immediate link search failed: {e}, will try with wait")
            
            # If immediate find failed, try with a shorter wait
            if not download_link:
                try:
                    # Use a shorter timeout of 3 seconds
                    quick_wait = WebDriverWait(self.driver, 3)
                    download_link = quick_wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='download.php'][href*='id=']"))
                    )
                    logger.debug("Found download link with wait")
                except TimeoutException:
                    try:
                        download_link = quick_wait.until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='download.php']"))
                        )
                        logger.debug("Found generic download link with wait")
                    except TimeoutException:
                        error_msg = "Download link not found on page"
                        logger.error(error_msg)
                        logger.debug("Page source for debugging:")
                        logger.debug(self.driver.page_source[:500])
                        return False, error_msg
            
            # Get the download URL and expected filename
            download_url = download_link.get_attribute('href')
            # Try to get the torrent name from the page title or details
            try:
                torrent_name = self.driver.find_element(By.CSS_SELECTOR, "h1, .details-title").text.strip()
            except:
                torrent_name = "unknown"
            logger.info(f"Found download URL: {download_url} for torrent: {torrent_name}")
            
            # Get initial file list and timestamps
            try:
                initial_files = {}
                for f in os.listdir(self.download_dir):
                    path = os.path.join(self.download_dir, f)
                    if os.path.isfile(path):
                        initial_files[f] = os.path.getmtime(path)
            except Exception as e:
                error_msg = f"Error accessing download directory: {str(e)}"
                logger.error(error_msg)
                return False, error_msg
            
            # Click download link
            download_link.click()
            logger.debug("Clicked download link")
            
            # Wait for new file to appear in download directory (up to 30 seconds)
            max_wait = 30
            start_time = time.time()
            while time.time() - start_time < max_wait:
                try:
                    current_files = {}
                    for f in os.listdir(self.download_dir):
                        path = os.path.join(self.download_dir, f)
                        if os.path.isfile(path):
                            current_files[f] = os.path.getmtime(path)
                    
                    # Find new or modified files
                    new_files = []
                    for fname, mtime in current_files.items():
                        if fname not in initial_files or mtime > initial_files[fname]:
                            new_files.append(fname)
                    
                    if new_files:
                        # Sort by modification time to get the most recent file
                        new_files.sort(key=lambda x: current_files[x], reverse=True)
                        downloaded_file = new_files[0]
                        logger.success(f"Download completed: {torrent_name}")
                        return True, None
                except Exception as e:
                    error_msg = f"Error checking download directory: {str(e)}"
                    logger.error(error_msg)
                    return False, error_msg
                time.sleep(1)
            
            error_msg = "Timeout waiting for download to complete"
            logger.error(error_msg)
            return False, error_msg
            
        except Exception as e:
            logger.exception("Download failed with unexpected error")
            return False, str(e)

    def close(self):
        """Clean up resources"""
        if self.driver:
            self.driver.quit()
            logger.info("WebDriver closed")

def main():
    downloader = BitHumenDownloader()
    
    try:
        if downloader.login():
            logger.success("Successfully logged in!")
            
            while True:
                query = input("Enter search term (or 'quit' to exit): ")
                if query.lower() == 'quit':
                    break
                    
                results = downloader.search(query)
                if results:
                    logger.info(f"\nFound {len(results)} results:")
                    for i, result in enumerate(results, 1):
                        print(f"{i}. {result['title']}")
                    
                    # Ask user to select a torrent
                    while True:
                        try:
                            choice = input("\nEnter number to download (or 'n' for new search): ")
                            if choice.lower() == 'n':
                                break
                            
                            idx = int(choice) - 1
                            if 0 <= idx < len(results):
                                selected = results[idx]
                                logger.info(f"Selected: {selected['title']}")
                                success, error = downloader.download_torrent(selected['details_url'])
                                if success:
                                    logger.success("Download completed successfully")
                                else:
                                    logger.error(f"Failed to download torrent: {error}")
                                break
                            else:
                                logger.warning("Invalid selection, try again")
                        except ValueError:
                            logger.warning("Please enter a valid number")
                else:
                    logger.warning("No results found")
                    
        else:
            logger.error("Login failed!")
            
    finally:
        downloader.close()

if __name__ == "__main__":
    main()
