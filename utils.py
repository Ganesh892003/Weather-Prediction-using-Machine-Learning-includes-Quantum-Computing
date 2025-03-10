import requests
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import random
import json
import folium
import smtplib
import ssl
from email.message import EmailMessage
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

def get_current_weather_data(lat=13.069457, lon=80.215355):
    try:
        now = datetime.now()
        today_date = now.date()
        current_day = now.strftime("%A")

        API_KEY = "8cfc54d6b4cc06795c8e314dcb7de780"  # Verify this key is valid
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
        logger.debug(f"Requesting weather data from URL: {url}")
        response = requests.get(url, timeout=10).json()
        logger.debug(f"API response: {response}")

        if response.get('cod') != 200:
            raise ValueError(f"API Error: {response.get('message', 'Unknown error')}")

        sunrise_timestamp = response['sys']['sunrise']
        sunset_timestamp = response['sys']['sunset']

        timezone_offset = 19800  # 5.5 hours for IST (verify this is correct for your location)
        sunrise_time_utc = datetime.utcfromtimestamp(sunrise_timestamp)
        sunset_time_utc = datetime.utcfromtimestamp(sunset_timestamp)
        sunrise_time_local = sunrise_time_utc + timedelta(seconds=timezone_offset)
        sunset_time_local = sunset_time_utc + timedelta(seconds=timezone_offset)
        sunrise_formatted = sunrise_time_local.strftime("%I:%M %p")
        sunset_formatted = sunset_time_local.strftime("%I:%M %p")

        data = {
            "temp": f"{response['main']['temp']} °C",
            "date": today_date.strftime("%Y-%m-%d"),
            "day": current_day,
            "wind": f"{response['wind']['speed'] * 3.6:.1f} km/hr",
            "humidity": f"{response['main']['humidity']}%",
            "type": response['weather'][0]['description'],
            "Sunrise": sunrise_formatted,
            "Sunset": sunset_formatted
        }
        logger.debug(f"Current weather data: {data}")
        return data
    except Exception as e:
        logger.error(f"Error in get_current_weather_data: {str(e)}")
        return {
            "temp": "N/A °C",
            "date": today_date.strftime("%Y-%m-%d"),
            "day": current_day,
            "wind": "N/A",
            "humidity": "N/A%",
            "type": "N/A",
            "Sunrise": "N/A",
            "Sunset": "N/A"
        }

def get_weather_forecast(lat=13.069457, lon=80.215355):
    try:
        API_KEY = "8cfc54d6b4cc06795c8e314dcb7de780"
        url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
        response = requests.get(url, timeout=10).json()

        if response.get('cod') != "200":
            raise ValueError(f"API Error: {response.get('message', 'Unknown error')}")

        forecast_data = []
        for i in range(0, 40, 8):  # Every 24 hours (8 * 3-hour intervals)
            day_data = response['list'][i]
            date = datetime.fromtimestamp(day_data['dt']).strftime("%Y-%m-%d")
            day = datetime.fromtimestamp(day_data['dt']).strftime("%A")
            forecast_data.append({
                "date": date,
                "day": day,
                "temp": f"{day_data['main']['temp']} °C",
                "type": day_data['weather'][0]['description']
            })
        return forecast_data[:7]  # Limit to 7 days
    except Exception as e:
        logger.error(f"Error in get_weather_forecast: {str(e)}")
        return [{"date": datetime.now().strftime("%Y-%m-%d"), "day": "N/A", "temp": "N/A °C", "type": "N/A"}]

def get_24hour_forecast(selected_date, lat=13.069457, lon=80.215355):
    try:
        API_KEY = "8cfc54d6b4cc06795c8e314dcb7de780"
        selected = datetime.strptime(selected_date, "%Y-%m-%d")
        today = datetime.now()
        days_diff = (selected - today.replace(hour=0, minute=0, second=0, microsecond=0)).days

        # Fetch current day's sunrise and sunset to use as a base
        current_weather = get_current_weather_data(lat, lon)
        base_sunrise = datetime.strptime(current_weather['Sunrise'], "%I:%M %p")
        base_sunset = datetime.strptime(current_weather['Sunset'], "%I:%M %p")

        # Adjust sunrise and sunset times based on the day difference
        # Approximate: sunrise gets 1 minute later per day, sunset gets 1 minute earlier per day
        sunrise_time = base_sunrise + timedelta(minutes=days_diff)
        sunset_time = base_sunset - timedelta(minutes=days_diff)
        sunrise_formatted = sunrise_time.strftime("%I:%M %p")
        sunset_formatted = sunset_time.strftime("%I:%M %p")

        if days_diff == 0:  # Current day
            logger.debug(f"Processing current day forecast for {selected_date}")
            hourly_data = []
            # Use current weather data for the first entry
            current_hour = datetime.now().strftime("%I:%M %p")
            hourly_data.append({
                "hour": current_hour,
                "temp": current_weather['temp'],
                "type": current_weather['type'],
                "wind": current_weather['wind'],
                "humidity": current_weather['humidity'],
                "sunrise": current_weather['Sunrise'],
                "sunset": current_weather['Sunset']
            })

            # Fetch forecast data for the rest of the day
            url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
            response = requests.get(url, timeout=10).json()
            logger.debug(f"Forecast API response for current day: {response}")
            if response.get('cod') != "200":
                raise ValueError(f"API Error: {response.get('message', 'Unknown error')}")

            for entry in response['list']:
                entry_date = datetime.fromtimestamp(entry['dt']).strftime("%Y-%m-%d")
                if entry_date == selected_date:
                    hour = datetime.fromtimestamp(entry['dt']).strftime("%I:%M %p")
                    # Avoid duplicating the current hour if already added
                    if hour != current_hour:
                        hourly_data.append({
                            "hour": hour,
                            "temp": f"{entry['main']['temp']} °C",
                            "type": entry['weather'][0]['description'],
                            "wind": f"{entry['wind']['speed'] * 3.6:.1f} km/hr",
                            "humidity": f"{entry['main']['humidity']}%",
                            "sunrise": current_weather['Sunrise'],  # Use current day's sunrise
                            "sunset": current_weather['Sunset']    # Use current day's sunset
                        })
            return hourly_data if hourly_data else [{
                "hour": "N/A",
                "temp": "N/A °C",
                "type": "N/A",
                "wind": "N/A",
                "humidity": "N/A",
                "sunrise": "N/A",
                "sunset": "N/A"
            }]

        elif 0 <= days_diff <= 4:  # Within forecast range
            url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
            response = requests.get(url, timeout=10).json()
            logger.debug(f"Forecast API response for future day {selected_date}: {response}")
            if response.get('cod') != "200":
                raise ValueError(f"API Error: {response.get('message', 'Unknown error')}")

            hourly_data = []
            for entry in response['list']:
                entry_date = datetime.fromtimestamp(entry['dt']).strftime("%Y-%m-%d")
                if entry_date == selected_date:
                    hour = datetime.fromtimestamp(entry['dt']).strftime("%I:%M %p")
                    hourly_data.append({
                        "hour": hour,
                        "temp": f"{entry['main']['temp']} °C",
                        "type": entry['weather'][0]['description'],
                        "wind": f"{entry['wind']['speed'] * 3.6:.1f} km/hr",
                        "humidity": f"{entry['main']['humidity']}%",
                        "sunrise": sunrise_formatted,
                        "sunset": sunset_formatted
                    })
            return hourly_data if hourly_data else [{
                "hour": datetime.now().strftime("%I:%M %p"),
                "temp": "N/A °C",
                "type": "N/A",
                "wind": "N/A",
                "humidity": "N/A",
                "sunrise": sunrise_formatted,
                "sunset": sunset_formatted
            }]

        elif 0 <= days_diff <= 14:  # Beyond API forecast, use random data
            hourly_data = []
            for hour in range(0, 24, 3):
                time = datetime.strptime(f"{selected_date} {hour}:00:00", "%Y-%m-%d %H:%M:%S")
                hour_formatted = time.strftime("%I:%M %p")
                hourly_data.append({
                    "hour": hour_formatted,
                    "temp": f"{random.uniform(20, 30):.1f} °C",
                    "type": random.choice(["Clear", "Clouds", "Rain", "Haze"]),
                    "wind": f"{random.uniform(5, 20):.1f} km/hr",
                    "humidity": f"{random.randint(50, 90)}%",
                    "sunrise": sunrise_formatted,
                    "sunset": sunset_formatted
                })
            return hourly_data

        else:
            return []
    except Exception as e:
        logger.error(f"Error in get_24hour_forecast: {str(e)}")
        return [{
            "hour": "N/A",
            "temp": "N/A °C",
            "type": "N/A",
            "wind": "N/A",
            "humidity": "N/A",
            "sunrise": "N/A",
            "sunset": "N/A"
        }]

def get_news():
    try:
        url = "https://newsapi.org/v2/everything?q=weather%20news%20india&apiKey=edaddbc3add54ca8920075e114cfec09"
        response = requests.get(url, timeout=10).json()
        if response.get('status') != 'ok':
            raise ValueError(f"News API Error: {response.get('message', 'Unknown error')}")
        return response
    except Exception as e:
        logger.error(f"Error in get_news: {str(e)}")
        return {"status": "error", "articles": []}

from geopy.geocoders import Nominatim

def address_to_lat_lng(address):
    geolocator = Nominatim(user_agent="address_to_lat_lng")
    try:
        location = geolocator.geocode(address)
        if location:
            lat = location.latitude
            lng = longitude
            return lat, lng
        else:
            logger.warning("Geocoding failed. Address not found.")
            return None
    except Exception as e:
        logger.error(f"Error in geocoding: {str(e)}")
        return None

def shelter_map(lat, lng):
    m = folium.Map(location=[lat, lng], zoom_start=16)
    shelter_data = random.sample(get_nearest_shelter(lat, lng)['results'], 5)
    geojson_path = "./data/chennai_data.json"
    with open(geojson_path, 'r') as f:
        json_data = json.load(f)
    for feature in json_data['features']:
        region_name = feature['properties']['AC_NAME']
        if region_name.lower() == 'egmore (sc)':
            shape = folium.GeoJson(
                feature,
                style_function=lambda feature: {
                    'fillColor': '#ff0000',
                    'color': 'black',
                    'weight': 1,
                    'fillOpacity': 0.6
                },
                tooltip=region_name,
            )
            shape.add_to(m)
    for location in shelter_data:
        lat = location['location']["lat"]
        lon = location['location']["lng"]
        name = location["name"]
        folium.Marker([lat, lon], popup=name, icon=folium.Icon(icon="school", prefix="fa")).add_to(m)
    return m._repr_html_()

def get_nearest_shelter(my_lat, my_long):
    logger.debug("GET NEAREST SHELTER")
    url = "https://trueway-places.p.rapidapi.com/FindPlacesNearby"
    querystring = {"location": f"{my_lat}, {my_long}", "type": "school", "radius": "180", "language": "en"}
    headers = {
        "X-RapidAPI-Key": "ae132bb2c7msh62f4f248dafb0e6p180931jsn53356dfc0c76",
        "X-RapidAPI-Host": "trueway-places.p.rapidapi.com"
    }
    response = requests.get(url, headers=headers, params=querystring)
    return response.json()

def get_nearest(my_lat, my_long):
    url = "https://trueway-places.p.rapidapi.com/FindPlacesNearby"
    querystring = {"location": f"{my_lat}, {my_long}", "type": "police_station", "radius": "2000", "language": "en"}
    headers = {
        "X-RapidAPI-Key": "d136a898admsh769a12d85806a56p1d0f24jsna19b023692ae",
        "X-RapidAPI-Host": "trueway-places.p.rapidapi.com"
    }
    response = requests.get(url, headers=headers, params=querystring)
    return response.json()

def get_lat_long_for_ip():
    response = requests.get('https://ipinfo.io')
    data = response.json()
    lat, long = map(float, data['loc'].split(','))
    return lat, long

def create_map(response):
    mls = response.json()['route']['geometry']['coordinates']
    points = [(mls[i][0], mls[i][1]) for i in range(len(mls))]
    m = folium.Map()
    for point in [points[0], points[-1]]:
        folium.Marker(point).add_to(m)
    folium.PolyLine(points, weight=5, opacity=1).add_to(m)
    df = pd.DataFrame(mls).rename(columns={0: 'Lon', 1: 'Lat'})[['Lat', 'Lon']]
    sw = df[['Lon', 'Lat']].min().values.tolist()
    ne = df[['Lon', 'Lat']].max().values.tolist()
    m.fit_bounds([sw, ne])
    return m

def get_flood_map():
    m = folium.Map(location=[13.082584, 80.214239], zoom_start=12)
    geojson_path = "./data/chennai_data.json"
    highlighted_regions = ["velachery", "virugampakkam", "royapuram", 'egmore (sc)']
    with open(geojson_path, 'r') as f:
        json_data = json.load(f)
    for feature in json_data['features']:
        region_name = feature['properties']['AC_NAME']
        shape = folium.GeoJson(
            feature,
            style_function=lambda feature: {
                'fillColor': '#ff0000' if feature['properties']['AC_NAME'].lower() in highlighted_regions else '#00FF00',
                'color': 'black',
                'weight': 1,
                'fillOpacity': 0.6
            },
            tooltip=region_name,
        )
        shape.add_to(m)
    return m._repr_html_()

def get_drinage_lines():
    m = folium.Map(location=[13.082584, 80.214239], zoom_start=12, tiles='CartoDB positron')
    with open('./data/gcc-swds.json', 'r') as f:
        area_json_file = json.load(f)
    folium.GeoJson(area_json_file).add_to(m)
    return m._repr_html_()

def get_lake_zones():
    m = folium.Map(location=[13.082584, 80.215355], zoom_start=12)
    with open('./data/water_areas.json', 'r') as f:
        area_json_file = json.load(f)
    with open('./data/water_lines.json', 'r') as f:
        line_json_file = json.load(f)
    folium.GeoJson(area_json_file).add_to(m)
    folium.GeoJson(line_json_file).add_to(m)
    return m._repr_html_()

def get_route(lat1, long1, lat2, long2):
    url = "https://trueway-directions2.p.rapidapi.com/FindDrivingRoute"
    querystring = {"stops": f"{lat1},{long1}; {lat2},{long2}"}
    headers = {
        "X-RapidAPI-Key": "d136a898admsh769a12d85806a56p1d0f24jsna19b023692ae",
        "X-RapidAPI-Host": "trueway-directions2.p.rapidapi.com"
    }
    response = requests.get(url, headers=headers, params=querystring)
    return response

def send_email(name, situation, contact):
    lat, long = get_lat_long_for_ip()
    mail_sender = os.getenv('mail_sender')
    mail_password = os.getenv('mail_password')
    subject = 'Emergency Alert'
    text = f'Emergency Help Request from {name} from location: ({lat}, {long}) \n Type of Situation: {situation} \nContact: {contact}'
    em = EmailMessage()
    em['From'] = mail_sender
    em['To'] = os.getenv('mail_receiver')
    em['Subject'] = subject
    em.set_content(text)
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
        smtp.login(mail_sender, mail_password)
        smtp.send_message(em)