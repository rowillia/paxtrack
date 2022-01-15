import asyncio
from collections import defaultdict
from itertools import chain
import json
from pathlib import Path
from typing import DefaultDict, Dict, List

import jinja2
import geojson
import tqdm
from icecream import ic
import analysis
from models import TheraputicLocations, load_updates


loader = jinja2.FileSystemLoader(searchpath="./templates")
temoplate_env = jinja2.Environment(loader=loader)
template = temoplate_env.get_template("data.html")


async def write_data(locations: List[TheraputicLocations], dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    ic("Building data")
    df = analysis.build_dataframe(await load_updates())
    ic("Summary data")
    data = analysis.to_summary_data(df, ["state_code", "county"])
    geojson_features: Dict[int, geojson.Feature] = {}
    queue: List[analysis.SummaryData] = [data]
    with tqdm.tqdm(total=1, desc="Writing json & html") as pbar:
        while queue:
            next_item = queue.pop()
            output = json.loads(next_item.json(exclude={"children", "locations"}))
            output["children"] = {
                k: child_courses[-1]
                for k in sorted(next_item.children.keys())
                if (
                    child_courses := list(
                        next_item.children[k].courses_available.values()
                    )
                )
            }
            output["child_treatments"] = sorted(
                set(chain.from_iterable(x.keys() for x in output["children"].values()))
            )
            if next_item.locations:
                treatments: DefaultDict[int, Dict[str, int]] = defaultdict(dict)
                providers: Dict[int, Dict] = {}
                for location in next_item.locations:
                    providers[location.location_id] = location.dict(
                        include={
                            "provider_name",
                            "address1",
                            "address2",
                            "state_code",
                            "city",
                            "zip_code",
                            "county",
                            "lat",
                            "lng",
                            "order_label",
                        }
                    )
                    geojson_features[location.location_id] = geojson.Feature(
                        geometry=geojson.Point(
                            [
                                providers[location.location_id]["lng"],
                                providers[location.location_id]["lat"],
                            ]
                        ),
                        properties=providers[location.location_id],
                        id=location.location_id,
                    )
                    treatments[location.location_id][location.order_label] = (
                        location.courses_available or 0
                    )
                    output["providers"] = providers
                    output["treatments"] = treatments

            output_path = dest / Path(*next_item.path)
            output_path.mkdir(parents=True, exist_ok=True)
            (output_path / "data.json").write_text(json.dumps(output))
            (output_path / "index.html").write_text(template.render(output))
            children = list(next_item.children.values())
            queue.extend(children)
            if len(children):
                pbar.reset(len(queue))

    ic("Writing geojson", len(geojson_features))
    (dest / "data.geojson").write_text(
        geojson.dumps(
            geojson.FeatureCollection(list(geojson_features.values())), sort_keys=True
        )
    )


async def main() -> None:
    ic("Loading updates")
    locations = await load_updates()
    await write_data(locations, Path("data"))


if __name__ == "__main__":
    asyncio.run(main())
