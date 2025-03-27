from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
import os
import logging
from flask import Flask, jsonify, request
from threading import Thread
from queue import Queue
import traceback
import platform
import subprocess
import shutil
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Store results of background tasks
task_results = {}

def get_chrome_driver():
    """Initialize and return a Chrome WebDriver with appropriate configuration"""
    logger.info("Setting up Chrome WebDriver")
    
    # Check if running on Render
    is_render = 'RENDER' in os.environ
    logger.info(f"Running on Render: {is_render}")
    
    # Log environment variables
    chrome_bin = os.environ.get('CHROME_BIN')
    chromedriver_path = os.environ.get('CHROMEDRIVER_PATH')
    logger.info(f"CHROME_BIN environment variable: {chrome_bin}")
    logger.info(f"CHROMEDRIVER_PATH environment variable: {chromedriver_path}")
    
    # Check Chrome installation
    try:
        chrome_path = shutil.which('google-chrome')
        logger.info(f"Chrome path from shutil.which: {chrome_path}")
        if chrome_path:
            chrome_version_cmd = f"{chrome_path} --version"
            chrome_version = subprocess.check_output(chrome_version_cmd, shell=True).decode('utf-8').strip()
            logger.info(f"Chrome version: {chrome_version}")
        else:
            logger.warning("Chrome not found in PATH using shutil.which")
            # Try using the environment variable
            if chrome_bin:
                chrome_version_cmd = f"{chrome_bin} --version"
                try:
                    chrome_version = subprocess.check_output(chrome_version_cmd, shell=True).decode('utf-8').strip()
                    logger.info(f"Chrome version from CHROME_BIN: {chrome_version}")
                except Exception as e:
                    logger.error(f"Error getting Chrome version from CHROME_BIN: {str(e)}")
    except Exception as e:
        logger.error(f"Error checking Chrome installation: {str(e)}")
    
    # Set up Chrome options
    chrome_options = Options()
    
    # Add user agent to make the headless browser look more like a regular browser
    user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    chrome_options.add_argument(f'user-agent={user_agent}')
    
    # Run in headless mode
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # Additional options for Render environment
    if is_render:
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--single-process")
        chrome_options.add_argument("--disable-setuid-sandbox")
    
    # Performance optimizations
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--blink-settings=imagesEnabled=false")  # Disable images
    
    # Set page load strategy to eager
    chrome_options.page_load_strategy = 'eager'
    
    # Disable automation flags to avoid detection
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Set Chrome binary location if available
    if chrome_bin:
        chrome_options.binary_location = chrome_bin
        logger.info(f"Set Chrome binary location to: {chrome_bin}")
    
    # Try different methods to initialize the Chrome driver
    driver = None
    errors = []
    
    # Method 1: Try using the ChromeDriver path from environment variable
    if chromedriver_path and not driver:
        try:
            logger.info(f"Attempting to initialize Chrome with ChromeDriver from CHROMEDRIVER_PATH: {chromedriver_path}")
            service = Service(executable_path=chromedriver_path)
            driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("Successfully initialized Chrome with CHROMEDRIVER_PATH")
        except Exception as e:
            error_msg = f"Failed to initialize Chrome with CHROMEDRIVER_PATH: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
    
    # Method 2: Try using the system ChromeDriver
    if not driver:
        try:
            logger.info("Attempting to initialize Chrome with system ChromeDriver")
            driver = webdriver.Chrome(options=chrome_options)
            logger.info("Successfully initialized Chrome with system ChromeDriver")
        except Exception as e:
            error_msg = f"Failed to initialize Chrome with system ChromeDriver: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
    
    # Method 3: Try using webdriver-manager
    if not driver:
        try:
            logger.info("Attempting to initialize Chrome with webdriver-manager")
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("Successfully initialized Chrome with webdriver-manager")
        except Exception as e:
            error_msg = f"Failed to initialize Chrome with webdriver-manager: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
    
    # If all methods failed, raise an exception
    if not driver:
        error_message = "Failed to initialize Chrome WebDriver. Errors:\n" + "\n".join(errors)
        logger.error(error_message)
        raise Exception(error_message)
    
    # Set the window size explicitly after browser initialization
    driver.set_window_size(1920, 1080)
    
    # Set shorter page load timeout
    driver.set_page_load_timeout(30)
    
    return driver

def login_and_get_cookies(email, password, task_id=None):
    logger.info(f"Starting login process for task_id: {task_id}")
    
    driver = None
    try:
        # Initialize the Chrome WebDriver
        driver = get_chrome_driver()
        
        # Navigate to the login page
        logger.info("Navigating to login page")
        driver.get("https://www.biopharmcatalyst.com/account/login")
        
        # Reduced initial wait time
        time.sleep(1)
        
        # Wait for the login form to load with shorter timeout
        logger.info("Waiting for login form")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "form"))
        )
        
        # Find the email and password fields - optimized selectors
        logger.info("Finding login form elements")
        try:
            email_field = driver.find_element(By.CSS_SELECTOR, "input[type='email']")
            password_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
            logger.info("Found email and password fields with CSS selectors")
        except Exception as e:
            logger.warning(f"Could not find inputs with CSS selectors. Error: {e}")
            # Try alternative selectors
            try:
                form = driver.find_element(By.TAG_NAME, "form")
                inputs = form.find_elements(By.TAG_NAME, "input")
                if len(inputs) >= 2:
                    email_field = inputs[0]  # First input in form
                    password_field = inputs[1]  # Second input in form
                    logger.info("Found email and password fields with form inputs")
                else:
                    raise Exception("Could not locate email and password fields")
            except Exception as e2:
                logger.warning(f"Could not find inputs with form inputs. Error: {e2}")
                # Last resort with XPath
                email_field = driver.find_element(By.XPATH, "//label[contains(text(), 'Email')]/following-sibling::input")
                password_field = driver.find_element(By.XPATH, "//label[contains(text(), 'Password')]/following-sibling::input")
                logger.info("Found email and password fields with XPath")
        
        # Enter credentials
        logger.info("Entering credentials")
        email_field.send_keys(email)
        password_field.send_keys(password)
        
        # Click the login button - optimized selector
        logger.info("Clicking login button")
        try:
            login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            logger.info("Found login button with CSS selector")
        except:
            try:
                login_button = driver.find_element(By.XPATH, "//button[text()='Login']")
                logger.info("Found login button with XPath")
            except:
                form = driver.find_element(By.TAG_NAME, "form")
                login_button = form.find_element(By.TAG_NAME, "button")
                logger.info("Found login button with form button")
        
        login_button.click()
        
        # Wait for login to complete - reduced wait time
        logger.info("Waiting for login to complete")
        time.sleep(2)
        
        # Get all cookies
        logger.info("Retrieving cookies")
        cookies = driver.get_cookies()
        
        # Extract only the specific cookies we need
        biopharm_session = None
        xsrf_token = None
        
        for cookie in cookies:
            if cookie['name'] == 'biopharm_user_session':
                biopharm_session = cookie['value']
            elif cookie['name'] == 'XSRF-TOKEN':
                xsrf_token = cookie['value']
        
        result = {
            "success": True,
            "XSRF-TOKEN": xsrf_token,
            "biopharm_user_session": biopharm_session
        }
        
        if not biopharm_session or not xsrf_token:
            result["success"] = False
            result["error"] = "Failed to retrieve required cookies"
            
        logger.info(f"Login process completed for task_id: {task_id}")
        
        if task_id:
            task_results[task_id] = result
            
        return result
        
    except Exception as e:
        error_msg = f"An error occurred: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        result = {
            "success": False,
            "error": str(e)
        }
        if task_id:
            task_results[task_id] = result
        return result
    finally:
        # Close the browser
        if driver:
            logger.info("Closing browser")
            driver.quit()

def background_login(email, password, task_id):
    """Run the login process in a background thread"""
    login_and_get_cookies(email, password, task_id)

@app.route('/')
def home():
    return "Biopharm Catalyst Login Service"

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data or 'email' not in data or 'password' not in data:
        return jsonify({"error": "Email and password are required"}), 400
    
    # Check if async parameter is provided and true
    use_async = data.get('async', False)
    
    if use_async:
        # Generate a task ID
        task_id = str(time.time())
        
        # Start background task
        thread = Thread(target=background_login, args=(data['email'], data['password'], task_id))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "task_id": task_id,
            "message": "Login process started in background"
        }), 202
    else:
        # Synchronous approach with timeout protection
        try:
            result = login_and_get_cookies(data['email'], data['password'])
            
            if result.get("success", False):
                return jsonify({
                    "XSRF-TOKEN": result.get("XSRF-TOKEN"),
                    "biopharm_user_session": result.get("biopharm_user_session")
                }), 200
            else:
                return jsonify({"error": result.get("error", "Unknown error")}), 500
                
        except Exception as e:
            logger.error(f"Error in login route: {str(e)}")
            return jsonify({"error": str(e)}), 500

@app.route('/task/<task_id>', methods=['GET'])
def check_task(task_id):
    """Check the status of a background task"""
    if task_id in task_results:
        result = task_results[task_id]
        
        # Clean up the result if it's completed
        if result.get("success", False):
            # Remove from storage to free memory
            task_data = task_results.pop(task_id)
            return jsonify({
                "XSRF-TOKEN": task_data.get("XSRF-TOKEN"),
                "biopharm_user_session": task_data.get("biopharm_user_session")
            }), 200
        else:
            # Remove from storage to free memory
            task_data = task_results.pop(task_id)
            return jsonify({"error": task_data.get("error", "Unknown error")}), 500
    else:
        return jsonify({"status": "pending", "message": "Task is still processing or does not exist"}), 202

if __name__ == "__main__":
    # For local development
    if os.environ.get('PORT'):
        port = int(os.environ.get('PORT'))
    else:
        port = 5001
    
    app.run(host='0.0.0.0', port=port)
