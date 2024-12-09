# Shopify Sales Tracker

A web application for tracking and monitoring Shopify store sales data.

## Features

- Track individual product sales and performance
- View store-wide sales statistics
- Monitor product revenue and sales history
- Beautiful, responsive UI built with TailwindCSS

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file with your MongoDB connection string:
```
MONGO_URI=your_mongodb_connection_string
```

3. Run the application:
```bash
python app.py
```

4. Visit `http://localhost:5000` in your browser

## Usage

1. **Track a Product**:
   - Enter a Shopify product URL to start tracking its sales

2. **View Store Data**:
   - Enter your store URL to see overall performance metrics
   - View all tracked products and their statistics

3. **Check Product Performance**:
   - Enter a product URL to see detailed sales data
   - Monitor individual product metrics and history

## Security Note

Make sure to keep your MongoDB connection string secure and never commit it to version control.
