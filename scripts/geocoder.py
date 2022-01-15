from __future__ import annotations

from contextlib import contextmanager
import json
import os
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterator

import httpx
from pydantic.main import BaseModel
import geojson
import random
import string
from icecream import ic

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_GEOCODE_BASE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
CACHE_FILE = Path(".cache", "geocoder.json")


ALPHABET = string.ascii_lowercase + string.digits


def random_id() -> str:
    return "".join(random.choices(ALPHABET, k=8))


class Location(BaseModel):
    lat: float
    lng: float
    place_id: str

    @classmethod
    def get_random(cls) -> Location:
        rand_point = geojson.utils.generate_random("Point")
        return Location(
            lat=rand_point.coordinates[0],
            lng=rand_point.coordinates[1],
            place_id=f"random_{random_id()}",
        )


@dataclass
class CachingGeocoder:
    client: httpx.AsyncClient
    _cache: Dict[str, str] = field(default_factory=dict)

    async def get_location(
        self,
        address1: str,
        address2: str | None,
        city: str,
        state_code: str,
        zip_code: str,
    ) -> Location | None:
        if not GOOGLE_API_KEY:
            return Location.get_random()

        params = (
            (
                "address",
                f"{address1}{', ' + address2 if address2 else ''}, {city}, {state_code} {zip_code}",
            ),
        )
        cache_key = urllib.parse.urlencode(params)

        if cache_key not in self._cache:
            query_params = params + (("key", GOOGLE_API_KEY),)
            self._cache[cache_key] = (
                await self.client.get(GOOGLE_GEOCODE_BASE_URL, params=query_params)
            ).text
        response = self._cache[cache_key]
        data = json.loads(response)

        if data["status"] == "OK":
            result = data["results"][0]
            location = result["geometry"]["location"]
            return Location(
                lat=location["lat"], lng=location["lng"], place_id=result["place_id"]
            )
        else:
            return None


@contextmanager
def Geocoder(client: httpx.AsyncClient) -> Iterator[CachingGeocoder]:
    saved_cache: Dict[str, str] = {}
    if CACHE_FILE.exists():
        saved_cache = json.loads(CACHE_FILE.read_text())
    yield CachingGeocoder(client, saved_cache)
    CACHE_FILE.parents[0].mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(saved_cache))
