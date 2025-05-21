from fastapi import Depends, FastAPI, HTTPException, Query, APIRouter, Response, Request
from fastapi.responses import StreamingResponse
import pandas as pd
import geopandas as gpd
import transit_service_analyst as tsa
from pathlib import Path
import json

app = FastAPI()

path = "./gtfs_data"
transit_analyst = tsa.load_gtfs(path, "20250114")

# routes
routes = transit_analyst.get_lines_gdf()
routes_cols = [
    "rep_trip_id",
    "route_id",
    "trip_headsign",
    "route_short_name",
    "route_long_name",
    "route_type",
    "direction_id",
    "ct_cardinal_direction",
]

# routes_stops
routes_stops = transit_analyst.get_line_stops_gdf()
routes_stops = routes_stops[
    [
        "rep_trip_id",
        "trip_id",
        "stop_id",
        "stop_sequence",
        "stop_name",
        "stop_lat",
        "stop_lon",
    ]
]
# create an id column for routes and routes_stops
routes["id"] = (
    routes["route_id"].astype(str) + "_" + routes["ct_cardinal_direction"].astype(str)
)
routes_stops = routes_stops.merge(
    routes[["rep_trip_id", "id"]], on="rep_trip_id", how="left"
)

# get rid of any duplicate routes
routes = routes.groupby(["id"]).first().reset_index()
routes.set_index("id", inplace=True)

# create dictionaries to store end point data
routes_geo_dict = routes["geometry"].to_dict()
routes_dict = routes[routes_cols].to_dict(orient="index")

# create a dictionary to store the stops for each route
routes_stops_dict = (
    routes_stops.groupby("id")
    .apply(
        lambda df: df[
            ["stop_id", "stop_name", "stop_sequence", "stop_lat", "stop_lon"]
        ].to_dict(orient="records")
    )
    .to_dict()
)

# add point and line geometry to the routes_dict
for id in routes_dict.keys():
    a = routes[routes.index == id]
    a = a.to_geo_dict(show_bbox=True)
    routes_dict[id]["bbox"] = a["features"][0]["bbox"]
    routes_dict[id]["geometry"] = a["features"][0]["geometry"]
    routes_dict[id]["stops"] = routes_stops_dict.get(id)


# endpoint to get all routes
@app.get("/route_ids")
def get_route_ids():
    """
    Get route information by id
    """
    return list(routes_dict.keys())


# endpoint to individual route and stops
@app.get("/route")
def get_route(id: str, include_route_geometry: bool = False):
    """
    Get route information by id
    """
    if id not in routes_dict:
        raise HTTPException(status_code=404, detail="Route not found")
    elif include_route_geometry:
        route = routes_dict[id]
    else:
        route = routes_dict[id].copy()
        route.pop("geometry", None)
        route.pop("bbox", None)
    return route
