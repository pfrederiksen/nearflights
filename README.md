# Nearby Flights Tracker

A simple text-based UI application that displays the number of flights within a specified distance from a given location. The app uses the OpenSky Network API to fetch live flight data.

## Features

- Enter your location using a human-readable address.
- View a list of flights within a specified radius, with distances in miles.
- See detailed information about each flight, including airline name and military status.
- Follow a specific flight.
- Real-time updates of flight data.

## Requirements

- Python 3.6+
- Required packages (see `requirements.txt`):
  - rich
  - requests
  - python-dotenv
  - geopy
  - readchar

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/pfrederiksen/nearflights.git
   cd nearflights
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Run the application:
   ```bash
   python nearflights.py
   ```

2. Enter your address when prompted. The app will convert it to latitude and longitude coordinates.

3. Specify the number of closest flights to display and the update interval in seconds.

4. Use the up/down arrow keys to navigate the flight list, press Enter to see detailed information, press 'r' to refresh the data, and 'q' to quit.

## Note

This application uses the OpenSky Network API to fetch live flight data. The API is free to use and does not require an API key. However, please be mindful of the API's usage policy and rate limits.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 