import asyncio
from collections import defaultdict
from itertools import chain
import json
from pathlib import Path
from typing import Any, DefaultDict, Dict, List, Set

import jinja2
import analysis
from models import TheraputicLocations, load_updates


loader = jinja2.FileSystemLoader(searchpath="./templates")
temoplate_env = jinja2.Environment(loader=loader)
template = temoplate_env.get_template("data.html")

def data_vectors_js(vectors: List[Dict[str,Any]]) -> str:
    names:Set[str] = set()
    for m in vectors:
        names |= set(m.keys())

    columns = defaultdict(list)
    for m in vectors:
        for n in names:
            columns[n].append(m.get(n))
    return '\n'.join(f"const vector_{n} = {json.dumps(v)};" for n,v in columns.items())
    

async def write_date(locations: List[TheraputicLocations], dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    df = analysis.build_dataframe(await load_updates())
    data = analysis.to_summary_data(df, ["state_code", "county"])
    queue: List[analysis.SummaryData] = [data]
    vectors: List[Dict[str,Any]] = []
    while queue:
        next_item = queue.pop()
        output = json.loads(next_item.json(exclude={"children", "locations"}))
        output["children"] = {
            k: child_courses[-1]
            for k in sorted(next_item.children.keys())
            if (child_courses := list(next_item.children[k].courses_available.values()))
        }
        output["child_treatments"] = sorted(
            set(chain.from_iterable(x.keys() for x in output["children"].values()))
        )
        if next_item.locations:
            providers = {
                x.location_id: x.dict(
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
                for x in next_item.locations
            }
            treatments: DefaultDict[int, Dict[str, int]] = defaultdict(dict)
            for location in next_item.locations:
                treatments[location.location_id][location.order_label] = (
                    location.courses_available or 0
                )
                if location.courses_available:
                    vectors.append({'path': str(Path(*next_item.path)), **location.dict(include={"lat","lng","provider_name","location_id"})})
            output["providers"] = providers
            output["treatments"] = treatments

        output_path = dest / Path(*next_item.path)
        output_path.mkdir(parents=True, exist_ok=True)
        (output_path / "data.json").write_text(json.dumps(output))
        (output_path / "index.html").write_text(template.render(output))
        queue.extend(list(next_item.children.values()))
    (dest / "data_vectors.json").write_text(data_vectors_js(vectors))


async def main() -> None:
    locations = await load_updates()
    await write_date(locations, Path("data"))


if __name__ == "__main__":
    asyncio.run(main())
