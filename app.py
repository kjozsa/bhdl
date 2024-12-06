from flask import Flask, render_template, request, flash, redirect, url_for
from bithumen_downloader import BitHumenDownloader
import os
from dotenv import load_dotenv

app = Flask(__name__)
app.secret_key = os.urandom(24)  # for flash messages

# Initialize the downloader
downloader = None

def init_downloader():
    global downloader
    if downloader is None:
        downloader = BitHumenDownloader()
        if not downloader.login():
            raise Exception("Failed to login to BitHumen")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    try:
        if downloader is None:
            init_downloader()
            
        query = request.form.get('query')
        if not query:
            return render_template('index.html', error="Please enter a search term")
            
        results = downloader.search(query)
        return render_template('index.html', results=results)
        
    except Exception as e:
        return render_template('index.html', error=f"Search error: {str(e)}")

@app.route('/download', methods=['POST'])
def download():
    try:
        if downloader is None:
            init_downloader()
            
        details_url = request.form.get('details_url')
        if not details_url:
            return render_template('index.html', error="No torrent selected")
            
        if downloader.download_torrent(details_url):
            message = "Torrent download started successfully"
        else:
            message = "Failed to download torrent"
            
        return render_template('index.html', message=message)
        
    except Exception as e:
        return render_template('index.html', error=f"Download error: {str(e)}")

if __name__ == '__main__':
    # Load environment variables
    load_dotenv()
    
    # Get host and port from environment or use defaults
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', '5000'))
    
    # Initialize downloader
    try:
        init_downloader()
        print("Successfully logged in to BitHumen")
    except Exception as e:
        print(f"Error initializing downloader: {str(e)}")
        exit(1)
    
    # Run the Flask app
    app.run(host=host, port=port)
