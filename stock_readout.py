import time
import requests
from bs4 import BeautifulSoup
import pyttsx3

def get_stock_price(ticker):
    url = f"https://finance.yahoo.com/quote/{ticker}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        price_element = soup.find('span', {'data-testid': 'qsp-price'})

        if not price_element:
            price_element = soup.find('fin-streamer', {'data-field': 'regularMarketPrice'})

        if price_element:
            price_str = price_element.text.strip().replace(',', '')
            return float(price_str)
        else:
            return None
    except requests.exceptions.RequestException as e:
        return None
    except ValueError:
        return None
    except Exception as e:
        return None

def check_stock_exists(ticker):
    url = f"https://finance.yahoo.com/quote/{ticker}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=5, allow_redirects=True)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        price_element_1 = soup.find('span', {'data-testid': 'qsp-price'})

        return (response.status_code == 200) and price_element_1
    except requests.exceptions.RequestException:
        return False

def read_stock_price(ticker, price):
    if price is not None:
        # Changed message to only contain the numerical price
        message = f"${price:.2f}"
        print(f"The current price for {ticker.upper()} is {message}") # Keep full print for console
        try:
            engine = pyttsx3.init()
            # Set rate to 5% slower
            current_rate = engine.getProperty('rate')
            engine.setProperty('rate', current_rate * 0.95)

            # Attempt to set a female voice
            voices = engine.getProperty('voices')
            for voice in voices:
                if 'female' in voice.name.lower() or 'zira' in voice.name.lower() or 'samantha' in voice.name.lower():
                    engine.setProperty('voice', voice.id)
                    break 
            
            engine.say(message) # Say only the price
            engine.runAndWait()
        except Exception as e:
            print(f"Error playing audio: {e}")
    else:
        print(f"Failed to retrieve price for {ticker.upper()}.")

def get_validated_input(prompt_message, validation_func):
    while True:
        user_input = input(prompt_message).strip()
        try:
            result = validation_func(user_input)
            if result is not None:
                return result
        except Exception as e:
            print(f"An unexpected error occurred during input validation: {e}")

def stock_price_reader():
    def validate_interval(input_str):
        if not input_str.isdigit():
            print("Invalid input. Please enter a positive integer for seconds.")
            return None
        interval = int(input_str)
        if interval <= 0:
            print("Interval must be a positive integer. Please try again.")
            return None
        return interval

    def validate_ticker(input_str):
        if not input_str:
            print("Stock ticker cannot be empty. Please try again.")
            return None
        print(f"Checking if '{input_str.upper()}' is a valid stock ticker...")
        if not check_stock_exists(input_str):
            print(f"Stock ticker '{input_str.upper()}' does not appear to exist on Yahoo Finance. Please try again.")
            return None
        return input_str

    update_interval = get_validated_input("Enter the interval in seconds: ", validate_interval)
    stock_ticker = get_validated_input("Enter the stock ticker symbol (e.g., AAPL, GOOGL): ", validate_ticker)

    print(f"\nStarting stock price updates for {stock_ticker.upper()} every {update_interval} seconds.")
    print("Press Ctrl+C to stop.")

    try:
        while True:
            price = get_stock_price(stock_ticker)
            read_stock_price(ticker=stock_ticker, price=price)
            time.sleep(update_interval)
    except KeyboardInterrupt:
        print("\nStock price reader stopped.")
    except Exception as e:
        print(f"An error occurred during execution: {e}")

if __name__ == "__main__":
    stock_price_reader()
