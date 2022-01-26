import * as ReactLeaflet from "react-leaflet";
import L from "leaflet";
import { useEffect, useState } from "react";
import { TileJSONMarkers } from "./geojson";
import MarkerClusterGroup from "react-leaflet-markercluster";

import type { LatLngExpression } from "leaflet";

import "leaflet/dist/leaflet.css";
import "react-leaflet-markercluster/dist/styles.min.css";

const DEFAULT_CENTER: LatLngExpression = [38.907132, -77.036546];
const DEFAULT_ZOOM = 15;

const { MapContainer, TileLayer, CircleMarker, useMapEvent } = ReactLeaflet;

const LocationMarker = () => {
  const [loc, setLoc] = useState(null);
  useMapEvent("locationfound", setLoc);
  return loc === null ? null : (
    <CircleMarker
      center={[loc.latlng.lat, loc.latlng.lng]}
      pathOptions={{
        color: "red",
        fill: true,
        fillColor: "red",
        fillOpacity: 0.5,
      }}
    />
  );
};

const OSMBaseLayer = () => {
  return (
    <TileLayer
      url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      attribution='&copy; <a href="htttp://osm.org/copyright">OpenStreetMap</a> contributors'
    />
  );
};

function Map({
  children,
  ...rest
}: React.ComponentProps<typeof MapContainer>): JSX.Element {
  useEffect(() => {
    delete L.Icon.Default.prototype._getIconUrl;
    L.Icon.Default.mergeOptions({
      iconRetinaUrl: require("leaflet/dist/images/marker-icon-2x.png").default
        .src,
      iconUrl: require("leaflet/dist/images/marker-icon.png").default.src,
      shadowUrl: require("leaflet/dist/images/marker-shadow.png").default.src,
    });
  }, []);

  return (
    <MapContainer
      zoom={DEFAULT_ZOOM}
      center={DEFAULT_CENTER}
      style={{ width: "100%", minHeight: "100vh" }}
      whenCreated={(map) => {
        map.locate({
          setView: true,
          enableHighAccuracy: true,
          maxZoom: DEFAULT_ZOOM,
        });
      }}
      {...rest}
    >
      <OSMBaseLayer />
      <LocationMarker />
      <MarkerClusterGroup>
        <TileJSONMarkers url="/data/geojson_data.json" />
      </MarkerClusterGroup>
      {children}
    </MapContainer>
  );
}

export default Map;
