from __future__ import annotations

import asyncio
import os
import re
from collections import defaultdict
from csv import DictReader
from datetime import datetime, date
from io import StringIO
from pathlib import Path
from operator import attrgetter
from typing import Any, Dict, List, Tuple

import httpx
import tqdm
from pandas._libs.tslibs.timestamps import Timestamp
from pydantic import BaseModel, validator, root_validator
from pydantic.fields import Field

from geocoder import CachingGeocoder, Geocoder

ARCHIVE_URL = os.getenv("ARCHIVE_URL", "https://healthdata.gov/resource/j7fh-jg79.json")
CACHE_DIR = Path(".cache")
GEOCODE_ADDRESS_RE = re.compile(r"POINT\s+\((-?\d+\.?\d*)\s+(-?\d+\.?\d*)\)")
MIN_DATE = date(2022, 1, 5)


def to_word(string: str) -> str:
    return " ".join(word.capitalize() for word in string.split("_"))


class Link(BaseModel):
    url: str


address_to_location_id: Dict[Tuple[str, str, str | None, str], int] = {}
next_id = 0


class TheraputicLocation(BaseModel):
    provider_name: str
    address1: str
    address2: str | None
    city: str
    county: str | None
    state_code: str
    zip_code: str = Field(alias="Zip")
    lat: float | None
    lng: float | None
    national_drug_code: str
    order_label: str
    last_order_date: datetime | None
    last_delivered_date: datetime | None
    total_courses: int | None
    courses_available: int | None
    courses_available_date: datetime | None

    @property
    def location_id(self) -> int:
        global next_id
        key = (self.provider_name, self.address1, self.address2, self.zip_code)
        if key not in address_to_location_id:
            address_to_location_id[key] = next_id
            next_id += 1
        return address_to_location_id[key]

    @root_validator(pre=True)
    def parse_point(cls, values: Dict[str, Any]) -> None:
        if match := GEOCODE_ADDRESS_RE.match(values.get("Geocoded Address", "")):
            lng, lat = (float(x) for x in match.groups())
            values["lat"] = lat
            values["lng"] = lng
        return values

    async def geocode(self, geocoder: CachingGeocoder) -> None:
        if self.lat is None or self.lng is None:
            location = await geocoder.get_location(
                address1=self.address1,
                address2=self.address2,
                city=self.city,
                state_code=self.state_code,
                zip_code=self.zip_code,
            )
            if location:
                self.lat = location.lat
                self.lng = location.lng

    @validator("*", pre=True)
    def empty_str_to_none(cls, v: str) -> str | None:
        if v == "":
            return None
        return v

    @validator(
        "last_order_date", "last_delivered_date", "courses_available_date", pre=True
    )
    def parse_theraputic_datetime(cls, value: str | Timestamp) -> datetime | None:
        if isinstance(value, Timestamp):
            return value.to_pydatetime()
        if value:
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return datetime.strptime(value, "%m/%d/%Y %I:%M:%S %p")
        return None

    @validator("provider_name", "address1", "address2", "city", "county", pre=True)
    def normalize(cls, value: str) -> str | None:
        if value:
            return " ".join(word.capitalize() for word in value.split())
        return None

    class Config:
        alias_generator = to_word
        allow_population_by_field_name = True


class TheraputicLocations(BaseModel):
    update_time: datetime
    locations: List[TheraputicLocation]

    async def geocode(self, geocoder: CachingGeocoder, batch_size: int = 10) -> None:
        for i in tqdm.trange(0, len(self.locations), batch_size, desc="Geocoder"):
            await asyncio.gather(
                *[
                    location.geocode(geocoder)
                    for location in self.locations[i : i + batch_size]
                ]
            )


class ArchiveUpdate(BaseModel):
    update_date: datetime
    user: str
    rows: int
    row_change: int
    columns: int
    column_change: int
    metadata_published: str
    metadata_updates: str
    column_level_metadata: str
    column_level_metadata_updates: str
    archive_link: Link

    async def theraputic_locations(
        self, client: httpx.AsyncClient
    ) -> TheraputicLocations:
        locations = list(
            DictReader(StringIO((await client.get(self.archive_link.url)).text))
        )
        return TheraputicLocations(update_time=self.update_date, locations=locations)

    @property
    def path(self) -> Path:
        return Path(self.update_date.strftime("%Y_%m_%d_%H_%M_%S") + ".json")


class Archive(BaseModel):
    updates: List[ArchiveUpdate]

    @classmethod
    async def fetch(cls, client: httpx.AsyncClient) -> Archive:
        return Archive(updates=(await client.get(ARCHIVE_URL)).json())


async def load_updates() -> List[TheraputicLocations]:
    updates_by_date: Dict[date, List[TheraputicLocations]] = defaultdict(list)
    async with httpx.AsyncClient() as client:
        with Geocoder(client) as geocoder:
            archive = await Archive.fetch(client)
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            for update in archive.updates:
                if update.update_date.date() < MIN_DATE:
                    continue
                cached_update = CACHE_DIR / update.path
                if not cached_update.exists():
                    locations = await update.theraputic_locations(client)
                    await locations.geocode(geocoder)
                    cached_update.write_text(
                        locations.json(exclude_none=True, by_alias=True)
                    )
                else:
                    locations = TheraputicLocations.parse_file(cached_update)
                updates_by_date[update.update_date.date()].append(locations)
    result = [
        max(locs, key=attrgetter("update_time")) for locs in updates_by_date.values()
    ]
    return result
