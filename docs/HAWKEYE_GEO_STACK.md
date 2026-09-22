# Hawkeye Geo Stack

Hawkeye uses a provider-neutral geospatial engine.

## Analytical/offline foundation
- OpenStreetMap data for roads/buildings/features, with attribution and a compliant/self-hosted tile pipeline.
- MapLibre Native for mobile rendering.
- PMTiles for local vector/raster/DEM field packs.
- CesiumJS / 3D Tiles for PC 3D Earth and survey visualization.
- OpenDroneMap/NodeODM for local photogrammetry, orthophotos, DEMs, point clouds and meshes.
- KartaView for available street-level imagery.
- Bhuvan/Bhoonidhi adapters for India EO/thematic data where dataset/service terms permit.

## Optional Google visualization
Google Maps, Street View and Photorealistic 3D Tiles are optional licensed visualization adapters. Hawkeye must not cache Google content into offline Field Packs or use it as machine-analysis/training input unless the applicable Google terms explicitly permit that use.

## Unified modes
MAP, SATELLITE, STREET, TERRAIN, 3D_EARTH, 3D_SURVEY, AR, HISTORY.

All analytical outputs retain provenance and MEASURED / OBSERVED / INFERRED / PREDICTED / UNKNOWN evidence state.
