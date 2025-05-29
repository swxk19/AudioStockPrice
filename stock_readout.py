import time
import requests
from bs4 import BeautifulSoup
import pyttsx3
import tkinter as tk
from tkinter import ttk
import threading
import webbrowser
import queue # Import the queue module

# Global flag to control the stock update loop
running = False

# Global queue for text-to-speech requests
_tts_queue = queue.Queue()
_tts_engine = None # Will be initialized in the worker thread
_tts_engine_ready_event = threading.Event() # Event to signal when TTS engine is ready

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
        price_element_2 = soup.find('fin-streamer', {'data-field': 'regularMarketPrice'})

        return (response.status_code == 200) and (price_element_1 is not None or price_element_2 is not None)
    except requests.exceptions.RequestException:
        return False

def read_stock_price(text_to_speak, selected_voice_id):
    _tts_queue.put((text_to_speak, selected_voice_id))

def _tts_worker():
    global _tts_engine
    try:
        _tts_engine = pyttsx3.init()
        initial_rate = _tts_engine.getProperty('rate')
        _tts_engine.setProperty('rate', initial_rate * 0.95)
        _tts_engine_ready_event.set() # Signal that engine is ready

        while True:
            text, voice_id = _tts_queue.get()
            if text is None: # Sentinel value to stop the thread
                break
            
            try:
                if voice_id:
                    _tts_engine.setProperty('voice', voice_id)
                _tts_engine.say(text)
                _tts_engine.runAndWait()
            except Exception as e:
                print(f"Error in TTS worker while speaking: {e}")
    except Exception as e:
        print(f"Error initializing TTS engine in worker: {e}")
    finally:
        if _tts_engine:
            _tts_engine.stop()
            _tts_engine.endLoop()

def stock_update_loop(ticker_entry, interval_entry, price_label, selected_voice_id):
    global running
    last_valid_interval = 5
    last_valid_ticker = ticker_entry.get().strip()

    while running:
        current_interval = last_valid_interval
        current_ticker = last_valid_ticker
        
        price_label.config(style="TLabel") 

        try:
            entered_interval_str = interval_entry.get().strip()
            if entered_interval_str.isdigit() and int(entered_interval_str) > 0:
                current_interval = int(entered_interval_str)
                last_valid_interval = current_interval
            else:
                price_label.config(text=f"Error: Invalid interval '{entered_interval_str}'. Using {last_valid_interval}s.", style="Error.TLabel")
                time.sleep(1)
                continue
        except ValueError:
            price_label.config(text=f"Error: Non-numeric interval. Using {last_valid_interval}s.", style="Error.TLabel")
            time.sleep(1)
            continue
        except Exception as e:
            price_label.config(text=f"Error getting interval: {e}. Using {last_valid_interval}s.", style="Error.TLabel")
            time.sleep(1)
            continue

        try:
            entered_ticker = ticker_entry.get().strip()
            if not entered_ticker:
                price_label.config(text=f"Error: Stock ticker cannot be empty.", style="Error.TLabel")
                time.sleep(1)
                continue
            elif not check_stock_exists(entered_ticker):
                price_label.config(text=f"Error: '{entered_ticker.upper()}' doesn't exist.", style="Error.TLabel")
                time.sleep(1)
                continue
            else:
                current_ticker = entered_ticker
                last_valid_ticker = current_ticker
        except Exception as e:
            price_label.config(text=f"Error getting ticker: {e}. Using {last_valid_ticker.upper()}.", style="Error.TLabel")
            time.sleep(1)
            continue

        price = get_stock_price(current_ticker)
        if price is not None:
            price_str = f"${price:.2f}"
            full_text_to_speak = price_str
            price_label.config(text=f"{current_ticker.upper()}\nCurrent Price: {price_str}", style="TLabel")
            read_stock_price(full_text_to_speak, selected_voice_id)
        else:
            price_label.config(text=f"Failed to retrieve price for {current_ticker.upper()}.", style="Error.TLabel")
        
        time.sleep(current_interval)

def start_stop_reading(ticker_entry, interval_entry, price_label, start_button, voice_combobox):
    global running

    if running:
        running = False
        start_button.config(text="Start Reading")
        price_label.config(text="Stock Price: --.--", style="TLabel")
    else:
        ticker = ticker_entry.get().strip()
        interval_str = interval_entry.get().strip()
        selected_voice_name = voice_combobox.get()
        selected_voice_id = None

        if not ticker:
            price_label.config(text="Error: Stock ticker cannot be empty.", style="Error.TLabel")
            return
        
        if not interval_str.isdigit() or int(interval_str) <= 0:
            price_label.config(text="Error: Interval must be a positive integer.", style="Error.TLabel")
            return

        if not check_stock_exists(ticker):
            price_label.config(text=f"Error: '{ticker.upper()}' does not exist.", style="Error.TLabel")
            return
        else:
            price_label.config(text=f"{ticker.upper()}\nChecking price...", style="TLabel")


        if _tts_engine: # Check if the engine was successfully initialized
            voices = _tts_engine.getProperty('voices')
            for voice in voices:
                if voice.name == selected_voice_name:
                    selected_voice_id = voice.id
                    break
        else:
            price_label.config(text="Error: TTS engine not initialized.", style="Error.TLabel")
            return

        running = True
        start_button.config(text="Stop Reading")
        
        thread = threading.Thread(target=stock_update_loop, args=(ticker_entry, interval_entry, price_label, selected_voice_id))
        thread.daemon = True
        thread.start()

def _perform_apply_changes_validation(ticker_entry, interval_entry, price_label):
    """Actual validation logic for Apply Changes button, called after a short delay."""
    ticker = ticker_entry.get().strip()
    interval_str = interval_entry.get().strip()

    if not ticker:
        price_label.config(text="Error: Stock ticker cannot be empty.", style="Error.TLabel")
        return
    
    if not interval_str.isdigit() or int(interval_str) <= 0:
        price_label.config(text="Error: Interval must be a positive integer.", style="Error.TLabel")
        return

    if not check_stock_exists(ticker):
        price_label.config(text=f"Error: '{ticker.upper()}' does not exist.", style="Error.TLabel")
        return

def apply_changes_to_display(ticker_entry, interval_entry, price_label, root_instance):
    """Schedules the validation for Apply Changes button after a short delay."""
    price_label.config(text="Processing changes...", style="TLabel") # Immediate feedback
    # Schedule the actual validation after 100ms
    root_instance.after(100, lambda: _perform_apply_changes_validation(ticker_entry, interval_entry, price_label))

def open_voice_download_link():
    webbrowser.open("https://support.microsoft.com/en-us/topic/download-languages-and-voices-for-immersive-reader-read-mode-and-read-aloud-4c83a8d8-7486-42f7-8e46-2b0fdf753130")

def main_app():
    root = tk.Tk()
    root.title("Stock Price Reader")
    root.geometry("400x300")
    root.resizable(False, False)

    # Start the TTS worker thread immediately
    tts_worker_thread = threading.Thread(target=_tts_worker, daemon=True)
    tts_worker_thread.start()

    def on_closing():
        global running
        running = False
        _tts_queue.put((None, None)) # Send sentinel to stop the TTS worker thread
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)

    style = ttk.Style()
    style.configure('TFrame', background='#f0f0f0')
    style.configure('TLabel', background='#f0f0f0', font=('Arial', 10), foreground='black')
    style.configure('Error.TLabel', background='#f0f0f0', font=('Arial', 10), foreground='red')

    style.configure('TButton', font=('Arial', 10, 'bold'))
    style.configure('TEntry', font=('Arial', 10))
    style.configure('TCombobox', font=('Arial', 10))

    main_frame = ttk.Frame(root, padding="20")
    main_frame.pack(fill=tk.BOTH, expand=True)

    ttk.Label(main_frame, text="Update Interval (seconds):").grid(row=0, column=0, padx=5, pady=5, sticky="w")
    interval_entry = ttk.Entry(main_frame, width=10)
    interval_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
    interval_entry.insert(0, "5")

    ttk.Label(main_frame, text="Stock Ticker Symbol:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
    ticker_entry = ttk.Entry(main_frame, width=15)
    ticker_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
    ticker_entry.insert(0, "AAPL")

    ttk.Label(main_frame, text="Select Voice:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
    voice_names = []
    # Wait for the TTS engine to be ready before populating voices
    _tts_engine_ready_event.wait(timeout=5) # Wait up to 5 seconds for the engine to init

    if _tts_engine_ready_event.is_set() and _tts_engine:
        try:
            voices = _tts_engine.getProperty('voices')
            for voice in voices:
                voice_names.append(voice.name)
        except Exception as e:
            print(f"Could not load voices from initialized engine: {e}")
            voice_names = ["Default Voice (Error)"]
    else:
        voice_names = ["TTS Not Available (Init Failed)"]

    voice_names.append("Download More Voices...")

    voice_combobox = ttk.Combobox(main_frame, values=voice_names, state="readonly")
    voice_combobox.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
    
    if voice_names and voice_names[0] != "TTS Engine Init Error" and voice_names[0] != "TTS Not Available":
        voice_combobox.set(voice_names[0])
    else:
        voice_combobox.set("Download More Voices...")

    def handle_voice_selection(event):
        selected_option = voice_combobox.get()
        if selected_option == "Download More Voices...":
            open_voice_download_link()
            if voice_names and voice_names[0] != "TTS Engine Init Error" and voice_names[0] != "TTS Not Available":
                voice_combobox.set(voice_names[0])
            else:
                voice_combobox.set("Download More Voices...")

    voice_combobox.bind("<<ComboboxSelected>>", handle_voice_selection)

    price_label = ttk.Label(main_frame, text="Stock Price: --.--", font=('Arial', 14, 'bold'))
    price_label.grid(row=3, column=0, columnspan=2, padx=5, pady=15)

    start_button = ttk.Button(main_frame, text="Start Reading", 
                              command=lambda: start_stop_reading(ticker_entry, interval_entry, price_label, start_button, voice_combobox))
    start_button.grid(row=4, column=0, columnspan=2, padx=5, pady=10, sticky="ew")

    apply_button = ttk.Button(main_frame, text="Apply Changes",
                              command=lambda: apply_changes_to_display(ticker_entry, interval_entry, price_label, root))
    apply_button.grid(row=5, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

    root.mainloop()

if __name__ == "__main__":
    main_app()
