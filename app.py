from flask import Flask, render_template, request, flash, redirect, url_for, jsonify
from bithumen_downloader import BitHumenDownloader
import os
from dotenv import load_dotenv
from loguru import logger
import sys

# Configure loguru
logger.remove()  # Remove default handler
logger.add(sys.stderr, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
logger.add("bhdl.log", rotation="10 MB", retention="7 days", format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}")

app = Flask(__name__)
app.secret_key = os.urandom(24)  # for flash messages

# Initialize the downloader
downloader = None

def init_downloader():
    global downloader
    if downloader is None:
        logger.info("Initializing BitHumen downloader")
        downloader = BitHumenDownloader()
        if not downloader.login():
            logger.error("Failed to login to BitHumen")
            raise Exception("Failed to login to BitHumen")
        logger.success("Successfully logged in to BitHumen")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    try:
        if downloader is None:
            init_downloader()
            
        query = request.form.get('query', '')
        if not query:
            logger.warning("Empty search query received")
            return render_template('index.html', error="Please enter a search term", query=query)
            
        logger.info(f"Searching for: {query}")
        results = downloader.search(query)
        logger.success(f"Found {len(results)} results for query: {query}")
        return render_template('index.html', results=results, query=query)
        
    except Exception as e:
        logger.exception(f"Search error occurred: {str(e)}")
        return render_template('index.html', error=f"Search error: {str(e)}", query=query)

@app.route('/download', methods=['POST'])
def download():
    try:
        if downloader is None:
            init_downloader()
            
        details_url = request.form.get('details_url')
        if not details_url:
            logger.warning("No torrent URL provided for download")
            return jsonify({'status': 'error', 'message': 'No torrent selected'})
            
        logger.info(f"Attempting to download torrent from: {details_url}")
        success, error_msg = downloader.download_torrent(details_url)
        
        if success:
            logger.success("Torrent download completed successfully")
            return jsonify({'status': 'success', 'message': 'Torrent download started successfully'})
        else:
            logger.error(f"Failed to download torrent: {error_msg}")
            return jsonify({'status': 'error', 'message': f'Failed to download torrent: {error_msg}'})
        
    except Exception as e:
        logger.exception(f"Download error occurred: {str(e)}")
        return jsonify({'status': 'error', 'message': f'Download error: {str(e)}'})

@app.route('/reboot', methods=['POST'])
def reboot():
    try:
        logger.info("Reboot request received")
        os.system('sudo systemctl reboot')
        return jsonify({'status': 'success', 'message': 'Reboot initiated'})
    except Exception as e:
        logger.exception(f"Reboot error occurred: {str(e)}")
        return jsonify({'status': 'error', 'message': f'Reboot error: {str(e)}'})

if __name__ == '__main__':
    # Load environment variables
    load_dotenv()
    
    # Get Flask configuration from environment
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    
    logger.info(f"Starting Flask server on {host}:{port}")
    app.run(host=host, port=port)
