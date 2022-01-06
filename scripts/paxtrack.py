import asyncio
import json
from pathlib import Path
from typing import List

import analysis
from models import TheraputicLocations, load_updates


async def write_date(locations: List[TheraputicLocations], dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    df = analysis.build_dataframe(await load_updates())
    data = analysis.to_summary_data(df, ['state_code', 'county'])
    queue: List[analysis.SummaryData] = [data]
    while queue:
        next_item = queue.pop()
        output = json.loads(next_item.json(exclude={'children'}))
        output['children'] = list(next_item.children.keys())
        output_path = dest / Path(*next_item.path)
        output_path.mkdir(parents=True, exist_ok=True)
        (output_path / 'data.json').write_text(json.dumps(output))
        queue.extend(list(next_item.children.values()))
    

async def main() -> None:
    locations = await load_updates()
    await write_date(locations, Path('data'))

if __name__ == "__main__":
    asyncio.run(main())