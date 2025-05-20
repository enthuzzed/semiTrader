from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, timedelta
import tweepy
import re
import os
from dotenv import load_dotenv
from collections import Counter

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Allow all origins by default

# Configure the database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///trader.db'  # SQLite for simplicity
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Twitter API Setup
twitter_client = tweepy.Client(
    bearer_token=os.getenv('TWITTER_BEARER_TOKEN'),
    consumer_key=os.getenv('TWITTER_API_KEY'),
    consumer_secret=os.getenv('TWITTER_API_SECRET'),
    access_token=os.getenv('TWITTER_ACCESS_TOKEN'),
    access_token_secret=os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
)

# Database Models
class StockPick(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(10), nullable=False)
    source = db.Column(db.String(10), nullable=False)  # AI or Manual
    date = db.Column(db.Date, default=datetime.utcnow)
    mention_count = db.Column(db.Integer, default=1)
    twitter_users = db.Column(db.String(500))  # Comma-separated list of users who mentioned the stock

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

def extract_stock_symbols(text):
    # Match stock symbols that start with $ and are followed by 1-5 capital letters
    pattern = r'\$([A-Z]{1,5})'
    matches = re.findall(pattern, text)
    return matches

def fetch_twitter_stocks():
    followed_accounts = os.getenv('TWITTER_FOLLOWED_ACCOUNTS', '').split(',')
    stock_mentions = Counter()
    user_mentions = {}
    
    for username in followed_accounts:
        try:
            # Get user ID
            user = twitter_client.get_user(username=username)
            if not user:
                continue
                
            # Get recent tweets from user
            tweets = twitter_client.get_users_tweets(
                id=user.data.id,
                max_results=100,
                start_time=datetime.utcnow() - timedelta(days=1)
            )
            
            if not tweets.data:
                continue
                
            for tweet in tweets.data:
                stocks = extract_stock_symbols(tweet.text)
                for stock in stocks:
                    stock_mentions[stock] += 1
                    if stock not in user_mentions:
                        user_mentions[stock] = set()
                    user_mentions[stock].add(username)
                    
        except Exception as e:
            print(f"Error fetching tweets for {username}: {str(e)}")
            continue
    
    # Update database with new mentions
    for stock, count in stock_mentions.items():
        users = ','.join(user_mentions[stock])
        existing = StockPick.query.filter_by(
            ticker=stock,
            source='AI',
            date=datetime.utcnow().date()
        ).first()
        
        if existing:
            existing.mention_count += count
            existing.twitter_users = users
        else:
            new_pick = StockPick(
                ticker=stock,
                source='AI',
                mention_count=count,
                twitter_users=users
            )
            db.session.add(new_pick)
    
    db.session.commit()

# Initialize the database
with app.app_context():
    db.create_all()

# Root Route
@app.route('/')
def home():
    return "Server is running!"

# API Routes
@app.route('/picks', methods=['GET', 'POST'])
def handle_picks():
    if request.method == 'GET':
        # Fetch new Twitter data
        fetch_twitter_stocks()
        
        # Get all picks, sorted by mention count for AI picks
        picks = StockPick.query.all()
        return jsonify([{
            'id': p.id,
            'ticker': p.ticker,
            'source': p.source,
            'date': p.date.strftime('%Y-%m-%d'),
            'mention_count': p.mention_count,
            'twitter_users': p.twitter_users.split(',') if p.twitter_users else []
        } for p in picks])
    
    if request.method == 'POST':
        data = request.json
        new_pick = StockPick(
            ticker=data['ticker'],
            source=data['source']
        )
        db.session.add(new_pick)
        db.session.commit()
        return jsonify({'message': 'Stock pick added successfully!'}), 201

@app.route('/positions', methods=['GET', 'POST'])
def handle_positions():
    if request.method == 'GET':
        positions = Position.query.all()
        return jsonify([{
            'id': p.id,
            'ticker': p.ticker,
            'entry_price': p.entry_price,
            'exit_price': p.exit_price,
            'status': p.status,
            'performance': p.performance
        } for p in positions])

    if request.method == 'POST':
        data = request.json
        new_position = Position(
            ticker=data['ticker'],
            entry_price=data['entry_price'],
            exit_price=data.get('exit_price'),
            status=data['status'],
            performance=data.get('performance')
        )
        db.session.add(new_position)
        db.session.commit()
        return jsonify({'message': 'Position added successfully!'}), 201

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

if __name__ == '__main__':
    app.run(debug=True)
