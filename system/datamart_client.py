import requests
import json

class DataMartClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = 'https://datamartbackened.onrender.com/api/developer'
        self.headers = {
            'Content-Type': 'application/json',
            'X-API-Key': api_key
        }
    
    def purchase_data(self, phone_number, network, capacity):
        """Purchase a data bundle for the specified phone number."""
        url = f"{self.base_url}/purchase"
        payload = {
            'phoneNumber': phone_number,
            'network': network,
            'capacity': capacity,
            'gateway': 'wallet'
        }

        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            print(f"Response Status: {response.status_code}")
            print(f"Response Text: {response.text}")

            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            print("❌ HTTP Error Occurred!")
            print(f"Status: {response.status_code}")
            print(f"Body: {response.text}")
            raise
