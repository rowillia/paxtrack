import * as ReactLeaflet from "react-leaflet";
import L from "leaflet";
import { useState } from "react";

import { useFetch } from "react-async";
import ReactDOMServer from "react-dom/server";
import ProviderPopupContent from "./ProviderPopupContent";
import type { ProviderProperties } from "./ProviderPopupContent";
import geojsonvt, { GeoJSONVT } from "geojson-vt";

import type { Geometry, GeoJsonObject } from "geojson";

const { GeoJSON, useMap, useMapEvent, Marker, Popup } = ReactLeaflet;

export const GeoJSONMarkers = ({ url }) => {
  // Less performant version: load all markers into GeoJSON layer. Replaced with TileJSONMarkers.
  const { data } = useFetch(url, {}, { json: true });

  const onEachFeature = (feature, layer) => {
    layer.bindPopup(
      ReactDOMServer.renderToString(
        <ProviderPopupContent properties={feature.properties} />
      )
    );
  };

  // TODO: use isPending/error states
  if (data) {
    return <GeoJSON data={data} onEachFeature={onEachFeature} />;
  } else {
    return null;
  }
};

// This only works with 256 (ie tilesize of map tiles) for some reason --
// unclear exactly why
const TILE_EXTENT = 256;

const getTileIdx = (
  pxy: L.Point,
  tileExtent: number = TILE_EXTENT
): [number, number] => [
  Math.floor(pxy.x / tileExtent),
  Math.floor(pxy.y / tileExtent),
];

const indexGeoJSON = (data: GeoJsonObject): GeoJSONVT => {
  const idx = geojsonvt(data, {
    maxZoom: 18,
    indexMaxZoom: 5,
    tolerance: 0,
    extent: TILE_EXTENT,
    buffer: 64,
    debug: 0,
    indexMaxPoints: 10000,
  });
  return idx;
};

type MapPosition = {
  zoom: number;
  center: L.LatLng;
  pixelCenter: L.Point;
  pixelBounds: L.Bounds;
};

const getBBoxTilesXY = (pos: MapPosition): [number, number][] => {
  const ul: L.Point = pos.pixelBounds.getTopLeft();
  const br: L.Point = pos.pixelBounds.getBottomRight();

  const [x0, y0] = [...getTileIdx(ul)];
  const [x1, y1] = [...getTileIdx(br)];
  const tilesXY = [];
  for (let x = x0; x <= x1; x++) {
    for (let y = y0; y <= y1; y++) {
      tilesXY.push([x, y]);
    }
  }
  return tilesXY;
};

type TileFeature = {
  geometry: Geometry;
  tags: ProviderProperties;
  id: number;
};

const mergeFeatures = (
  tilesXY: [number, number][],
  index: GeoJSONVT,
  zoom: number
): TileFeature[] => {
  const tiles = tilesXY.map(([x, y]) => index.getTile(zoom, x, y));
  const features: TileFeature[] = tiles
    .flatMap((tile) => tile?.features)
    .filter((x) => x != null);
  const featuresById = Object.fromEntries(
    features.map((f: TileFeature): [number, TileFeature] => [f.id, f])
  );
  return Object.values(featuresById);
};

export const TileJSONMarkers = ({ url }) => {
  // More performant version of GeoJSONMarkers: we create an index of the
  // markers and load all tiles within the bounding box of the view.

  const { data }: { data: GeoJsonObject } = useFetch(url, {}, { json: true });

  const [index, setIndex] = useState(null);
  const [pos, setPos] = useState<MapPosition | null>(null);
  const map = useMap();
  const onMoveMap = () => {
    const center = map.getCenter();
    const zoom = map.getZoom();
    setPos({
      zoom,
      center,
      pixelCenter: map.project([center.lat, center.lng], zoom),
      pixelBounds: map.getPixelBounds(),
    });
  };

  // - viewreset: fires at setView (only onload)
  // - zoomend: fires on zoom
  // - moveend: fires on setview, zoom, pan <--- we'll use this
  useMapEvent("moveend", onMoveMap);

  if (data == null) {
    return null;
  } else if (index === null) {
    setIndex(indexGeoJSON(data));
  }

  if (pos !== null && index !== null) {
    const tilesXY = getBBoxTilesXY(pos);
    const features = mergeFeatures(tilesXY, index, pos.zoom);
    const markers = features.map((f) => (
      <Marker position={[f.tags.lat, f.tags.lng]} key={f.id}>
        <Popup>
          <ProviderPopupContent properties={f.tags} />
        </Popup>
      </Marker>
    ));
    return <>{markers}</>;
  }
  return null;
};
