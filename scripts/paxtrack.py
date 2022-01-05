from __future__ import annotations

import asyncio
import os
from csv import DictReader
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import List

import httpx
from pydantic import BaseModel, validator
from pydantic.fields import Field

from geocoder import CachingGeocoder, Geocoder, Location

ARCHIVE_URL = os.getenv("ARCHIVE_URL", "https://healthdata.gov/resource/j7fh-jg79.json")


def to_word(string: str) -> str:
    return " ".join(word.capitalize() for word in string.split("_"))


class Link(BaseModel):
    url: str


class TheraputicLocation(BaseModel):
    provider_name: str
    address1: str
    address2: str | None
    city: str
    county: str | None
    state_code: str
    zip_code: str = Field(alias="Zip")
    location: Location | None
    national_drug_code: str
    order_label: str
    last_order_date: datetime | None
    last_delivered_date: datetime | None
    total_courses: int | None
    courses_available: int | None
    courses_available_date: datetime | None

    async def geocode(self, geocoder: CachingGeocoder) -> None:
        self.location = await geocoder.get_location(
            address1=self.address1,
            address2=self.address2,
            city=self.city,
            state_code=self.state_code,
            zip_code=self.zip_code,
        )

    @validator("*", pre=True)
    def empty_str_to_none(cls, v):
        if v == "":
            return None
        return v

    @validator(
        "last_order_date", "last_delivered_date", "courses_available_date", pre=True
    )
    def parse_theraputic_datetime(cls, value: str) -> datetime | None:
        if value:
            return datetime.strptime(value, "%m/%d/%Y %I:%M:%S %p")
        return None

    @validator("provider_name", "address1", "address2", "city", "county", pre=True)
    def normalize(cls, value: str) -> str | None:
        if value:
            return " ".join(word.capitalize() for word in value.split())
        return None

    class Config:
        alias_generator = to_word


class TheraputicLocations(BaseModel):
    locations: List[TheraputicLocation]

    async def geocode(self, geocoder: CachingGeocoder, batch_size: int = 10):
        for i in range(0, len(self.locations), batch_size):
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

    async def theraputic_locations(self, client: httpx.AsyncClient):
        locations = list(
            DictReader(StringIO((await client.get(self.archive_link.url)).text))
        )
        return TheraputicLocations(locations=locations)

    @property
    def path(self) -> Path:
        return Path(self.update_date.strftime("%Y_%m_%d_%H_%M_%S") + ".json")


class Archive(BaseModel):
    updates: List[ArchiveUpdate]

    @classmethod
    async def fetch(cls, client: httpx.AsyncClient) -> Archive:
        return Archive(updates=(await client.get(ARCHIVE_URL)).json())


async def main():
    async with httpx.AsyncClient() as client:
        with Geocoder(client) as geocoder:
            archive = await Archive.fetch(client)
            for update in archive.updates:
                if not update.path.exists():
                    locations = await update.theraputic_locations(client)
                    await locations.geocode(geocoder)
                    update.path.write_text(locations.json(exclude_none=True))
                
                


asyncio.run(main())
