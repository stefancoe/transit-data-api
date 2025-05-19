from fastapi import Depends, FastAPI, HTTPException, Query, APIRouter, Response, Request
from fastapi.responses import StreamingResponse
import pandas as pd
import geopandas as gpd
import transit_service_analyst as tsa
#import openpyxl
#from openpyxl.utils.dataframe import dataframe_to_rows
from pathlib import Path

app = FastAPI()

#path = r"C:\Users\scoe\Puget Sound Regional Council\GIS - Sharing\Projects\Transportation\RTP_2026\transit\GTFS\2024\CT"
path = "./gtfs_data"
transit_analyst = tsa.load_gtfs(path, "20250114")



# routes
routes = transit_analyst.get_lines_gdf()
routes = routes[
    [
        "rep_trip_id",
        "route_id",
        "trip_headsign",
        "route_short_name",
        "route_long_name",
        "route_type",
        "direction_id",
        "ct_cardinal_direction",
    ]
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

routes['id'] = routes['route_id'].astype(str) + '_' + routes['ct_cardinal_direction'].astype(str)
routes_stops = routes_stops.merge(routes[['rep_trip_id', 'id']], on='rep_trip_id', how='left')


routes = routes.groupby(["id"]).first().reset_index()
routes.set_index('id', inplace=True)
routes_dict = routes.to_dict(orient='index')


routes_stops_dict = (
    routes_stops
    .groupby('id')
    .apply(lambda df: df[['stop_id', 'stop_name', 'stop_sequence', 'stop_lat', 'stop_lon']].to_dict(orient='records'))
    .to_dict()
)

for id in routes_dict.keys():
    routes_dict[id]['stops'] = routes_stops_dict.get(id)   

@app.get("/route_ids")
def get_route_ids():
    """
    Get route information by id
    """
    return list(routes_dict.keys())

@app.get("/route")
def get_route(id: str):
    """
    Get route information by id
    """
    if id not in routes_dict:
        raise HTTPException(status_code=404, detail="Route not found")
    route = routes_dict[id]
    return route

@app.get("/route_stops")
def get_route_stops(id: str):
    """
    Get route stops information by id
    """
    if id not in routes_stops_dict:
        raise HTTPException(status_code=404, detail="Route stops not found")
    route_stops = routes_stops_dict[id]
    return route_stops

# @app.get("/routes_stops")
# def get_routes_stops(id: str):
#     """
#     Get route information by id
#     """
#     if id not in routes_stops['id'].values:
#         raise HTTPException(status_code=404, detail="Route not found")
#     return routes_stops[routes_stops["id"] == id].to_dict(orient='records')

print ('done')