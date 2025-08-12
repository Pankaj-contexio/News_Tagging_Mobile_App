from flask import Blueprint, render_template, send_file, jsonify, request, session, Response, current_app
import os
from io import BytesIO
from xhtml2pdf import pisa
from bson import ObjectId, SON
from models import analytics_collection, party_share_history,foreignRelations
from pdf2docx import Converter
import tempfile
from datetime import datetime
import requests
import base64
import random
from collections import defaultdict
analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/api/analytics', methods=['GET', 'POST'])
def analytics():
    """
    Render the analytics page.
    """
    if 'username' not in session:
        return render_template('login.html')
    
    if request.method == 'POST':
        formdata = request.json

        # Extract values from request
        rate_party = formdata.get('addRate')                      # Party to increase
        add_rating = float(formdata.get('partyRating'))           # Rating to add
        remove_party = formdata.get('removeRate')                 # Party to decrease
        remove_rating = float(formdata.get('removePartyRating'))  # Rating to remove
        country_id = formdata.get('countryId')
        date_str = datetime.now().strftime('%Y-%m-%d')            # Current date

        # Store rating for party being added
        party_share_history.insert_one({
            "country": country_id,
            "party": rate_party,
            "party_share": add_rating,
            "action": "add",
            "date": date_str
        })

        # Handle rating deduction
        if remove_party != "All":
            party_share_history.insert_one({
                "country": country_id,
                "party": remove_party,
                "party_share": -remove_rating,
                "action": "remove",
                "date": date_str
            })
        else:
            # Fetch all other parties (except the one being added)
            all_parties = party_share_history.distinct("party", {"country": country_id})
            other_parties = [p for p in all_parties if p != rate_party]

            if other_parties:
                deduct_each = add_rating / len(other_parties)
                for party_name in other_parties:
                    party_share_history.insert_one({
                        "country": country_id,
                        "party": party_name,
                        "party_share": -deduct_each,
                        "action": "auto_remove",
                        "date": date_str
                    })
        return jsonify({'status': 'success', 'message': 'Rating updated successfully'})
    
    # Fetching the list of parties from the social collection
    analytics = analytics_collection.find_one({}, {'_id': 0})
    
    return jsonify({
        'status': 'success',
        'analytics': analytics})



@analytics_bp.route('/api/chart-data')
def chart_data():
    x_axis = request.args.get('x_axis', 'month')  # 'month' or 'day'
    country_id = request.args.get('country_id', 'country_1')

    # Choose date format
    if x_axis == "month":
        date_format = "%Y-%m"
        date_projection = {
            "$dateToString": {
                "format": "%Y-%m",
                "date": {"$dateFromString": {"dateString": "$date"}}
            }
        }
    else:
        date_format = "%Y-%m-%d"
        date_projection = {
            "$dateToString": {
                "format": "%Y-%m-%d",
                "date": {"$dateFromString": {"dateString": "$date"}}
            }
        }

    # MongoDB 4.x compatible pipeline
    pipeline = [
        {"$match": {"country": country_id}},
        {"$addFields": {"grouped_date": date_projection}},
        {"$project": {"party": 1, "party_share": 1, "grouped_date": 1}},
        {"$sort": {"party": 1, "grouped_date": 1}}
    ]

    cursor = party_share_history.aggregate(pipeline)

    # Cumulative logic in Python
    cumulative_data = defaultdict(list)
    running_totals = defaultdict(float)
    date_set = set()

    for doc in cursor:
        party = doc["party"]
        date = doc["grouped_date"]
        share = doc["party_share"]

        running_totals[party] += share
        cumulative_data[party].append({"date": date, "share": round(running_totals[party], 2)})
        date_set.add(date)

    # Collect all unique dates sorted
    labels = sorted(date_set)

    # Forward-fill values for each party
    party_data = {}
    for party, history in cumulative_data.items():
        history_map = {record["date"]: record["share"] for record in history}
        shares = []
        last_value = 0
        for date in labels:
            if date in history_map:
                last_value = history_map[date]
            shares.append(last_value)
        party_data[party] = shares

    # Prepare chart.js datasets
    colors = ["red", "blue", "green", "orange", "purple", "teal", "brown", "pink", "gray", "black"]
    datasets = []
    for i, (party, shares) in enumerate(party_data.items()):
        datasets.append({
            "label": party,
            "data": shares,
            "borderColor": colors[i % len(colors)],
            "fill": False
        })

    return jsonify({
        "labels": labels,
        "datasets": datasets
    })

@analytics_bp.route("/api/relations", methods=['GET', 'POST'])
def get_relations():
    if request.method == 'POST':
        formdata = request.json
        countryRelation = formdata.get('countryRelation')
        rateCountry = formdata.get('rateCountry')
        countryRating = formdata.get('countryRating')
        data = list(foreignRelations.find({"country":countryRelation}, {"_id": 0}))
        if data and data[0]["relations"].get(rateCountry):
            countryRating = float(countryRating) + float(data[0]["relations"][rateCountry])
        else:
            countryRating = float(countryRating)  

        # Insert or update foreign relations
        foreignRelations.update_one(
            {"country": countryRelation},
            {"$set": {f"relations.{rateCountry}": countryRating}},
            upsert=True
        )
        return jsonify({'status': 'success', 'message': 'Foreign relation updated successfully'})
    country_id = request.args.get('country_id', 'country_1')
    data = list(foreignRelations.find({"country":country_id}, {"_id": 0}))
    return jsonify(data)