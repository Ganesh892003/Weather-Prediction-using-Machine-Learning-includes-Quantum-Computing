from flask import Flask, render_template, jsonify, redirect, url_for, request, session
import json
import utils
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'the random string'

with open('details.json', 'r') as f:
    users = json.load(f)

news_list = utils.get_news().get("articles", [])[:6]
logger.debug(f"Fetched news articles: {news_list}")

class Post:
    def __init__(self, title, image_url):
        self.title = title or "No Title"
        self.image_url = image_url or ""

posts = [Post(news_list[i].get("title", "No Title"), news_list[i].get("urlToImage", "")) for i in range(len(news_list))]

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        longitude = request.form.get('longitude', '0.0')
        latitude = request.form.get('latitude', '0.0')
        username = request.form.get('email', '')
        password = request.form.get('password', '')
        logger.debug(f'Login attempt - user: {username}, password: {password}, lat: {latitude}, long: {longitude}')
        if username in users and users[username] == password:
            session['lat'] = latitude
            session['lon'] = longitude
            return redirect(url_for('weatherDetails'))
        error = 'Invalid username or password'
        return render_template('Login.html', error=error)
    return render_template('Login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email', '')
        password = request.form.get('password', '')
        confirmPassword = request.form.get('confirm-password', '')
        logger.debug(f'Signup attempt - user: {email}, password: {password}, confirm: {confirmPassword}')
        if password == confirmPassword:
            users[email] = password
            with open('details.json', 'w') as jf:
                json.dump(users, jf)
            return redirect(url_for('login'))
        error = 'Passwords do not match'
        return render_template('Signup.html', error=error)
    return render_template('Signup.html')

@app.route('/weatherDetails', methods=['GET', 'POST'])
def weatherDetails():
    lat = float(session.get('lat', 13.069457))  # Ensure lat is float
    lon = float(session.get('lon', 80.215355))  # Ensure lon is float
    data = utils.get_current_weather_data(lat=lat, lon=lon) or {
        "temp": "N/A °C",
        "wind": "N/A",
        "humidity": "N/A",
        "type": "N/A",
        "Sunrise": "N/A",
        "Sunset": "N/A",
        "date": datetime.now().strftime("%Y-%m-%d")
    }
    logger.debug(f"Weather data loaded for lat={lat}, lon={lon}: {data}")
    now = datetime.now()
    current_month = now.strftime("%B")
    current_year = now.year
    calendar_days = []
    for i in range(15):
        day = now + timedelta(days=i)
        calendar_days.append({
            "date": day.strftime("%Y-%m-%d"),
            "day_name": day.strftime("%A"),
            "day_number": day.day,
            "is_today": i == 0
        })
    return render_template(
        'Weather.html',
        data=data,
        current_month=current_month,
        current_year=current_year,
        calendar_days=calendar_days
    )

@app.route('/get_24hour_forecast', methods=['POST'])
def get_24hour_forecast():
    selected_date = request.json.get('selected_date', datetime.now().strftime("%Y-%m-%d"))
    lat = float(session.get('lat', 13.069457))  # Fallback to default lat
    lon = float(session.get('lon', 80.215355))  # Fallback to default lon
    hourly_data = utils.get_24hour_forecast(selected_date, lat=lat, lon=lon)
    logger.debug(f"Processed forecast data for {selected_date}: {hourly_data}")
    if not hourly_data or len(hourly_data) == 0:
        logger.warning(f"No hourly data for {selected_date}, using fallback")
        hourly_data = [{
            "hour": "N/A",
            "temp": "N/A °C",
            "type": "N/A",
            "wind": "N/A",
            "humidity": "N/A",
            "sunrise": "N/A",
            "sunset": "N/A"
        }]
    return jsonify(hourly_data)
@app.route('/floodzone', methods=['POST', 'GET'])
def floodzone():
    if request.method == 'POST':
        selected_zone = request.form.get('zone')
        map_image_url = get_map(selected_zone)
        return render_template('FloodZone.html', map=map_image_url)
    return render_template('FloodZone.html', map=None)

def get_map(zone):
    maps = {
        "flood Map": utils.get_flood_map(),
        "lake": utils.get_lake_zones(),
        "drainage": utils.get_drinage_lines(),
    }
    return maps.get(zone, "default_map_url_if_zone_not_found")

@app.route('/alert', methods=['POST', 'GET'])
def alert():
    return render_template('Alert.html', posts=posts)

@app.route('/shelter', methods=['POST', 'GET'])
def shelter():
    if request.method == 'POST':
        location_data = request.json
        session['location_data'] = location_data
        return redirect(url_for('shelter_map_page'))
    return render_template('Shelter.html')

@app.route('/shelter_map_page', methods=['GET'])
def shelter_map_page():
    location_data = session.get('location_data')
    if location_data:
        latitude, longitude = utils.get_lat_long_for_ip()
        map_html = utils.shelter_map(latitude, longitude)
        return render_template('map.html', map=map_html)
    return "No location data found", 404

@app.route('/sos', methods=['POST', 'GET'])
def sos():
    if request.method == 'POST':
        name = request.form.get('name', '')
        situation = request.form.get('situation', '')
        contact = request.form.get('contact', '')
        utils.send_email(name, situation, contact)
    return render_template('Sos.html')

if __name__ == '__main__':
    app.run(debug=True)