import type { Feature, Geometry } from "geojson";
import classnames from "classnames";

type ProviderProperties = {
  address1: string;
  address2: string | null;
  city: string;
  county: string;
  zip_code: string;
  state_code: string;
  lat: number;
  lng: number;
  provider_name: string;
  treatments: { [treatment_name: string]: number };
};

const MiddotList = ({ children, className, ...rest }) => {
  return (
    <div className={classnames(className, "flex flex-row")}>
      {children
        .map((item, i) => [
          item,
          <span key={`${i}-middot`} className="p-[2px]">
            &middot;
          </span>,
        ])
        .flat(1)
        .slice(0, -1)}
    </div>
  );
};

export default ({ data }: { data: Feature<Geometry, ProviderProperties> }) => {
  const { geometry, id, properties } = data;

  const treatments = (
    <ul className="list-none">
      {Object.entries(properties.treatments).map(([n, c]) => (
        <li key={n} className="whitespace-nowrap">
          {n} ({c})
        </li>
      ))}
    </ul>
  );

  const searchAddress = [
    properties.address1,
    properties.city,
    `${properties.state_code} ${properties.zip_code}`,
  ]
    .filter((i) => i !== null)
    .join(", ");

  const gmapsLink = (
    <a
      href={`https://www.google.com/maps/search/?api=1&query=${searchAddress}`}
      target="_blank"
    >
      {searchAddress}
    </a>
  );

  return (
    <div className="p-2 divide-solid divide-y-2 flex flex-col">
      <div className="text-xl pb-2">{properties.provider_name}</div>
      <div className="text-base text-lime-800 py-2">{treatments}</div>
      <div className="text-sm flex flex-col pt-2">
        {properties.address2 === null ? "" : properties.address2}
        {gmapsLink}
      </div>
    </div>
  );
};
