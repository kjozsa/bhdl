import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
from dotenv import load_dotenv

class BitHumenDownloader:
    def __init__(self):
        load_dotenv()
        self.base_url = "https://bithumen.be"
        self.username = os.getenv('BITHUMEN_USERNAME')
        self.password = os.getenv('BITHUMEN_PASSWORD')
        self.download_dir = os.getenv('DOWNLOAD_DIR', os.path.join(os.path.expanduser('~'), 'Downloads'))
        self.setup_driver()

    def setup_driver(self):
        """Initialize the Chrome WebDriver with custom options"""
        chrome_options = webdriver.ChromeOptions()
        # Set download directory
        prefs = {
            "download.default_directory": self.download_dir,
            "download.prompt_for_download": False,
        }
        chrome_options.add_experimental_option("prefs", prefs)
        chrome_options.binary_location = "/usr/bin/google-chrome-stable"
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)

    def login(self):
        """Handle the login process"""
        try:
            self.driver.get(f"{self.base_url}/login.php")
            
            # Fill in login form
            username_field = self.wait.until(EC.presence_of_element_located((By.NAME, "username")))
            password_field = self.driver.find_element(By.NAME, "password")
            
            username_field.send_keys(self.username)
            password_field.send_keys(self.password)
            
            # Check if captcha is present
            captcha_element = self.driver.find_elements(By.CLASS_NAME, "g-recaptcha")
            if captcha_element:
                print("Captcha detected! Please solve the captcha manually.")
                input("Press Enter after solving the captcha...")
            
            # Submit form
            password_field.submit()
            
            # Wait for successful login
            self.wait.until(EC.url_changes(f"{self.base_url}/login.php"))
            
            # Verify we're logged in by checking if we're redirected to my.php
            if "/my.php" in self.driver.current_url:
                print("Login successful, navigating to browse page...")
                return True
            else:
                print("Login failed - unexpected redirect")
                return False
            
        except TimeoutException:
            print("Login failed or timed out")
            return False

    def search(self, query):
        """Perform a search and return results"""
        try:
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
            
            # Wait for results table to load
            time.sleep(2)
            
            # Find the torrent table by its ID
            results_table = self.driver.find_element(By.ID, "torrenttable")
            if not results_table:
                print("No results table found")
                return []
                
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
                    print(f"Found torrent: {title}")
                except Exception as e:
                    print(f"Error parsing row: {str(e)}")
                    continue
            
            print(f"Found {len(results)} results")
            return results
            
        except TimeoutException:
            print("Search failed or timed out")
            return []
        except Exception as e:
            print(f"Search error: {str(e)}")
            return []

    def download_torrent(self, details_url):
        """Download a torrent file from its details page"""
        try:
            # Navigate to the details page
            self.driver.get(details_url)
            
            # Find and click the download link
            download_link = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='download.php']")))
            if download_link:
                download_link.click()
                print("Started torrent download")
                time.sleep(2)  # Wait for download to start
                return True
            return False
        except Exception as e:
            print(f"Error downloading torrent: {str(e)}")
            return False

    def close(self):
        """Clean up resources"""
        if self.driver:
            self.driver.quit()

def main():
    downloader = BitHumenDownloader()
    
    try:
        if downloader.login():
            print("Successfully logged in!")
            
            while True:
                query = input("Enter search term (or 'quit' to exit): ")
                if query.lower() == 'quit':
                    break
                    
                results = downloader.search(query)
                if results:
                    print(f"\nFound {len(results)} results:")
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
                                print(f"Selected: {selected['title']}")
                                if downloader.download_torrent(selected['details_url']):
                                    print("Download completed successfully")
                                else:
                                    print("Failed to download torrent")
                                break
                            else:
                                print("Invalid selection, try again")
                        except ValueError:
                            print("Please enter a valid number")
                else:
                    print("No results found")
                    
        else:
            print("Login failed!")
            
    finally:
        downloader.close()

if __name__ == "__main__":
    main()
