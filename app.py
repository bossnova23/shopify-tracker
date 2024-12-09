from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
import os
from dotenv import load_dotenv
import requests
from datetime import datetime
import urllib.parse
import logging
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__, static_folder='static')

# Database configuration
if os.environ.get('RENDER'):
    # Use PostgreSQL in production
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        # Render adds postgres:// instead of postgresql://
        database_url = database_url.replace('postgres://', 'postgresql://')
    else:
        # Fallback to SQLite if no DATABASE_URL is set
        database_url = 'sqlite:///shopify_tracker.db'
    
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 5,
        'pool_timeout': 30,
        'pool_recycle': 1800,
        'pool_pre_ping': True,
        'connect_args': {
            'sslmode': 'require',
            'connect_timeout': 10
        }
    }
else:
    # Use SQLite in development
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shopify_tracker.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy after all configurations
db = SQLAlchemy(app)

# Add error handling for database operations
def handle_db_operation(operation):
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            return operation()
        except Exception as e:
            retry_count += 1
            logger.error(f"Database operation failed (attempt {retry_count}/{max_retries}): {str(e)}")
            if retry_count == max_retries:
                raise
            db.session.rollback()
    
# Models
class Store(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    domain = db.Column(db.String(120), unique=True, nullable=False)
    track_start = db.Column(db.String(10), nullable=False)
    total_sales = db.Column(db.Float, default=0.0)
    week_sales = db.Column(db.Float, default=0.0)
    products = db.relationship('Product', backref='store', lazy=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('store.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    handle = db.Column(db.String(200), nullable=False)
    bought = db.Column(db.String(50), nullable=False)
    post = db.Column(db.String(50), nullable=False)
    image = db.Column(db.String(500), nullable=False)
    price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, default=0.0)
    total_sales = db.Column(db.Integer, default=0)
    track_start = db.Column(db.String(10), nullable=False)

    __table_args__ = (db.UniqueConstraint('store_id', 'handle', name='unique_store_product'),)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    logger.debug('Rendering index.html')
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f'Error rendering index.html: {str(e)}')
        return str(e), 500

@app.route('/api/track-product', methods=['POST'])
def track_product():
    logger.debug('Tracking product')
    try:
        product_link = request.json.get('product_link')
        
        # Extract handle and domain
        handle_id = product_link.split("/products/")[1].split('?')[0]
        domain = product_link.split("/")[2]
        
        # Get product data from Shopify
        url = f"https://{domain}/products/{handle_id}/products.json"
        response = requests.get(url, timeout=10)
        data_json = response.json()
        
        def db_operation():
            # Get or create store
            store = Store.query.filter_by(domain=domain).first()
            if not store:
                store = Store(
                    domain=domain,
                    track_start=datetime.today().strftime('%m-%d-%y'),
                    total_sales=0.0,
                    week_sales=0.0
                )
                db.session.add(store)
                db.session.commit()
            
            # Check if product already exists
            existing_product = Product.query.filter_by(
                store_id=store.id,
                handle=data_json["product"]['handle']
            ).first()
            
            if existing_product:
                return {
                    "status": "error",
                    "message": "Product is already being tracked"
                }
            
            # Create new product
            new_product = Product(
                store_id=store.id,
                title=data_json["product"]['title'],
                handle=data_json["product"]['handle'],
                bought=data_json["product"]['updated_at'],
                post=data_json["product"]['published_at'],
                image=data_json["product"]["images"][0]["src"],
                price=float(data_json["product"]["variants"][0]["price"]),
                total_price=0.0,
                total_sales=0,
                track_start=datetime.today().strftime('%m-%d-%y')
            )
            
            db.session.add(new_product)
            db.session.commit()
            
            return {
                "status": "success",
                "message": "Product tracking started",
                "data": {
                    "title": new_product.title,
                    "price": new_product.price,
                    "track_start": new_product.track_start
                }
            }
        
        result = handle_db_operation(db_operation)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f'Error tracking product: {str(e)}')
        return jsonify({
            "status": "error",
            "message": str(e)
        })

@app.route('/api/store-data', methods=['GET'])
def get_store_data():
    logger.debug('Getting store data')
    try:
        website = request.args.get('website')
        domain = website.replace("https://", "").replace("/", "")
        
        def db_operation():
            store = Store.query.filter_by(domain=domain).first()
            
            if not store:
                return {
                    "status": "error",
                    "message": "Store not found"
                }
            
            products = Product.query.filter_by(store_id=store.id).all()
            products_data = [{
                "title": p.title,
                "handle": p.handle,
                "image": p.image,
                "price": p.price,
                "total_price": p.total_price,
                "total_sales": p.total_sales,
                "track_start": p.track_start
            } for p in products]
            
            return {
                "status": "success",
                "data": {
                    "track_start": store.track_start,
                    "total_sales": store.total_sales,
                    "week_sales": store.week_sales,
                    "products": products_data
                }
            }
        
        result = handle_db_operation(db_operation)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f'Error getting store data: {str(e)}')
        return jsonify({
            "status": "error",
            "message": str(e)
        })

@app.route('/api/product-data', methods=['GET'])
def get_product_data():
    logger.debug('Getting product data')
    try:
        product_link = request.args.get('product_link')
        
        handle_id = product_link.split("/products/")[1].split('?')[0]
        domain = product_link.split("/")[2]
        
        def db_operation():
            store = Store.query.filter_by(domain=domain).first()
            if not store:
                return {
                    "status": "error",
                    "message": "Store not found"
                }
                
            product = Product.query.filter_by(store_id=store.id, handle=handle_id).first()
            if not product:
                return {
                    "status": "error",
                    "message": "Product not found"
                }
            
            return {
                "status": "success",
                "data": {
                    "title": product.title,
                    "handle": product.handle,
                    "image": product.image,
                    "price": product.price,
                    "total_price": product.total_price,
                    "total_sales": product.total_sales,
                    "track_start": product.track_start,
                    "bought": product.bought,
                    "post": product.post
                }
            }
        
        result = handle_db_operation(db_operation)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f'Error getting product data: {str(e)}')
        return jsonify({
            "status": "error",
            "message": str(e)
        })

if __name__ == '__main__':
    app.run(debug=True, port=5001)
