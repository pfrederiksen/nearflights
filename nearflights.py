import os
import time
from typing import Dict, List, Optional, Tuple
import requests
from rich.console import Console, Group
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.layout import Layout
from dotenv import load_dotenv
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
import readchar
import math
from datetime import datetime

# Load environment variables
load_dotenv()

class FlightTracker:
    def __init__(self):
        self.console = Console()
        self.show_details = True  # Always show details now
        self.following_flight = None
        self.geolocator = Nominatim(user_agent="nearflights")
        self.base_url = "https://opensky-network.org/api/states/all"
        self.selected_index = 0
        self.flights: List[Dict] = []
        self.latitude = 0.0
        self.longitude = 0.0
        self.radius = 200
        self.update_interval = 10

    def get_coordinates(self, address: str) -> Tuple[float, float]:
        """Convert address to latitude and longitude coordinates."""
        try:
            location = self.geolocator.geocode(address)
            if location:
                return location.latitude, location.longitude
            else:
                self.console.print("[red]Could not find coordinates for the given address.[/red]")
                exit(1)
        except (GeocoderTimedOut, GeocoderUnavailable) as e:
            self.console.print(f"[red]Error geocoding address: {str(e)}[/red]")
            exit(1)

    def get_nearby_flights(self, lat, lon, num_flights):
        """Fetch the specified number of closest flights from OpenSky Network API"""
        try:
            self.console.print("[blue]Fetching flight data...[/blue]")
            url = f"https://opensky-network.org/api/states/all"
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            
            if not data or 'states' not in data:
                self.console.print("[red]No flight data available[/red]")
                return []
            
            flights = []
            for state in data['states']:
                if state[5] is None or state[6] is None:
                    continue  # Skip flights with missing coordinates
                flight_lat = state[6]
                flight_lon = state[5]
                distance = self.calculate_distance(lat, lon, flight_lat, flight_lon)
                
                # Determine if flight is military based on callsign
                callsign = state[1].strip() if state[1] else "UNKNOWN"
                is_military = callsign.startswith(('RCH', 'SAM', 'AF', 'NAVY', 'ARMY'))
                
                flights.append({
                    'flight_number': callsign,
                    'airline_name': self.get_airline_name(callsign),
                    'military': is_military,
                    'departure_airport': state[11] if state[11] else "Unknown",
                    'arrival_airport': state[12] if state[12] else "Unknown",
                    'distance': distance,
                    'status': 'Active',
                    'altitude': state[7] if state[7] is not None else "Unknown",
                    'speed': state[9] * 1.852 if state[9] else 0,  # Convert m/s to km/h
                    'last_update': datetime.fromtimestamp(state[3]).strftime('%Y-%m-%d %H:%M:%S'),
                    'callsign': callsign,
                    'origin_country': state[2] if state[2] else "Unknown"
                })
            
            # Sort flights by distance and return the closest ones
            flights.sort(key=lambda x: x['distance'])
            return flights[:num_flights]
        except requests.exceptions.RequestException as e:
            self.console.print(f"[red]Error fetching flight data: {str(e)}[/red]")
            return []

    def get_airline_name(self, callsign):
        """Map callsign to airline name (simplified example)"""
        # This is a simplified example. You can expand this with a more comprehensive mapping
        airline_map = {
            'UAL': 'United Airlines',
            'AAL': 'American Airlines',
            'DAL': 'Delta Air Lines',
            'SWA': 'Southwest Airlines',
            'RCH': 'Military - Air Force',
            'SAM': 'Military - Special Air Mission',
            'AF': 'Military - Air Force',
            'NAVY': 'Military - Navy',
            'ARMY': 'Military - Army'
        }
        prefix = callsign[:3]
        return airline_map.get(prefix, 'Unknown Airline')

    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points using the Haversine formula."""
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371  # Earth's radius in kilometers
        
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        distance = R * c
        
        return distance

    def build_table(self) -> Table:
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=3)
        table.add_column("Callsign")
        table.add_column("Country")
        table.add_column("Distance (km)")
        table.add_column("Altitude (m)")
        table.add_column("Speed (km/h)")
        for idx, flight in enumerate(self.flights):
            style = "on blue" if idx == self.selected_index else ""
            table.add_row(
                str(idx+1),
                flight.get('callsign', 'N/A'),
                flight.get('origin_country', 'N/A'),
                str(round(flight.get('distance', 1), 1)),
                str(flight.get('altitude', 'N/A')),
                str(round(flight.get('velocity', 0) * 3.6, 1) if flight.get('velocity') is not None else 'N/A'),
                style=style
            )
        return table

    def build_details_panel(self) -> Panel:
        if not self.flights:
            return Panel("No flight selected.", title="Flight Details")
        flight = self.flights[self.selected_index]
        details = f"""
[bold]Callsign:[/bold] {flight.get('callsign', 'N/A')}
[bold]Country:[/bold] {flight.get('origin_country', 'N/A')}
[bold]Distance:[/bold] {round(flight.get('distance', 1), 1)} km
[bold]Altitude:[/bold] {flight.get('altitude', 'N/A')} m
[bold]Speed:[/bold] {round(flight.get('velocity', 0) * 3.6, 1) if flight.get('velocity') is not None else 'N/A'} km/h
[bold]Latitude:[/bold] {flight.get('latitude', 'N/A')}
[bold]Longitude:[/bold] {flight.get('longitude', 'N/A')}
[bold]ICAO24:[/bold] {flight.get('icao24', 'N/A')}
"""
        return Panel(details, title="Flight Details", border_style="green")

    def display_flights(self, flights, selected_index=0):
        """Display flights in a table format with pagination"""
        if not flights:
            self.console.print("[yellow]No flights found in the specified area.[/yellow]")
            return

        page_size = 10  # Number of flights to display per page
        total_pages = (len(flights) + page_size - 1) // page_size
        current_page = selected_index // page_size

        start_idx = current_page * page_size
        end_idx = min(start_idx + page_size, len(flights))

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Flight", style="dim")
        table.add_column("Airline", style="dim")
        table.add_column("From", style="dim")
        table.add_column("To", style="dim")
        table.add_column("Distance", style="dim")
        table.add_column("Status", style="dim")
        table.add_column("Military", style="dim")  # New column for military status

        for i in range(start_idx, end_idx):
            flight = flights[i]
            style = "bold green" if i == selected_index else ""
            table.add_row(
                flight['flight_number'],
                flight.get('airline_name', 'N/A'),
                flight['departure_airport'],
                flight['arrival_airport'],
                f"{flight['distance']:.1f} km",
                flight['status'],
                'Yes' if flight.get('military', False) else 'No',  # Display military status
                style=style
            )

        self.console.print(table)
        self.console.print(f"\nPage {current_page + 1} of {total_pages}")
        self.console.print("\n[bold]Controls:[/bold]")
        self.console.print("↑/↓: Navigate  [r]efresh  [q]uit  [Enter]: Show details")

        if selected_index < len(flights):
            flight = flights[selected_index]
            self.console.print("\n[bold]Selected Flight Details:[/bold]")
            self.console.print(f"Flight: {flight['flight_number']}")
            self.console.print(f"Airline: {flight.get('airline_name', 'N/A')}")
            self.console.print(f"Military: {'Yes' if flight.get('military', False) else 'No'}")
            self.console.print(f"From: {flight['departure_airport']}")
            self.console.print(f"To: {flight['arrival_airport']}")
            self.console.print(f"Distance: {flight['distance']:.1f} km")
            self.console.print(f"Status: {flight['status']}")
            self.console.print(f"Altitude: {flight['altitude']} ft")
            self.console.print(f"Speed: {flight['speed']} km/h")
            self.console.print(f"Last Update: {flight['last_update']}")

    def run(self):
        """Main application loop."""
        self.console.print(Panel.fit(
            "[bold blue]Nearby Flights Tracker[/bold blue]\n"
            "Track flights within a specified radius of your location",
            title="Welcome"
        ))

        # Get user input
        address = self.console.input("Enter your address (e.g., '1600 Amphitheatre Parkway, Mountain View, CA'): ")
        self.latitude, self.longitude = self.get_coordinates(address)
        
        self.console.print(f"[green]Location coordinates: {self.latitude:.4f}, {self.longitude:.4f}[/green]")
        
        num_flights = int(self.console.input("Enter the number of closest flights to display (default 10): ") or "10")
        self.update_interval = int(self.console.input("Enter update interval in seconds (default 10): ") or "10")

        with Live(refresh_per_second=10, screen=True) as live:
            last_update = 0
            while True:
                now = time.time()
                if now - last_update > self.update_interval or not self.flights:
                    self.flights = self.get_nearby_flights(self.latitude, self.longitude, num_flights)
                    if self.selected_index >= len(self.flights):
                        self.selected_index = max(0, len(self.flights) - 1)
                    last_update = now
                layout = Layout()
                layout.split_column(
                    Layout(self.build_table(), name="table", ratio=2),
                    Layout(self.build_details_panel(), name="details", ratio=1)
                )
                live.update(layout)
                # Handle keyboard input (non-blocking)
                if self.flights:
                    key = readchar.readkey()
                    if key == readchar.key.UP:
                        self.selected_index = max(0, self.selected_index - 1)
                    elif key == readchar.key.DOWN:
                        self.selected_index = min(len(self.flights) - 1, self.selected_index + 1)
                    elif key == 'q':
                        break
                    elif key == 'r':
                        self.flights = self.get_nearby_flights(self.latitude, self.longitude, num_flights)
                        last_update = time.time()
                    elif key == 'd':  # Toggle display of flight details
                        self.show_details = not self.show_details
                else:
                    key = readchar.readkey()
                    if key == 'q':
                        break

if __name__ == "__main__":
    tracker = FlightTracker()
    tracker.run() 