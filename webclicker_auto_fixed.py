#!/usr/bin/env python3
import random
import time
import os
import platform
from typing import Optional, List
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging
import subprocess

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class WebclickerAutomator:
    def __init__(
        self,
        url: str,
        check_interval: int = 10,
        headless: bool = False,
        username: Optional[str] = None,
        password: Optional[str] = None
    ):
        """
        Initialize the Webclicker automation tool with managed webdriver.
        
        Args:
            url: The URL of the webclicker site
            check_interval: How often to check for new polls (seconds)
            headless: Whether to run the browser in headless mode
            username: Optional username for login
            password: Optional password for login
        """
        self.url = url
        self.check_interval = check_interval
        self.username = username
        self.password = password
        
        # Set up Chrome options
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-popup-blocking")
        
        # Try to find Chrome browser path based on OS
        if platform.system() == "Darwin":  # macOS
            # Check for common Chrome locations on macOS
            chrome_paths = [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Chrome.app/Contents/MacOS/Chrome"
            ]
            
            for path in chrome_paths:
                if os.path.exists(path):
                    chrome_options.binary_location = path
                    logger.info(f"Using Chrome binary at: {path}")
                    break
        
        # Initialize the Chrome driver
        try:
            # Try the simple approach first
            self.driver = webdriver.Chrome(options=chrome_options)
        except Exception as e:
            logger.warning(f"Simple Chrome initialization failed: {e}")
            logger.info("Trying alternative approach with browser detection...")
            
            # Get Chrome version to use matching driver
            try:
                if platform.system() == "Darwin":  # macOS
                    # On macOS, try to get Chrome version
                    chrome_path = chrome_options.binary_location or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
                    cmd = f"'{chrome_path}' --version"
                    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    stdout, stderr = process.communicate()
                    version_output = stdout.decode('utf-8').strip()
                    logger.info(f"Chrome version info: {version_output}")
                
                # Last resort: use Chrome directly with default service
                self.driver = webdriver.Chrome(options=chrome_options)
                
            except Exception as second_error:
                logger.error(f"Failed to initialize Chrome driver: {second_error}")
                raise Exception("Could not initialize Chrome driver. Make sure Chrome is installed.") from second_error
        
        self.wait = WebDriverWait(self.driver, 10)
        
    def login(self) -> bool:
        """Perform login if credentials are provided."""
        if not (self.username and self.password):
            logger.info("No login credentials provided, skipping login")
            return False
            
        try:
            # This is a placeholder as the login form details weren't visible
            logger.info("Attempting to log in")
            
            # Look for login fields and buttons
            login_elements = self.driver.find_elements(By.TAG_NAME, "input")
            login_button = None
            
            username_field = None
            password_field = None
            
            for element in login_elements:
                input_type = element.get_attribute("type")
                placeholder = element.get_attribute("placeholder") or ""
                
                if input_type == "text" or "user" in placeholder.lower() or "email" in placeholder.lower():
                    username_field = element
                elif input_type == "password" or "password" in placeholder.lower():
                    password_field = element
            
            # Look for button that might be the login button
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            for button in buttons:
                button_text = button.text.lower()
                if "login" in button_text or "sign in" in button_text or "submit" in button_text:
                    login_button = button
            
            # Fill the form if fields were found
            if username_field and password_field and login_button:
                username_field.send_keys(self.username)
                password_field.send_keys(self.password)
                login_button.click()
                logger.info("Login successful")
                return True
            else:
                logger.warning("Could not identify login form elements")
                return False
                
        except (TimeoutException, NoSuchElementException) as e:
            logger.error(f"Login failed: {e}")
            return False

    def is_poll_active(self) -> bool:
        """Check if there's an active poll."""
        try:
            # Based on the screenshot when no poll is active, there's red text saying "No current poll"
            # When a poll is active, this text should be absent or replaced with something else
            no_poll_elements = self.driver.find_elements(
                By.XPATH, 
                "//*[contains(text(), 'No current poll')]"
            )
            
            if no_poll_elements:
                return False
            
            # Also check for answer buttons (A, B, C, D, E)
            answer_buttons = self.driver.find_elements(
                By.CSS_SELECTOR,
                "button[class*='answer'], .answer-option, button[data-choice]"
            )
            
            # Look for buttons with letters A-E
            letter_buttons = []
            for button in self.driver.find_elements(By.TAG_NAME, "button"):
                if button.text.strip() in ["A", "B", "C", "D", "E"]:
                    letter_buttons.append(button)
            
            return len(answer_buttons) > 0 or len(letter_buttons) > 0
            
        except Exception as e:
            logger.error(f"Error checking for active poll: {e}")
            return False
    
    def get_answer_choices(self) -> List[tuple]:
        """Get the available answer choices for the current poll.
        
        Returns:
            List of tuples containing (element, choice_identifier)
        """
        try:
            # Look for buttons with the letters A, B, C, D, E
            choices = []
            
            # First try finding elements with specific attributes
            choice_elements = self.driver.find_elements(
                By.CSS_SELECTOR,
                "button[data-choice], .answer-option, button[class*='answer']"
            )
            
            if not choice_elements:
                # If no elements found with the above selectors, look for buttons with text A-E
                for button in self.driver.find_elements(By.TAG_NAME, "button"):
                    button_text = button.text.strip()
                    if button_text in ["A", "B", "C", "D", "E"]:
                        choices.append((button, button_text))
            else:
                for element in choice_elements:
                    choice_id = element.get_attribute("data-choice") or element.text.strip()
                    if choice_id:
                        choices.append((element, choice_id))
            
            logger.info(f"Found {len(choices)} answer choices")
            return choices
        except Exception as e:
            logger.error(f"Error getting answer choices: {e}")
            return []
    
    def select_random_answer(self, choices: List[tuple]) -> None:
        """Randomly select one of the available answer choices."""
        if not choices:
            logger.warning("No answer choices available")
            return
            
        random_choice = random.choice(choices)
        element, choice_id = random_choice
        
        logger.info(f"Randomly selected answer: {choice_id}")
        
        try:
            # Click the selected choice
            element.click()
            logger.info(f"Successfully clicked on answer {choice_id}")
        except Exception as e:
            logger.error(f"Error selecting answer choice: {e}")
    
    def run(self) -> None:
        """Main loop to continuously check for and answer polls."""
        logger.info(f"Starting WebClicker automation - connecting to {self.url}")
        
        try:
            self.driver.get(self.url)
            self.login()
            
            poll_answered = False
            
            while True:
                if self.is_poll_active():
                    if not poll_answered:
                        logger.info("Active poll detected!")
                        choices = self.get_answer_choices()
                        if choices:
                            self.select_random_answer(choices)
                            poll_answered = True
                            logger.info("Poll answered. Waiting for next poll...")
                        else:
                            logger.warning("Poll is active but no answer choices found")
                else:
                    # Reset the flag when no poll is active
                    if poll_answered:
                        logger.info("No active poll. Waiting for next poll...")
                        poll_answered = False
                
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            logger.info("Automation stopped by user")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        finally:
            self.driver.quit()
            logger.info("WebClicker automation stopped")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Automatically answer WebClicker polls")
    parser.add_argument("--url", type=str, default="https://webclicker.web.app/student/", help="WebClicker URL")
    parser.add_argument("--interval", type=int, default=5, help="Poll check interval in seconds")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    parser.add_argument("--username", type=str, help="Username for login")
    parser.add_argument("--password", type=str, help="Password for login")
    
    args = parser.parse_args()
    
    automator = WebclickerAutomator(
        url=args.url,
        check_interval=args.interval,
        headless=args.headless,
        username=args.username,
        password=args.password
    )
    
    automator.run() 