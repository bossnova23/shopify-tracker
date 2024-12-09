from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
from dotenv import load_dotenv
import requests
from datetime import datetime
import random
import colorsys
import json

load_dotenv()

app = Flask(__name__, static_folder='static')

# Database configuration
if os.environ.get('RENDER'):
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        database_url = database_url.replace('postgres://', 'postgresql://')
    else:
        database_url = 'sqlite:///shopify_themes.db'
    
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
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shopify_themes.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Theme(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    style = db.Column(db.String(50), nullable=False)
    primary_color = db.Column(db.String(7), nullable=False)
    secondary_color = db.Column(db.String(7), nullable=False)
    accent_color = db.Column(db.String(7), nullable=False)
    font_primary = db.Column(db.String(100), nullable=False)
    font_secondary = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    preview_data = db.Column(db.JSON)

with app.app_context():
    db.create_all()

def generate_color_palette():
    # Generate a harmonious color palette
    hue = random.random()
    primary = colorsys.hsv_to_rgb(hue, 0.6, 0.9)
    secondary = colorsys.hsv_to_rgb((hue + 0.33) % 1, 0.5, 0.8)
    accent = colorsys.hsv_to_rgb((hue + 0.66) % 1, 0.7, 1)
    
    return {
        'primary': '#{:02x}{:02x}{:02x}'.format(int(primary[0]*255), int(primary[1]*255), int(primary[2]*255)),
        'secondary': '#{:02x}{:02x}{:02x}'.format(int(secondary[0]*255), int(secondary[1]*255), int(secondary[2]*255)),
        'accent': '#{:02x}{:02x}{:02x}'.format(int(accent[0]*255), int(accent[1]*255), int(accent[2]*255))
    }

FONTS = {
    'modern': ['Roboto', 'Open Sans', 'Lato'],
    'elegant': ['Playfair Display', 'Cormorant Garamond', 'Libre Baskerville'],
    'playful': ['Quicksand', 'Comic Neue', 'Fredoka One'],
    'minimal': ['Montserrat', 'Work Sans', 'Source Sans Pro']
}

STYLES = ['modern', 'elegant', 'playful', 'minimal']

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/generate-theme', methods=['POST'])
def generate_theme():
    try:
        data = request.json
        style = data.get('style', random.choice(STYLES))
        
        # Generate colors
        colors = generate_color_palette()
        
        # Select fonts
        fonts = FONTS[style]
        font_primary = random.choice(fonts)
        font_secondary = random.choice([f for f in fonts if f != font_primary])
        
        # Create theme
        theme = Theme(
            name=f"{style.capitalize()} Theme {datetime.now().strftime('%Y%m%d%H%M')}",
            style=style,
            primary_color=colors['primary'],
            secondary_color=colors['secondary'],
            accent_color=colors['accent'],
            font_primary=font_primary,
            font_secondary=font_secondary,
            preview_data=json.dumps({
                'colors': colors,
                'fonts': {
                    'primary': font_primary,
                    'secondary': font_secondary
                },
                'style': style
            })
        )
        
        db.session.add(theme)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'theme': {
                'id': theme.id,
                'name': theme.name,
                'style': theme.style,
                'colors': colors,
                'fonts': {
                    'primary': font_primary,
                    'secondary': font_secondary
                }
            }
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/themes', methods=['GET'])
def get_themes():
    themes = Theme.query.order_by(Theme.created_at.desc()).limit(10).all()
    return jsonify({
        'status': 'success',
        'themes': [{
            'id': theme.id,
            'name': theme.name,
            'style': theme.style,
            'colors': {
                'primary': theme.primary_color,
                'secondary': theme.secondary_color,
                'accent': theme.accent_color
            },
            'fonts': {
                'primary': theme.font_primary,
                'secondary': theme.font_secondary
            }
        } for theme in themes]
    })

if __name__ == '__main__':
    app.run(debug=True, port=5001)
