from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
import os
from flask import Flask, jsonify, request

app = Flask(__name__)

def login_and_get_cookies(email, password):
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
    
    # Heroku-specific Chrome configuration
    if 'GOOGLE_CHROME_BIN' in os.environ:
        chrome_options.binary_location = os.environ.get('GOOGLE_CHROME_BIN')
    
    if 'CHROMEDRIVER_PATH' in os.environ:
        driver = webdriver.Chrome(
            service=Service(os.environ.get('CHROMEDRIVER_PATH')),
            options=chrome_options
        )
    else:
        # Initialize the Chrome driver for local development
        driver = webdriver.Chrome(options=chrome_options)
    
    try:
        # Set the window size explicitly after browser initialization
        driver.set_window_size(1920, 1080)
        
        # Navigate to the login page
        driver.get("https://www.biopharmcatalyst.com/account/login")
        
        # Reduced initial wait time
        time.sleep(1.5)
        
        # Wait for the login form to load with shorter timeout
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "form"))
        )
        
        # Find the email and password fields - optimized selectors
        try:
            email_field = driver.find_element(By.CSS_SELECTOR, "input[type='email']")
            password_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        except Exception as e:
            print(f"Could not find inputs with CSS selectors. Error: {e}")
            # Try alternative selectors
            try:
                form = driver.find_element(By.TAG_NAME, "form")
                inputs = form.find_elements(By.TAG_NAME, "input")
                if len(inputs) >= 2:
                    email_field = inputs[0]  # First input in form
                    password_field = inputs[1]  # Second input in form
                else:
                    raise Exception("Could not locate email and password fields")
            except Exception as e2:
                print(f"Could not find inputs with form inputs. Error: {e2}")
                # Last resort with XPath
                email_field = driver.find_element(By.XPATH, "//label[contains(text(), 'Email')]/following-sibling::input")
                password_field = driver.find_element(By.XPATH, "//label[contains(text(), 'Password')]/following-sibling::input")
        
        # Enter credentials
        email_field.send_keys(email)
        password_field.send_keys(password)
        
        # Click the login button - optimized selector
        try:
            login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        except:
            try:
                login_button = driver.find_element(By.XPATH, "//button[text()='Login']")
            except:
                form = driver.find_element(By.TAG_NAME, "form")
                login_button = form.find_element(By.TAG_NAME, "button")
        
        login_button.click()
        
        # Wait for login to complete - reduced wait time
        time.sleep(3)
        
        # Get all cookies
        cookies = driver.get_cookies()
        
        return cookies
        
    except Exception as e:
        print(f"An error occurred: {e}")
        raise
    finally:
        # Close the browser
        driver.quit()

@app.route('/')
def home():
    return "Biopharm Catalyst Login Service"

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data or 'email' not in data or 'password' not in data:
        return jsonify({"error": "Email and password are required"}), 400
    
    try:
        all_cookies = login_and_get_cookies(data['email'], data['password'])
        
        # Extract only the specific cookies we need
        biopharm_session = None
        xsrf_token = None
        
        for cookie in all_cookies:
            if cookie['name'] == 'biopharm_user_session':
                biopharm_session = cookie['value']
            elif cookie['name'] == 'XSRF-TOKEN':
                xsrf_token = cookie['value']
        
        # Return JSON response with the cookies
        if biopharm_session and xsrf_token:
            return jsonify({
                "XSRF-TOKEN": xsrf_token,
                "biopharm_user_session": biopharm_session
            }), 200
        else:
            return jsonify({"error": "Failed to retrieve required cookies"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # For local development
    if os.environ.get('PORT'):
        port = int(os.environ.get('PORT'))
    else:
        port = 5001
    
    app.run(host='0.0.0.0', port=port)
