from datetime import datetime, timedelta
from collections import defaultdict
import requests
import json
import math

# Function to convert a row of earthquake data into the desired format
def convert_to_earthquake_data(row):
    return {
        "magnitude": float(row["mag"]),
        "location": row["place"],
        "date": datetime.strptime(row["time"], "%Y-%m-%dT%H:%M:%S.%fZ")
    }

# Function to retrieve earthquake data using the USGS Earthquake API
def retrieve_and_save_earthquake_data(starttime, endtime, minmagnitude, filename):
    base_url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    params = {
        "format": "geojson",
        "starttime": starttime,
        "endtime": endtime,
        "minmagnitude": minmagnitude
    }
    
    response = requests.get(base_url, params=params)
    if response.status_code == 200:
        earthquake_data = response.json()
        
        if filename:
            with open(filename, "w") as json_file:
                json.dump(earthquake_data, json_file)
        
        return earthquake_data
    else:
        return None

# Function to convert timestamp to datetime
def timestamp_to_datetime(timestamp):
    return datetime.utcfromtimestamp(timestamp / 1000.0)  # Convert milliseconds to seconds



def calculate_bounding_box(lat, lon, radius_miles):
    # Earth's radius in miles
    earth_radius = 3958.8  # miles

    # Convert latitude and longitude from degrees to radians
    lat = math.radians(lat)
    lon = math.radians(lon)

    # Convert radius from miles to radians
    radius = radius_miles / earth_radius

    # Calculate bounds
    min_lat = lat - radius
    max_lat = lat + radius
    min_lon = lon - radius
    max_lon = lon + radius

    # Convert bounds back to degrees
    min_lat = math.degrees(min_lat)
    max_lat = math.degrees(max_lat)
    min_lon = math.degrees(min_lon)
    max_lon = math.degrees(max_lon)

    return min_lat, max_lat, min_lon, max_lon
"""
# Example coordinates (e.g., latitude and longitude of the first point)
initial_latitude = 34.0522  # Los Angeles, CA
initial_longitude = -118.2437  # Los Angeles, CA

# Radius in miles (1000 miles in this case)
radius_miles = 1000

# Calculate the bounding box for the 1000-mile radius
min_lat, max_lat, min_lon, max_lon = calculate_bounding_box(initial_latitude, initial_longitude, radius_miles)

print(f"Bounding Box Coordinates (Latitude, Longitude):")
print(f"Min Latitude: {min_lat}")
print(f"Max Latitude: {max_lat}")
print(f"Min Longitude: {min_lon}")
print(f"Max Longitude: {max_lon}")
"""


def find_megaquakes_and_aftershocks(megamagnitude_threshold, aftermagnitude_threshold, radius_miles):
    starttime = "1900-01-01T00:00:00"
    endtime = "now"
    minmagnitude = aftermagnitude_threshold
    filename = ""
    earthquake_data = retrieve_and_save_earthquake_data(starttime, endtime, minmagnitude, filename)
    earthquake_features = earthquake_data["features"]

  
    megaquake_count = 0

    for event in earthquake_features:
        if event["properties"]["mag"] >= megamagnitude_threshold:

            first_event = event
            megaquake_count += 1
            first_time = timestamp_to_datetime(first_event["properties"]["time"])
            first_megaquake_lat = first_event["geometry"]["coordinates"][1]
            first_megaquake_lon = first_event["geometry"]["coordinates"][0]
  
            min_lat, max_lat, min_lon, max_lon = calculate_bounding_box(first_megaquake_lat, first_megaquake_lon, radius_miles)

            # Filter aftershocks occurring after the first megamagnitude_threshold earthquake within the bounding box
            filtered_aftershocks = [
	            aftershock for aftershock in earthquake_features
	            if (
	                timestamp_to_datetime(aftershock["properties"]["time"]) > first_time and
		            min_lat <= aftershock["geometry"]["coordinates"][1] <= max_lat and
		            min_lon <= aftershock["geometry"]["coordinates"][0] <= max_lon
	            )
            ]

            # Count the number of earthquakes in the filtered dataset
            num_earthquakes_after_first = len(filtered_aftershocks)

            print(f"Number of earthquakes with magnitude >= {aftermagnitude_threshold} after the first M{megamagnitude_threshold} earthquake in a {radius_miles}-mile radius: {num_earthquakes_after_first}")
    
    if megaquake_count == 0:
        print(f"No megaquakes (magnitude >= {megamagnitude_threshold}) found.")

def find_megaquakes_and_aftershocks_test(megamagnitude_threshold, aftermagnitude_threshold, after_shocks_counts):
    starttime = "1900-01-01T00:00:00"
    endtime = "now"
    minmagnitude = aftermagnitude_threshold
    filename = ""
    earthquake_data = retrieve_and_save_earthquake_data(starttime, endtime, minmagnitude, filename)
    earthquake_features = earthquake_data["features"]
    
    megaquake_count = 0

    for event in earthquake_features:
        if event["properties"]["mag"] >= megamagnitude_threshold:
            megaquake_count += 1
            first_megaquake_lat = event["geometry"]["coordinates"][1]
            first_megaquake_lon = event["geometry"]["coordinates"][0]
            
            # Filter aftershocks occurring in the same region
            filtered_aftershocks = [
                aftershock for aftershock in earthquake_features
                if (
                    aftershock["properties"]["mag"] >= aftermagnitude_threshold
                    and abs(aftershock["geometry"]["coordinates"][1] - first_megaquake_lat) < 1.0
                    and abs(aftershock["geometry"]["coordinates"][0] - first_megaquake_lon) < 1.0
                )
            ]

            num_filtered_aftershocks = len(filtered_aftershocks)
            if num_filtered_aftershocks >= after_shocks_counts:
                print(f"Event {event['properties']['time']} is a megaquake (M{event['properties']['mag']}).")
                print(f"Number of aftershocks with magnitude >= {aftermagnitude_threshold} in the same region: {num_filtered_aftershocks}")
    
    if megaquake_count == 0:
        print(f"No megaquakes (magnitude >= {megamagnitude_threshold}) found.")

# Function to process earthquake data and find multiple quakes in a 24-hour window
def find_multiple_quakes_in_window(earthquake_features, magnitude_threshold, days=1, print_all=0):
    earthquake_counts_by_year = defaultdict(int)
    earthquake_counts_by_month = defaultdict(int)
    earthquake_counts_by_day = defaultdict(int)

    earthquake_features.sort(key=lambda entry: timestamp_to_datetime(entry["properties"]["time"]))

    # Initialize variables for 24-hour window tracking
    current_date = timestamp_to_datetime(earthquake_features[0]["properties"]["time"])
    earthquakes_within_24hrs = []

    for entry in earthquake_features:
        timestamp = entry["properties"]["time"]
        date_time = timestamp_to_datetime(timestamp)
        year, month, day = date_time.year, date_time.month, date_time.day

        earthquake_counts_by_year[year] += 1
        earthquake_counts_by_month[f"{year}-{month:02d}"] += 1
        earthquake_counts_by_day[f"{year}-{month:02d}-{day:02d}"] += 1

        if date_time - current_date <= timedelta(days):
            earthquakes_within_24hrs.append(entry)
        else:
            if len([e for e in earthquakes_within_24hrs if e["properties"]["mag"] >= magnitude_threshold]) > 1:
                window_count = len( earthquakes_within_24hrs)
                print(f"{days}-Day Window {window_count}:")
                for earthquake in earthquakes_within_24hrs:
                    print(f"{earthquake['properties']['place']} - Magnitude: {earthquake['properties']['mag']} - Date: {timestamp_to_datetime(earthquake['properties']['time'])}")
                print("\n")

            current_date = date_time
            earthquakes_within_24hrs = [entry]

    if len([e for e in earthquakes_within_24hrs if e["properties"]["mag"] >= magnitude_threshold]) > 1:
        window_count = len( earthquakes_within_24hrs)
        print(f"Last {days}-Day Window {window_count}:")
        # print(f"Last {days}-Day Window {len( earthquakie_within_24hours)}:")
        for earthquake in earthquakes_within_24hrs:
            print(f"{earthquake['properties']['place']} - Magnitude: {earthquake['properties']['mag']} - Date: {timestamp_to_datetime(earthquake['properties']['time'])}")
    
    if print_all:
        print("\nEarthquake Counts by Year:")
        for year, count in earthquake_counts_by_year.items():
            print(f"Year {year}: {count} earthquakes")

        print("\nEarthquake Counts by Month:")
        for month, count in earthquake_counts_by_month.items():
            print(f"{month}: {count} earthquakes")

        print("\nEarthquake Counts by Day:")
        for day, count in earthquake_counts_by_day.items():
            print(f"{day}: {count} earthquakes")

# Function to find the top 3 earthquake frequencies by year, month, and day
def find_top_3_earthquake_frequencies_by_year_month_day(earthquake_features):
    earthquake_counts_by_year = defaultdict(int)
    earthquake_counts_by_month = defaultdict(int)
    earthquake_counts_by_day = defaultdict(int)

    for entry in earthquake_features:
        timestamp = entry["properties"]["time"]
        date_time = timestamp_to_datetime(timestamp)
        year, month, day = date_time.year, date_time.month, date_time.day
        earthquake_counts_by_year[year] += 1
        earthquake_counts_by_month[f"{year}-{month:02d}"] += 1
        earthquake_counts_by_day[f"{year}-{month:02d}-{day:02d}"] += 1

    sorted_years = sorted(earthquake_counts_by_year.items(), key=lambda x: x[1], reverse=True)
    print("\nTop Three Earthquake Frequencies by Year:")
    for year, count in sorted_years[:3]:
        print(f"Year {year}: {count} earthquakes")

    sorted_months = sorted(earthquake_counts_by_month.items(), key=lambda x: x[1], reverse=True)
    print("\nTop Three Earthquake Frequencies by Month:")
    for year_month, count in sorted_months[:3]:
        year, month = map(int, year_month.split("-"))
        print(f"Month {year}-{month:02d}: {count} earthquakes")

    sorted_days = sorted(earthquake_counts_by_day.items(), key=lambda x: x[1], reverse=True)
    print("\nTop Three Earthquake Frequencies by Day:")
    for year_month_day, count in sorted_days[:3]:
        year, month, day = map(int, year_month_day.split("-"))
        print(f"Day {year}-{month:02d}-{day:02d}: {count} earthquakes")

if __name__ == "__main__":
    # Specify the path to your CSV file
    csv_file_path = "earthquake6plus24.csv"

    # Define the magnitude threshold (6.0 or greater)
    magnitude_threshold = 6.0

    # Step 1: Read earthquake data from a file or API (choose one method)
    # earthquake_data = read_earthquake_data_from_file(csv_file_path)
    starttime = "1900-01-01T00:00:00"
    endtime = "now"
    minmagnitude = 6.0
    filename = "earthquake_data.json"
    earthquake_data = retrieve_and_save_earthquake_data(starttime, endtime, minmagnitude, filename)

    # Step 2a: Find multiple quakes in a 24-hour window
    find_multiple_quakes_in_window(earthquake_data["features"], magnitude_threshold)
    # Step 2b: Find multiple quakes in a 30 day window
    find_multiple_quakes_in_window(earthquake_data["features"], magnitude_threshold, 30)

    # Step 3: Find the top 3 earthquake frequencies by year, month, and day
    find_top_3_earthquake_frequencies_by_year_month_day(earthquake_data["features"])
    
    # wip
   # find_megaquakes_and_aftershocks(8.0, 6.0, 300)
   
