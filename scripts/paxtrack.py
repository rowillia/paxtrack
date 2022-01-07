import asyncio
from collections import defaultdict
import json
from pathlib import Path
from typing import List

import jinja2
import analysis
from models import TheraputicLocations, load_updates


loader = jinja2.FileSystemLoader(searchpath="./templates")
temoplate_env = jinja2.Environment(loader=loader)
template = temoplate_env.get_template('data.html')


async def write_date(locations: List[TheraputicLocations], dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    df = analysis.build_dataframe(await load_updates())
    data = analysis.to_summary_data(df, ['state_code', 'county'])
    queue: List[analysis.SummaryData] = [data]
    while queue:
        next_item = queue.pop()
        output = json.loads(next_item.json(exclude={'children', 'locations'}))
        output['children'] = list(next_item.children.keys())
        if next_item.locations:
            providers = {x.place_id: x.dict(include={'provider_name', 'address1', 'address2', 'state_code', 'city', 'zip_code', 'county', 'lat', 'lng', 'place_id', 'order_label'}) for x in next_item.locations}
            treatments = defaultdict(dict)
            for location in next_item.locations:
                treatments[location.place_id][location.order_label] = location.courses_available
            output['providers'] = providers
            output['treatments'] = treatments

        output_path = dest / Path(*next_item.path)
        output_path.mkdir(parents=True, exist_ok=True)
        (output_path / 'data.json').write_text(json.dumps(output))
        (output_path / 'index.html').write_text(template.render(output))
        queue.extend(list(next_item.children.values()))
    

async def main() -> None:
    locations = await load_updates()
    await write_date(locations, Path('data'))

if __name__ == "__main__":
    asyncio.run(main())