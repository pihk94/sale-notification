"""A script to retrieve favorites items from interencheres
and send what's app notification"""
from datetime import datetime, timedelta
import os

import pandas as pd
import requests


# PARAMS
TWILIO_USERNAME = os.getenv("TWILIO_USERNAME")
TWILIO_PASSWORD = os.getenv("TWILIO_PASSWORD")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_NUMBER")
TWILIO_BASE_URL = "https://api.twilio.com/2010-04-01/Accounts/"
TWILIO_ENDPOINT = TWILIO_BASE_URL + f'{TWILIO_USERNAME}/Messages.json'
TO_NUMBER = os.getenv("TO_NUMBER")
COLUMNS = [
    'item.itemUrl',
    'item.saleUrl',
    'item.sale.datetime',
    'item.description',
    'item.pricing.estimates.max',
    'item.pricing.estimates.min',
    'item.sale.name',
    'item.meta.order_number.primary']
INTERENCHERES_ENDPOINT = 'https://graph.prod-indb.io/graphql'
INTERENCHERES_HEADERS = {
    "authority": "graph.prod-indb.io",
    "scheme": "https",
    "path": "/graphql",
    "accept": "application/json, text/plain, */*",
    "jwt": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJtam9sbG5pci1mcm9udC1tYWluLTA2LnByb2QuaW5kYi5pbyIsInN1YiI6ImVlNjVkNGNmLWIyODUtNDFjYS04OWVhLTU0YjYwYTYxYjgyNiIsInN1YmxpdmUiOiIxMjQ4ODYiLCJpYXQiOjE2MTUwMjAyMjcsImV4cCI6MTYxNzYxMjIyN30.2J3WYS6EoNhrrhqeE5rWLry0lqDBfyBINEWjvk3bz9w", # noqa
    "origin": "https://www.interencheres.com",
    "sec-fetch-site": "cross-site",
    "sec-fetch-mode": "cors",
    "sec-fetch-dest": "empty",
    "referer": "https://www.interencheres.com/",
    "accept-encoding": "gzip, deflate, br",
    "accept-language": "en-US,en;q=0.9,fr;q=0.8"
}
INTERENCHERES_FIELDS = """
    {
        item
            {id itemUrl saleUrl medias meta pricing description
            organization {   id   names   address }
            category {   name   field   summary   description }
            sale {   id   meta   states   name   datetime   address   contact }
            mailtoParams dateCountdown}
    }"""
INTERENCHERES_PAYLOAD = {
    "query": "{Selections(user_id : \"ee65d4cf-b285-41ca-89ea-54b60a61b826\")"
    + INTERENCHERES_FIELDS + "}"
    }

# Get interencheres favorites items
r = requests.post(
    INTERENCHERES_ENDPOINT,
    headers=INTERENCHERES_HEADERS,
    json=INTERENCHERES_PAYLOAD)
df = pd.json_normalize(r.json()['data']['Selections'])
assert df.shape[0] > 0

# Select the next hour sales
start = datetime.now().replace(minute=0, second=0, microsecond=0)
end = start + timedelta(hour=1)

df = df[COLUMNS].sort_values('item.sale.datetime')
df['item.sale.datetime'] = pd.to_datetime(
    df['item.sale.datetime'].apply(lambda x: x[:-6])
)
df = df[
    (df['item.sale.datetime'] >= start) &
    (df['item.sale.datetime'] < start + timedelta(hours=1))]

for vente in df['item.saleUrl'].unique():
    sub = df[df['item.saleUrl'] == vente]
    hour = pd.Timestamp(sub['item.sale.datetime'].values[0]).hour
    sale_name = sub['item.sale.name'].values[0]
    lots = sub['item.meta.order_number.primary'].values
    lots.sort()
    body = f"""*{sale_name} à {hour} H*
{vente}
*Objets suivis:* {sub.shape[0]}
*Lots:* {", ".join([str(int(l)) for l in lots])}
    """
    payloads = {
        'From': f'whatsapp:{TWILIO_FROM_NUMBER}',
        'To': f'whatsapp:{TO_NUMBER}',
        'Body': body
    }
    r = requests.post(
        TWILIO_ENDPOINT,
        data=payloads,
        auth=(TWILIO_USERNAME, TWILIO_PASSWORD)
    )
