import os
import requests
import sqlite3
import random
import string
from datetime import datetime
from flask import Flask, jsonify, request

app = Flask(__name__)

# Configuration
WEATHER_API_BASE = "https://wttr.in/"
DATABASE_PATH = '/tmp/weather.db'

# ========== DATABASE SETUP ==========
def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS api_keys
                 (key TEXT PRIMARY KEY, credits INTEGER, created_at TEXT, status TEXT)''')
    
    # Add demo API keys for testing
    demo_keys = [
        ('WEATHER123', 100, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'active'),
        ('WEATHER456', 50, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'active'),
        ('WEATHER789', 25, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'active'),
    ]
    
    for key, credits, created_at, status in demo_keys:
        check = conn.execute('SELECT * FROM api_keys WHERE key = ?', (key,)).fetchone()
        if not check:
            conn.execute('INSERT INTO api_keys (key, credits, created_at, status) VALUES (?, ?, ?, ?)',
                         (key, credits, created_at, status))
    
    conn.commit()
    conn.close()
    print("✅ Database initialized")

init_db()

# ========== MAIN ROUTES ==========
@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "service": "Weather API",
        "developer": "@FroxtDevil",
        "owner": "@notxsatvir",
        "version": "2.0.0",
        "endpoints": {
            "GET /": "API Information",
            "GET /health": "Health Check",
            "GET /api/weather?key=API_KEY&city=CityName": "Get Weather Data"
        },
        "usage": "/api/weather?key=WEATHER123&city=Delhi",
        "test_api_keys": ["WEATHER123", "WEATHER456", "WEATHER789"]
    })

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "owner": "@notxsatvir",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/weather')
def get_weather():
    api_key = request.args.get('key')
    city = request.args.get('city')
    
    # Validate API key and city
    if not api_key or not city:
        return jsonify({
            "status": "error",
            "message": "API key and City name are required",
            "usage": "/api/weather?key=YOUR_KEY&city=Delhi",
            "example": "/api/weather?key=WEATHER123&city=Mumbai"
        }), 400
    
    # Check API key in database
    conn = get_db_connection()
    key_data = conn.execute('SELECT * FROM api_keys WHERE key = ? AND status = "active"', (api_key,)).fetchone()
    
    if not key_data:
        conn.close()
        return jsonify({
            "status": "error",
            "message": "Invalid or expired API Key",
            "valid_keys": ["WEATHER123", "WEATHER456", "WEATHER789"]
        }), 403
    
    if key_data['credits'] <= 0:
        conn.close()
        return jsonify({
            "status": "error",
            "message": "Insufficient credits. Please recharge your API key.",
            "credits_left": 0
        }), 403
    
    try:
        # Fetch weather data from wttr.in
        response = requests.get(f"{WEATHER_API_BASE}{city}?format=j1", timeout=15)
        
        if response.status_code == 200:
            # Deduct 1 credit
            new_credits = key_data['credits'] - 1
            conn.execute('UPDATE api_keys SET credits = ? WHERE key = ?', (new_credits, api_key))
            conn.commit()
            
            weather_data = response.json()
            
            # Extract current conditions
            current = weather_data.get('current_condition', [{}])[0]
            
            return jsonify({
                "status": "success",
                "owner": "@notxsatvir",
                "developer": "@FroxtDevil",
                "city": city,
                "credits_left": new_credits,
                "weather": {
                    "temperature_celsius": current.get('temp_C', 'N/A'),
                    "temperature_fahrenheit": current.get('temp_F', 'N/A'),
                    "humidity": current.get('humidity', 'N/A'),
                    "wind_speed_kmh": current.get('windspeedKmph', 'N/A'),
                    "weather_desc": current.get('weatherDesc', [{}])[0].get('value', 'N/A'),
                    "pressure": current.get('pressure', 'N/A'),
                    "visibility": current.get('visibility', 'N/A'),
                    "uv_index": current.get('uvIndex', 'N/A')
                },
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "status": "error",
                "message": f"Could not fetch weather for '{city}'. Please check city name.",
                "example_cities": ["Delhi", "Mumbai", "London", "New York", "Tokyo"]
            }), 404
            
    except requests.exceptions.Timeout:
        return jsonify({
            "status": "error",
            "message": "Request timeout. Please try again."
        }), 504
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Server error: {str(e)}"
        }), 500
    finally:
        conn.close()

@app.route('/api/keys', methods=['GET'])
def get_keys_info():
    """Get list of valid API keys (for testing only)"""
    conn = get_db_connection()
    keys = conn.execute('SELECT key, credits, status FROM api_keys WHERE status = "active"').fetchall()
    conn.close()
    
    return jsonify({
        "status": "success",
        "owner": "@notxsatvir",
        "available_keys": [dict(key) for key in keys],
        "note": "These are test keys. For production, contact @notxsatvir"
    })

@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "status": "error",
        "message": "Endpoint not found",
        "available_endpoints": ["/", "/health", "/api/weather", "/api/keys"],
        "usage": "/api/weather?key=YOUR_KEY&city=CityName"
    }), 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("="*50)
    print("🌤️ WEATHER API STARTED")
    print("👑 Owner: @notxsatvir")
    print("🔑 Test Keys: WEATHER123, WEATHER456, WEATHER789")
    print("="*50)
    app.run(host='0.0.0.0', port=port, debug=False)
