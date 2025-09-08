import requests
import json

class DataMartClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = 'https://api.datamartgh.shop/api/developer'
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
        response = requests.post(url, json=payload, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def get_order_status(self, order_id):
        """Check the status of an order by its ID."""
        url = f"{self.base_url}/order/{order_id}"  # 👈 confirm endpoint
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        data = response.json()

        # Extract nested status safely
        try:
            return data["data"]["apiResponse"]["data"]["status"]
        except KeyError:
            return None
