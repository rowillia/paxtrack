from __future__ import annotations


from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
from pydantic.class_validators import validator
from pydantic.main import BaseModel

from models import TheraputicLocation, TheraputicLocations


MAX_LOCATIONS = 10


class SummaryData(BaseModel):
    path: List[str]
    children: Dict[str, SummaryData]
    total_courses: Dict[str, Dict[str, int]]
    courses_delivered: Dict[str, Dict[str, int]]
    courses_available: Dict[str, Dict[str, int]]
    locations: List[TheraputicLocation] | None

    @validator("total_courses", "courses_delivered", "courses_available", pre=True)
    def from_dataframe(cls, series: pd.Series) -> Dict[str, Dict[str, int]]:
        result = {}
        for k, v in series.to_dict().items():
            result.setdefault(k[0].strftime("%Y/%m/%d"), {})[k[1]] = v
        return result


def courses_delivered(row: TheraputicLocation) -> int:
    if row.total_courses is None:
        return None
    if row.courses_available is None:
        return 0
    return max(0, row.total_courses - row.courses_available)


def build_dataframe(locations: List[TheraputicLocations]) -> pd.DataFrame:
    updates = [
        pd.DataFrame(
            [loc.dict() | {"update_date": l.update_time.date()} for loc in l.locations]
        )
        for l in locations
    ]
    df = pd.concat(updates)

    df["courses_delivered"] = df.apply(courses_delivered, axis=1)

    return df


def to_summary_data(
    df: pd.DataFrame, dimensions: List[str], path: List[str] | None = None
) -> SummaryData:
    path = path or []
    grouped = df.groupby(["update_date", "order_label"])
    total_courses = grouped["total_courses"].sum()
    courses_delivered = grouped["courses_delivered"].sum()
    courses_available = grouped["courses_available"].sum()
    locations = None
    latest_date = df["update_date"].max()
    locs = (
        df.query("update_date == @latest_date and courses_available")
        .fillna(value=np.nan)
        .replace({np.nan: None})
        .to_dict("index")
    )
    if len(locs) < MAX_LOCATIONS or not dimensions:
        locations = [TheraputicLocation(**l) for l in locs.values()]
    children = {}
    if dimensions:
        next_dimension, *remaining_dimensions = dimensions
        for child in  list(set(df[next_dimension])):
            child = child or "UNKNOWN"
            children[child] = to_summary_data(df[df[next_dimension] == child], remaining_dimensions, path + [child])
    return SummaryData(
        path=path,
        total_courses=total_courses,
        courses_delivered=courses_delivered,
        courses_available=courses_available,
        children=children,
        locations=locations,
    )