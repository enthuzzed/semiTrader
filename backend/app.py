from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, timedelta, UTC
import requests
import re
import os
from dotenv import load_dotenv
from collections import Counter
import time
import random
import logging
import yfinance as yf

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Allow all origins by default

# Configure the database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///trader.db'  # SQLite for simplicity
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Twitter API Configuration
TWITTER_API_BASE = 'https://api.twitter.com/2'
BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')
HEADERS = {
    'Authorization': f'Bearer {BEARER_TOKEN}',
    'Content-Type': 'application/json'
}

print("Twitter API Configuration:")
print(f"Bearer token exists: {bool(BEARER_TOKEN)}")
print(f"Bearer token prefix: {BEARER_TOKEN[:20]}..." if BEARER_TOKEN else "No token found")

# Cache configuration
CACHE_DURATION = 3600 * 4  # Cache for 4 hours instead of 1
last_twitter_fetch = 0
RATE_LIMIT_TWEETS = 25  # Reduced from 50 to 25 tweets per user
MAX_USERS_PER_FETCH = 3  # Reduced from 5 to 3 users per update to stay within rate limits

# Database Models
class StockPick(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(10), nullable=False)
    source = db.Column(db.String(10), nullable=False)  # AI or Manual
    date = db.Column(db.Date, default=datetime.utcnow)
    mention_count = db.Column(db.Integer, default=1)
    twitter_users = db.Column(db.String(500))  # Comma-separated list of users who mentioned the stock
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    position_type = db.Column(db.String(10))  # long or short, only for manual picks

class Position(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(10), nullable=False)
    entry_price = db.Column(db.Float, nullable=False)
    exit_price = db.Column(db.Float, nullable=True)  # Null if not exited
    status = db.Column(db.String(10), nullable=False)  # long, short, or closed
    performance = db.Column(db.Float, nullable=True)  # Percentage gain/loss
    
class TradeHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(10), nullable=False)
    entry_price = db.Column(db.Float, nullable=False)
    exit_price = db.Column(db.Float, nullable=False)
    performance = db.Column(db.Float, nullable=False)
    date_closed = db.Column(db.Date, default=datetime.utcnow)

def init_db():
    with app.app_context():
        # Drop all tables
        db.drop_all()
        # Create all tables
        db.create_all()
        print("Database initialized!")

# Initialize the database
init_db()

def should_fetch_twitter():
    global last_twitter_fetch
    current_time = time.time()
    if current_time - last_twitter_fetch >= CACHE_DURATION:
        last_twitter_fetch = current_time
        return True
    return False

def get_user_id(username, retries=3):
    print(f"\nAPI Request Details for {username}:")
    print(f"URL: {TWITTER_API_BASE}/users/by/username/{username}")
    print(f"Headers: {HEADERS}")
    
    for attempt in range(retries):
        try:
            print(f"Attempting to get user ID for {username} (attempt {attempt + 1}/{retries})")
            response = requests.get(
                f'{TWITTER_API_BASE}/users/by/username/{username}',
                headers=HEADERS
            )
            
            remaining = response.headers.get('x-rate-limit-remaining', '0')
            reset_time = response.headers.get('x-rate-limit-reset', '0')
            print(f"Rate limit remaining: {remaining}, Reset time: {reset_time}")
            
            if response.status_code == 200:
                user_data = response.json()
                if 'data' in user_data:
                    print(f"Successfully found user ID for {username}")
                    return user_data['data']['id']
                else:
                    print(f"No user data found for {username}")
                    return None
            elif response.status_code == 429:
                reset_time = int(response.headers.get('x-rate-limit-reset', 900))
                current_time = int(time.time())
                wait_time = max(reset_time - current_time, 60)
                print(f"Rate limited, waiting {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print(f"Error getting user ID for {username}: {response.status_code}")
                print(f"Response: {response.text}")
                if attempt < retries - 1:
                    sleep_time = 2 ** attempt
                    print(f"Retrying in {sleep_time} seconds...")
                    time.sleep(sleep_time)
        except Exception as e:
            print(f"Exception getting user ID for {username}: {str(e)}")
            if attempt < retries - 1:
                sleep_time = 2 ** attempt
                print(f"Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
            else:
                return None
    return None

def get_user_tweets(user_id, retries=3):
    yesterday = (datetime.now(UTC) - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
    params = {
        'max_results': RATE_LIMIT_TWEETS,
        'start_time': yesterday,
        'tweet.fields': 'created_at,text'
    }
    
    for attempt in range(retries):
        try:
            logger.info(f"Attempting to get tweets (attempt {attempt + 1}/{retries})")
            response = requests.get(
                f'{TWITTER_API_BASE}/users/{user_id}/tweets',
                headers=HEADERS,
                params=params
            )
            
            remaining = response.headers.get('x-rate-limit-remaining', '0')
            reset_time = response.headers.get('x-rate-limit-reset', '0')
            print(f"Rate limit remaining: {remaining}, Reset time: {reset_time}")
            
            if response.status_code == 200:
                data = response.json().get('data', [])
                print(f"Found {len(data)} tweets")
                return data
            elif response.status_code == 429:
                reset_time = int(response.headers.get('x-rate-limit-reset', 900))
                current_time = int(time.time())
                wait_time = max(reset_time - current_time, 60)
                print(f"Rate limited, waiting {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print(f"Error getting tweets: {response.status_code}")
                print(f"Response: {response.text}")
                if attempt < retries - 1:
                    sleep_time = 2 ** attempt
                    print(f"Retrying in {sleep_time} seconds...")
                    time.sleep(sleep_time)
        except Exception as e:
            print(f"Exception getting tweets: {str(e)}")
            if attempt < retries - 1:
                sleep_time = 2 ** attempt
                print(f"Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
            else:
                return []
    return []

def extract_stock_symbols(text):
    # Match stock symbols that start with $ and are followed by 1-5 capital letters
    pattern = r'\$([A-Z]{1,5})'
    matches = re.findall(pattern, text)
    return matches

def fetch_twitter_stocks():
    if not should_fetch_twitter():
        logger.info("Using cached data (less than 4 hours old)")
        return
        
    logger.info("Fetching fresh Twitter data...")
    followed_accounts = os.getenv('TWITTER_FOLLOWED_ACCOUNTS', '').split(',')
    followed_accounts = [acc.strip() for acc in followed_accounts if acc.strip()]
    print(f"Checking accounts: {followed_accounts}")
    
    if not followed_accounts:
        print("No accounts configured in TWITTER_FOLLOWED_ACCOUNTS")
        return
        
    # Limit the number of accounts to fetch from
    followed_accounts = followed_accounts[:MAX_USERS_PER_FETCH]
    
    stock_mentions = Counter()
    user_mentions = {}
    
    for username in followed_accounts:
        try:
            print(f"\nProcessing tweets from @{username}")
            user_id = get_user_id(username)
            if not user_id:
                print(f"Could not find user ID for {username}")
                continue
                
            tweets = get_user_tweets(user_id)
            for tweet in tweets:
                stocks = extract_stock_symbols(tweet['text'])
                if stocks:
                    print(f"Found stocks in tweet: {stocks}")
                    print(f"Tweet text: {tweet['text']}")
                for stock in stocks:
                    stock_mentions[stock] += 1
                    if stock not in user_mentions:
                        user_mentions[stock] = set()
                    user_mentions[stock].add(username)
                    
        except Exception as e:
            print(f"Error fetching tweets for {username}: {str(e)}")
            continue
    
    if not stock_mentions:
        print("No stock mentions found in the last 24 hours")
        return
        
    print("\nStock mentions found:", dict(stock_mentions))
    
    # Update database with new mentions
    update_time = datetime.now(UTC)
    
    for stock, count in stock_mentions.items():
        users = ','.join(user_mentions[stock])
        existing = StockPick.query.filter_by(
            ticker=stock,
            source='AI',
            date=update_time.date()
        ).first()
        
        if existing:
            existing.mention_count += count
            existing.twitter_users = users
            existing.last_updated = update_time
        else:
            new_pick = StockPick(
                ticker=stock,
                source='AI',
                mention_count=count,
                twitter_users=users,
                last_updated=update_time
            )
            db.session.add(new_pick)
    
    db.session.commit()
    print("Database updated successfully")

def get_stock_data(tickers):
    stock_data = {}
    try:
        # Process tickers in smaller batches
        batch_size = 2
        for i in range(0, len(tickers), batch_size):
            batch = tickers[i:i + batch_size]
            
            for ticker in batch:
                retries = 3
                delay = 2
                success = False
                
                for attempt in range(retries):
                    try:
                        # Create ticker without custom session, let yfinance handle it
                        stock = yf.Ticker(ticker)
                        
                        # First try to get fast_info data (most reliable and efficient)
                        try:
                            fast_info = stock.fast_info
                            current_price = fast_info['lastPrice']
                            last_close = fast_info['previousClose']
                            price_change = ((current_price - last_close) / last_close) * 100
                            
                            stock_data[ticker] = {
                                'current_price': current_price,
                                'daily_change': price_change,
                                'last_close': last_close
                            }
                            success = True
                            break
                            
                        except Exception as e:
                            logger.warning(f"Fast info failed for {ticker}, trying history: {str(e)}")
                            # If fast_info fails, try historical data
                            hist = stock.history(period='2d', interval='1d', prepost=False)
                            if len(hist) >= 1:
                                current_or_last = float(hist['Close'].iloc[-1])
                                price_change = 0
                                
                                if len(hist) >= 2:
                                    yesterday_close = float(hist['Close'].iloc[-2])
                                    price_change = ((current_or_last - yesterday_close) / yesterday_close) * 100
                                
                                stock_data[ticker] = {
                                    'current_price': current_or_last,
                                    'daily_change': price_change,
                                    'last_close': current_or_last
                                }
                                success = True
                                break
                            
                    except Exception as e:
                        error_msg = str(e).lower()
                        logger.error(f"Error fetching data for {ticker} (attempt {attempt + 1}): {str(e)}")
                        
                        if any(x in error_msg for x in ['too many requests', '429', 'rate limit']):
                            sleep_time = delay * (2 ** attempt)
                            logger.info(f"Rate limited, waiting {sleep_time} seconds...")
                            time.sleep(sleep_time)
                        elif any(x in error_msg for x in ['not found', 'delisted', 'no data']):
                            logger.warning(f"Invalid symbol {ticker}")
                            break
                        else:
                            time.sleep(2)
                
                if not success:
                    logger.error(f"Failed to fetch data for {ticker} after {retries} attempts")
                    stock_data[ticker] = {
                        'current_price': None,
                        'daily_change': None,
                        'last_close': None
                    }
            
            # Add delay between batches to avoid rate limits
            time.sleep(2)
            
    except Exception as e:
        logger.error(f"Global error in get_stock_data: {str(e)}")
            
    return stock_data

# Root Route
@app.route('/')
def home():
    return "Server is running!"

# API Routes
@app.route('/picks', methods=['GET', 'POST'])
def handle_picks():
    if request.method == 'GET':
        # Only fetch new Twitter data if cache has expired
        fetch_twitter_stocks()
        
        # Get all picks
        picks = StockPick.query.all()
        
        # Get unique tickers from picks
        tickers = list(set(p.ticker for p in picks))
        
        # Fetch stock data for all picks
        stock_data = get_stock_data(tickers)
        
        return jsonify([{
            'id': p.id,
            'ticker': p.ticker,
            'source': p.source,
            'date': p.date.strftime('%Y-%m-%d'),
            'mention_count': p.mention_count,
            'twitter_users': p.twitter_users.split(',') if p.twitter_users else [],
            'last_updated': p.last_updated.isoformat() if p.last_updated else None,
            'position_type': p.position_type,
            'current_price': stock_data.get(p.ticker, {}).get('current_price'),
            'daily_change': stock_data.get(p.ticker, {}).get('daily_change')
        } for p in picks])
    
    if request.method == 'POST':
        data = request.json
        new_pick = StockPick(
            ticker=data['ticker'],
            source=data['source'],
            mention_count=data.get('mention_count', 1),
            twitter_users=','.join(data.get('twitter_users', []) if isinstance(data.get('twitter_users'), list) else [data.get('twitter_users')] if data.get('twitter_users') else []),
            last_updated=datetime.utcnow(),
            position_type=data.get('position_type') if data['source'] == 'Manual' else None
        )
        db.session.add(new_pick)
        db.session.commit()
        return jsonify({'message': 'Stock pick added successfully!'}), 201

@app.route('/picks/<int:pick_id>', methods=['PUT', 'DELETE'])
def handle_pick(pick_id):
    pick = StockPick.query.get_or_404(pick_id)
    
    if request.method == 'PUT':
        data = request.json
        pick.ticker = data['ticker']
        db.session.commit()
        return jsonify({'message': 'Stock pick updated successfully!'})
        
    if request.method == 'DELETE':
        db.session.delete(pick)
        db.session.commit()
        return jsonify({'message': 'Stock pick deleted successfully!'})

@app.route('/positions', methods=['GET', 'POST'])
def handle_positions():
    if request.method == 'GET':
        positions = Position.query.all()
        
        # Get unique tickers from positions
        tickers = list(set(p.ticker for p in positions))
        
        # Fetch stock data
        stock_data = get_stock_data(tickers)
        
        return jsonify([{
            'id': p.id,
            'ticker': p.ticker,
            'entry_price': p.entry_price,
            'exit_price': p.exit_price,
            'current_price': stock_data.get(p.ticker, {}).get('current_price'),
            'daily_change': stock_data.get(p.ticker, {}).get('daily_change'),
            'status': p.status,
            'performance': p.performance
        } for p in positions])

    if request.method == 'POST':
        data = request.json
        entry_price = float(data['entry_price'])
        exit_price = float(data.get('exit_price', 0)) if data.get('exit_price') else None
        
        # Calculate performance if we have both prices
        performance = None
        if exit_price and entry_price:
            if data['status'] == 'long':
                performance = ((exit_price - entry_price) / entry_price) * 100
            else:  # short position
                performance = ((entry_price - exit_price) / entry_price) * 100
        
        # If we have an exit price, create a trade history entry
        if exit_price:
            trade_history = TradeHistory(
                ticker=data['ticker'],
                entry_price=entry_price,
                exit_price=exit_price,
                performance=performance,
                date_closed=datetime.now(UTC).date()
            )
            db.session.add(trade_history)
            
            # Return success without creating a position
            db.session.commit()
            return jsonify({'message': 'Trade history added successfully!'}), 201
        
        # If no exit price, create a new position
        new_position = Position(
            ticker=data['ticker'],
            entry_price=entry_price,
            exit_price=exit_price,
            status=data['status'],
            performance=performance
        )
        db.session.add(new_position)
        db.session.commit()
        return jsonify({'message': 'Position added successfully!'}), 201

@app.route('/positions/<int:position_id>', methods=['PUT'])
def update_position(position_id):
    position = Position.query.get_or_404(position_id)
    data = request.json
    
    if 'exit_price' in data:
        exit_price = float(data['exit_price'])
        # Calculate performance
        if position.status == 'long':
            performance = ((exit_price - position.entry_price) / position.entry_price) * 100
        else:  # short position
            performance = ((position.entry_price - exit_price) / position.entry_price) * 100
            
        # Create trade history entry
        trade_history = TradeHistory(
            ticker=position.ticker,
            entry_price=position.entry_price,
            exit_price=exit_price,
            performance=performance,
            date_closed=datetime.now(UTC).date()
        )
        db.session.add(trade_history)
        
        # Delete the position
        db.session.delete(position)
        db.session.commit()
        
        return jsonify({'message': 'Position closed and moved to trade history!'})

@app.route('/positions/<int:position_id>', methods=['DELETE'])
def delete_position(position_id):
    position = Position.query.get_or_404(position_id)
    db.session.delete(position)
    db.session.commit()
    return jsonify({'message': 'Position deleted successfully!'})

@app.route('/trades', methods=['GET'])
def get_trades():
    trades = TradeHistory.query.all()
    return jsonify([{
        'id': t.id,
        'ticker': t.ticker,
        'entry_price': t.entry_price,
        'exit_price': t.exit_price,
        'performance': t.performance,
        'date_closed': t.date_closed.strftime('%Y-%m-%d')
    } for t in trades])

@app.route('/continue-iteration', methods=['POST'])
def continue_iteration():
    try:
        # For now, just fetch new Twitter data and update picks
        fetch_twitter_stocks()
        return jsonify({"message": "Iteration started successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/sectors')
def get_sectors():
    tickers = request.args.get('tickers', '').split(',')
    if not tickers or not tickers[0]:
        return jsonify({}), 400
        
    stock_data = get_stock_data(tickers)
    return jsonify(stock_data)

if __name__ == '__main__':
    app.run(debug=True, port=5001)
