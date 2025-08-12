from flask import Flask, jsonify, request, render_template, redirect, url_for, session, flash,Response
from pymongo import MongoClient
from copy import deepcopy
from bson.objectid import ObjectId
from datetime import datetime, timedelta
import pytz
from werkzeug.security import generate_password_hash, check_password_hash
from routes.image_routes import image_bp
from routes.projects_routes import projects_bp
from routes.pdf_routes import pdf_bp
from routes.manage_reports_routes import reports_bp
from routes.document_routes import document_bp
from routes.analytics_routes import analytics_bp
from routes.chatbot_routes import chatbot_bp
import secrets
from xhtml2pdf import pisa
from pdf2docx import Converter
from io import BytesIO
import pyaudio
import wave
import os
import uuid
import threading
import certifi
import json
import re
# from weasyprint import HTML
from urllib.parse import urlparse
from newspaper import Article
from functools import lru_cache
import logging
from logging.handlers import RotatingFileHandler
import tempfile
from models import users_collection, news_collection, social_collection, projects_collection, article_requests_collection, filters_collection, tags_collection, party_share_history, usage_collection
from collections import defaultdict

from routes.tracking import track_action

# from flask_cors import CORS
app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
app.register_blueprint(image_bp, url_prefix='/api/image')
app.register_blueprint(document_bp, url_prefix='/api/document')
app.register_blueprint(projects_bp, url_prefix='/api/projects')
app.register_blueprint(pdf_bp, url_prefix='/')
app.register_blueprint(reports_bp, url_prefix='/')
app.register_blueprint(analytics_bp, url_prefix='/')

# CORS(app, origins=["http://qa.platformxplus.com:5000"])

# Create logs directory if not exists
if not os.path.exists('logs'):
    os.makedirs('logs')

# Configure logging
log_file = 'logs/app.log'

handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3)  # 1MB per file
handler.setLevel(logging.INFO)
formatter = logging.Formatter(
    '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
)
handler.setFormatter(formatter)
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

# Configure upload folder and allowed extensions
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# users_collection.create_index(
#     [("company", 1), ("username", 1)],
#     unique=True
# )
company_collection = {"company":{"Contexio":"A", "Reinlabs":"B"}}

def get_data_from_db(collection, query, skip=0, limit=20, sort=None):
    """Fetch data from MongoDB with pagination and filters."""
    data = list(collection.find(query).sort(sort).skip(skip).limit(limit))
    for document in data:
        document['_id'] = str(document['_id'])
    return data




@app.route('/api/filters', methods=['GET'])
def get_filters():
    username = session.get('username')
    if not username:
        return jsonify({"success": False, "message": "User not logged in"}), 401

    def get_tag_counts(collection, username, base_query):
        def strip_html(text):
            return re.sub(r'<[^>]+>', '', text).strip()

        tag_counts = defaultdict(int)

        # Fetch only relevant documents
        cursor = collection.find(base_query, {"AI_tags": 1, f"tags.{username}": 1})

        for doc in cursor:
            ai_tags = doc.get("AI_tags", [])
            user_tags = doc.get("tags", {}).get(username, [])
            combined = ai_tags + user_tags

            for tag in combined:
                clean_tag = strip_html(tag)
                if clean_tag:
                    tag_counts[clean_tag] += 1

        # Format the final tag list
        return [
            {"count": count, "id": tag, "name": tag}
            for tag, count in sorted(tag_counts.items())
        ]
    
    

    # Fetch all filter names from `NewsfeedFilters`
    filters_data = filters_collection.find_one({}, {'_id': 0})
    if not filters_data:
        return jsonify({"success": False, "message": "Filters not found"}), 404

    applied_filters = request.args.to_dict(flat=False)
    filter_type = request.args.get('type', 'news')  # Default to "news" type
    print(applied_filters)
    # Ensure filters are properly parsed
    for key, value in applied_filters.items():
        if isinstance(value, list):
            applied_filters[key] = [v.strip() for v in ",".join(value).split(",")]  # Split values correctly

    # Select appropriate filters based on type
    if filter_type == 'social':
        collection = social_collection
        filters_to_use = ["country", "site", "person", "filter_tags"]
        # Construct base query
        base_query = {}
        for key in filters_to_use:
            if key in applied_filters:
                if key == 'filter_tag':
                    # Handle filter_tag separately
                    tags = [f"" for tag in applied_filters[key] if tag.strip()]
                    ai_wrapped_tags = [f'<span style="background-color: #26B99A; color: white;">{t}</span>' for t in tags]
                    user_wrapped_tags = [f'<span>{t}</span>' for t in tags]
                    base_query["$or"] = [
                        {"AI_tags": {"$in": ai_wrapped_tags}},
                        {f"tags.{username}": {"$in": user_wrapped_tags}}
                    ]
                else:
                    base_query[key] = {"$in": applied_filters[key]}  # Allow multiple selections
    elif filter_type == 'project':
        filters_to_use = ["country","sector", "publisian", "site", "person", "filter_tags"]
        collection1 = news_collection
        collection2 = social_collection
        base_query = {}
        for key in filters_to_use:
            if key in applied_filters:
                if key == 'filter_tag':
                    # Handle filter_tag separately
                    tags = [f"" for tag in applied_filters[key] if tag.strip()]
                    ai_wrapped_tags = [f'<span style="background-color: #26B99A; color: white;">{t}</span>' for t in tags]
                    user_wrapped_tags = [f'<span>{t}</span>' for t in tags]
                    base_query["$or"] = [
                        {"AI_tags": {"$in": ai_wrapped_tags}},
                        {f"tags.{username}": {"$in": user_wrapped_tags}}
                    ]
                else:
                    
                    base_query[key] = {"$in": applied_filters[key]}  # Allow multiple selections
        
        
    else:
        collection = news_collection
        filters_to_use = ["country", "sector", "publisian", "filter_tags"]
        base_query = {}
        for key in filters_to_use:
            if key in applied_filters:
                if key == 'filter_tag':
                    # Handle filter_tag separately
                    tags = [f"" for tag in applied_filters[key] if tag.strip()]
                    ai_wrapped_tags = [f'<span style="background-color: #26B99A; color: white;">{t}</span>' for t in tags]
                    user_wrapped_tags = [f'<span>{t}</span>' for t in tags]
                    base_query["$or"] = [
                        {"AI_tags": {"$in": ai_wrapped_tags}},
                        {f"tags.{username}": {"$in": user_wrapped_tags}}
                    ]
                else:
                    
                    base_query[key] = {"$in": applied_filters[key]}  # Allow multiple selections

    
    query_with_filters = {}
    query_with_filters_social = {}
    def get_counts(field):
        """
        This function calculates counts for a specific field while
        correctly handling multiple selected filters.
        """
        
        pipeline = []
        pipeline2 = []

        # Apply only relevant filters without removing the field itself
        
        

        search = request.args.get('search')  # Get search query
        project_id = request.args.get('project_id')
        start_date = request.args.get('start_date')  # Expected format: DD-MM-YYYY
        end_date = request.args.get('end_date')  # Expected format: DD-MM-YYYY

        if project_id:
            query_with_filters["projects"] = project_id
        if search:
            query_with_filters["$or"] = [  # Search in multiple fields
                {"title": {"$regex": search, "$options": "i"}},  # Case-insensitive search in title
                {"content": {"$regex": search, "$options": "i"}}  # Case-insensitive search in content
            ]
        query_with_filters_social = deepcopy(query_with_filters)
        # Apply date range filter
        if start_date and end_date:
            try:
                start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
                end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")+ timedelta(days=1)
                # query_with_filters["published_date"] = {
                #     "$gte": start_date_obj.strftime("%Y-%m-%d"),
                #     "$lte": end_date_obj.strftime("%Y-%m-%d")
                # }
                
                if filter_type == 'social':
                    query_with_filters["post_date"] = {
                        "$gte": start_date_obj,
                        "$lt": end_date_obj  # Use $lt if you added +1 day to make it inclusive
                    }   
                    for key, value in base_query.items():
                        if key != field:  # Do NOT exclude the field we're counting
                            query_with_filters[key] = value
                elif filter_type == 'news':
                    query_with_filters["published_date"] = {
                        "$gte": start_date_obj,
                        "$lt": end_date_obj  # Use $lt if you added +1 day to make it inclusive
                    }
                    for key, value in base_query.items():
                        if key != field:  # Do NOT exclude the field we're counting
                            query_with_filters[key] = value
                else:
                    #deep copy the query_with_filters
                    
                    query_with_filters_social["post_date"] = {
                        "$gte": start_date_obj,
                        "$lt": end_date_obj  # Use $lt if you added +1 day to make it inclusive
                    }
                    query_with_filters["published_date"] = {
                        "$gte": start_date_obj,
                        "$lt": end_date_obj  # Use $lt if you added +1 day to make it inclusive
                    }
                    
                    for key, value in base_query.items():
                        if key != field:  # Do NOT exclude the field we're counting
                            query_with_filters[key] = value
                    for key, value in base_query.items():
                        if key != field:  # Do NOT exclude the field we're counting
                            query_with_filters_social[key] = value
            except ValueError:
                return jsonify({"error": "Invalid date format"}), 400

        pipeline.append({"$match": query_with_filters})
        # Group by the field and count occurrences
        pipeline.append({
            "$group": {
                "_id": f"${field}",
                "count": {"$sum": 1}
            }
        })
        pipeline2.append({"$match": query_with_filters_social})
        pipeline2.append({"$group": {
            "_id": f"${field}",
            "count": {"$sum": 1}
        }}) 
        
        if filter_type == 'project':
            result1 = list(collection1.aggregate(pipeline))
            result2 = list(collection2.aggregate(pipeline2))
            
           # Ensure the second aggregation has time to complete
            # Combine results from both collections
            results = result1 + result2
            total_counts = defaultdict(int)
            for res in results:
                if res["_id"]:
                    total_counts[res["_id"]] += res["count"]
        else:
            # Execute aggregation query
            results = list(collection.aggregate(pipeline))
            total_counts = {res["_id"]: res["count"] for res in results}
        # Convert ID to name mapping from filters_data
        id_to_name = {item["id"]: item["name"] for item in filters_data.get(field, [])}
        
        # Sum counts properly for selected filters
        

        all_options = []
        
        for item in filters_data.get(field, []):
            count = total_counts.get(item["id"], 0)
    
            if item["id"].startswith("publisian_"):
                all_options.append({
                    "id": item["id"],
                    "name": item["name"],
                    "count": count,
                    "url": item["url"]
                })
            else:
                all_options.append({
                    "id": item["id"],
                    "name": item["name"],
                    "count": count
                })

        return all_options

    # Handle tags for all types
    if filter_type == "project":
        tags = get_tag_counts(collection1, username, query_with_filters) + get_tag_counts(collection2, username, query_with_filters_social)
        
        # Merge tag counts from both sources
        merged_counts = defaultdict(int)
        for tag in tags:
            merged_counts[tag['id']] += tag['count']
        
        tags = [{"count": c, "id": k, "name": k} for k, c in sorted(merged_counts.items())]
    else:
        tags = get_tag_counts(collection, username, query_with_filters)

    # Generate response for all filters
    filters_response = {field: get_counts(field) for field in filters_to_use}
    filters_response['filter_tags'] = tags  # Add tags to the response

    return jsonify(filters_response), 200


@app.route('/api/tags', methods=['GET'])
def get_tags():
    """Fetch tags from the 'tags' collection."""
    
    tags_data = tags_collection.find_one({}, {'_id': 0, 'tags': 1})
    if tags_data:
        return jsonify(tags_data['tags'])
    else:
        return jsonify([])  # Return an empty array if no tags are found



@app.route('/api/news', methods=['GET'])
def get_news():
    username = session.get('username')
    company = session.get('company')
    if not username:
        return jsonify({"success": False, "message": "User not logged in"}), 401


    project_id = request.args.get('project_id')
    level = request.args.get('level')
    country = request.args.get('country')
    publisian = request.args.get('publisian')
    sector = request.args.get('sector')
    filter_tags = request.args.get('filter_tag')  # Get tags from request
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    search = request.args.get('search')  # Get search query
    skip = int(request.args.get('skip', 0))
    limit = int(request.args.get('limit', 20))
    qcdone = request.args.get('qc_done')
    
    
    # Initialize the query
    query = {}
    if project_id:
        query["projects"] = project_id

    # If 'level' is provided, convert it to an integer and apply the filter
    if level:
        try:
            level_int = int(level)  # Convert level to an integer
            query["level"] = {"$in": [level_int]}  # Query against integer value
        except ValueError:
            return jsonify({"error": "Invalid level value"}), 400

    # Apply country filter
    if country:
        query["country"] = {"$in": country.split(",")}

    if publisian:
        query["publisian"] = {"$in": publisian.split(",")}

    # Apply sector filter
    if sector:
        query["sector"] = {"$in": sector.split(",")}

    if filter_tags:
        plain_tags = [t.strip() for t in filter_tags.split(",") if t.strip()]

        ai_wrapped_tags = [f'<span style="background-color: #26B99A; color: white;">{t}</span>' for t in plain_tags]
        user_wrapped_tags = [f'<span>{t}</span>' for t in plain_tags]

        query["$or"] = [
            {"AI_tags": {"$in": ai_wrapped_tags}},
            {f"tags.{username}": {"$in": user_wrapped_tags}}
        ]

    # Apply date range filter
    if start_date and end_date:
        try:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")+ timedelta(days=1)
            query["published_date"] = {
                "$gte": start_date_obj,
                "$lt": end_date_obj  # Use $lt if you added +1 day to make it inclusive
            }
            
        except ValueError:
            return jsonify({"error": "Invalid date format"}), 400

    # Apply search query with case-insensitive regex
    if search:
        query["$or"] = [  # Search in multiple fields
            {"title": {"$regex": search, "$options": "i"}},  # Case-insensitive search in title
            {"content": {"$regex": search, "$options": "i"}}  # Case-insensitive search in content
        ]

    #Add sorting by gather_date in descending order (latest first)
    sort = [("published_date", -1)]
    # Fetch news from the database with pagination
    if qcdone== 'all':
        query[f'{company}.QC_Done.active'] = True
        query[f'{company}.QC_Done.company'] = company
    elif qcdone == username:
        query[f'{company}.QC_Done.user'] = username
        query[f'{company}.QC_Done.company'] = company
    elif qcdone == 'published':
        query[f'{company}.level'] = 2
        query[f'{company}.QC_Done.company'] = company
    news_data = get_data_from_db(news_collection, query, skip=skip, limit=limit, sort=sort)
    

    # Fetch all count and QC done count

    count_query = query.copy()
    if "level" in count_query:
        del count_query["level"]
    all_count = news_collection.count_documents(count_query)
    
    myqc_done_count = news_collection.count_documents({f"{company}.QC_Done.user": username,f"{company}.QC_Done.company": session.get('company')}) + \
                    social_collection.count_documents({f"{company}.QC_Done.user": username,f"{company}.QC_Done.company": session.get('company')})
    allqc_count = news_collection.count_documents({f"{company}.QC_Done.active": True, f"{company}.QC_Done.company": session.get('company')}) + \
                    social_collection.count_documents({f"{company}.QC_Done.active": True,f"{company}.QC_Done.company": session.get('company')})
    published_count = news_collection.count_documents({f"{company}.level": 2}) + \
                        social_collection.count_documents({f"{company}.level": 2})
    if qcdone== 'all':
        qcnewscount = news_collection.count_documents({**query, f"{company}.QC_Done.active": True, f"{company}.QC_Done.company": session.get('company')}) 
        qcsocialcount = social_collection.count_documents({f"{company}.QC_Done.active": True,f"{company}.QC_Done.company": session.get('company')})
   
    elif qcdone == username:
        qcnewscount = news_collection.count_documents({**query, f"{company}.QC_Done.user": username,f"{company}.QC_Done.company": session.get('company')})
        qcsocialcount = social_collection.count_documents({f"{company}.QC_Done.user": username,f"{company}.QC_Done.company": session.get('company')})
     
    elif qcdone == 'published':
        qcnewscount = news_collection.count_documents({**query, f"{company}.level": 2})
        qcsocialcount = social_collection.count_documents({f"{company}.level": 2})
    else:
        qcnewscount = 0 
        qcsocialcount = 0
    
    qccounts = {
        "myqc_done_count": myqc_done_count,
        "allqc_count": allqc_count,
        "published_count": published_count,
        "qcnewscount": qcnewscount,
        "qcsocialcount": qcsocialcount
    }


    if "projects" in query:
        project = projects_collection.find_one({"_id": ObjectId(project_id), "owner": username})
        project_name = project["name"]
    else:
        project_name = ""

    # Fetch counts for filters dynamically
    def get_filter_counts(field):
        pipeline = [
            {"$match": query},
            {"$group": {"_id": f"${field}", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        return [{"name": res["_id"], "count": res["count"]} for res in news_collection.aggregate(pipeline) if
                res["_id"]]

    filters_count = {
        "country": get_filter_counts("country"),
        "sector": get_filter_counts("sector"),
        "publisian": get_filter_counts("publisian")
    }


    

    return jsonify({
        "data": news_data,
        "all_count": all_count,
        "qccounts": qccounts,
        "project_name": project_name,
        "filters_count":filters_count,
        "username":username
    })

    # return jsonify(news)




@app.route('/api/social', methods=['GET'])
def get_social():
    username = session.get('username')
    if not username:
        return jsonify({"success": False, "message": "User not logged in"}), 401

    project_id = request.args.get('project_id')
    level = request.args.get('level')
    country = request.args.get('country')
    site = request.args.get('site')
    person = request.args.get('person')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    search = request.args.get('search')
    skip = int(request.args.get('skip', 0))
    limit = int(request.args.get('limit', 20))
    qcdone = request.args.get('qc_done')
    company = session.get('company')
    filter_tags = request.args.get('filter_tag')  # Get tags from request

    query = {}
    if qcdone== 'all':
        query[f'{company}.QC_Done.active'] = True
        query[f'{company}.QC_Done.company'] = company
    elif qcdone == username:
        query[f'{company}.QC_Done.user'] = username
        query[f'{company}.QC_Done.company'] = company
    elif qcdone == 'published':
        query[f'{company}.level'] = 2
        query[f'{company}.QC_Done.company'] = company
    if project_id:
        query["projects"] = project_id

    # If 'level' is provided, convert it to an integer and apply the filter
    if level:
        try:
            level_int = int(level)  # Convert level to an integer
            query["level"] = {"$in": [level_int]}  # Query against integer value
        except ValueError:
            return jsonify({"error": "Invalid level value"}), 400

    if country:
        query["country"] = {"$in": country.split(",")}
    if site:
        query["site"] = {"$in": site.split(",")}
    if person:
        query["person"] = {"$in": person.split(",")}
    if filter_tags:
        plain_tags = [t.strip() for t in filter_tags.split(",") if t.strip()]

        ai_wrapped_tags = [f'<span style="background-color: #26B99A; color: white;">{t}</span>' for t in plain_tags]
        user_wrapped_tags = [f'<span>{t}</span>' for t in plain_tags]

        query["$or"] = [
            {"AI_tags": {"$in": ai_wrapped_tags}},
            {f"tags.{username}": {"$in": user_wrapped_tags}}
        ]
    # Apply date range filter
    if start_date and end_date:
        try:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")+ timedelta(days=1)
            query["post_date"] = {
                "$gte": start_date_obj,
                "$lt": end_date_obj
            }
        except ValueError:
            return jsonify({"error": "Invalid date format"}), 400

    # Apply search query
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"content": {"$regex": search, "$options": "i"}}
        ]

    
    # Add sorting by gather_date in descending order (latest first)
    sort = [("post_date", -1)]
    social_data = get_data_from_db(social_collection, query, skip=skip, limit=limit, sort=sort)
    

    # Fetch all count and QC done count

    count_query =  query.copy()
    if "level" in count_query:
        del count_query["level"]
    all_count = social_collection.count_documents(count_query)
    myqc_done_count = news_collection.count_documents({f"{company}.QC_Done.user": username,f"{company}.QC_Done.company": session.get('company')}) + \
                    social_collection.count_documents({f"{company}.QC_Done.user": username,f"{company}.QC_Done.company": session.get('company')})
    allqc_count = news_collection.count_documents({f"{company}.QC_Done.active": True, f"{company}.QC_Done.company": session.get('company')}) + \
                    social_collection.count_documents({f"{company}.QC_Done.active": True,f"{company}.QC_Done.company": session.get('company')})
    published_count = news_collection.count_documents({f"{company}.level": 2}) + \
                        social_collection.count_documents({f"{company}.level": 2})
    qc_done_count = social_collection.count_documents({**query, "level":1})
    if qcdone== 'all':
        qcnewscount = news_collection.count_documents({f"{company}.QC_Done.active": True, f"{company}.QC_Done.company": session.get('company')}) 
        qcsocialcount = social_collection.count_documents({**query, f"{company}.QC_Done.active": True,f"{company}.QC_Done.company": session.get('company')})
   
    elif qcdone == username:
        qcnewscount = news_collection.count_documents({f"{company}.QC_Done.user": username,f"{company}.QC_Done.company": session.get('company')})
        qcsocialcount = social_collection.count_documents({**query, f"{company}.QC_Done.user": username,f"{company}.QC_Done.company": session.get('company')})
     
    elif qcdone == 'published':
        qcnewscount = news_collection.count_documents({f"{company}.level": 2})
        qcsocialcount = social_collection.count_documents({**query, f"{company}.level": 2})
    else:
        qcnewscount = 0 
        qcsocialcount = 0
    
    qccounts = {
        "myqc_done_count": myqc_done_count,
        "allqc_count": allqc_count,
        "published_count": published_count,
        "qcnewscount": qcnewscount,
        "qcsocialcount": qcsocialcount
    }
    if "projects" in query:
        project = projects_collection.find_one({"_id": ObjectId(project_id), "owner": username})
        project_name = project["name"]
    else:
        project_name = ""

    return jsonify({
        "data": social_data,
        "all_count": all_count,
        "qccounts": qccounts,
        "qc_done_count": qc_done_count,
        "project_name":project_name,
        "username":username
    })
    # return jsonify(social)


@app.route('/api/publish', methods=['POST'])
def send_data():
    data = request.json
    
    document_id = data.get('_id')
    company = session.get('company')
    if not document_id:
        return jsonify({"message": "Document _id is missing."}), 400
    try:
        object_id = ObjectId(document_id)
    except:
        return jsonify({"message": "Invalid _id format."}), 400
    

     
    data.pop('_id', None)
    query = {"_id": object_id}
    update = {"$set": {f"{company}.level": 2}}
    if data.get('page', '') == 'news':
        
        result = news_collection.update_one(query, update)  # , upsert=False
    else:
        result = social_collection.update_one(query, update)  # , upsert=False

    if result.matched_count > 0:
        return jsonify({"message": "Data updated successfully!"}), 200
    else:
        return jsonify({"message": "No matching document found to update."}), 404


# Notes Api #-------------------------------------------------------------------------------
@app.route('/api/savenotes', methods=['POST'])
def save_notes():
    data = request.json
    document_id = data.get('_id')
    note = data.get('notes', '')
    user = session.get('username')
    if not document_id:
        return jsonify({"message": "Document _id is missing."}), 400
    try:
        object_id = ObjectId(document_id)
    except:
        return jsonify({"message": "Invalid _id format."}), 400

    data.pop('_id', None)
    query = {"_id": object_id}
    update = {"$push": {f"notes.{user}": note}}  # Append the note to the user's notes array
    
    if data.get('page', '') == 'news':
        
        result = news_collection.update_one(query, update)  # , upsert=False
    else:
        result = social_collection.update_one(query, update)  # , upsert=False
    
    if result.matched_count > 0:
        track_action('note_added', {
            'Article_id': object_id,
            'page': data.get('page', ''),
        })

        return jsonify({"message": "Data updated successfully!"}), 200
    else:
        return jsonify({"message": "No matching document found to update."}), 404


@app.route('/api/saveobservations', methods=['POST'])
def save_observations():
    data = request.json
    document_id = data.get('_id')
    note = data.get('observations', '')
    user = session.get('username')
    if not document_id:
        return jsonify({"message": "Document _id is missing."}), 400
    try:
        object_id = ObjectId(document_id)
    except:
        return jsonify({"message": "Invalid _id format."}), 400

    data.pop('_id', None)
    query = {"_id": object_id}
    update = {"$push": {f"observations.{user}": note}}  # Append the note to the user's notes array

    if data.get('page', '') == 'news':

        result = news_collection.update_one(query, update)  # , upsert=False
    else:
        result = social_collection.update_one(query, update)  # , upsert=False

    if result.matched_count > 0:
        track_action('observation_added', {
            'Article_id': object_id,
            'page': data.get('page', ''),
        })

        return jsonify({"message": "Data updated successfully!"}), 200
    else:
        return jsonify({"message": "No matching document found to update."}), 404

@app.route('/api/saveinsights', methods=['POST'])
def save_insights():
    data = request.json
    document_id = data.get('_id')
    note = data.get('insights', '')
    user = session.get('username')
    if not document_id:
        return jsonify({"message": "Document _id is missing."}), 400
    try:
        object_id = ObjectId(document_id)
    except:
        return jsonify({"message": "Invalid _id format."}), 400

    data.pop('_id', None)
    query = {"_id": object_id}
    update = {"$push": {f"insights.{user}": note}}  # Append the note to the user's notes array

    if data.get('page', '') == 'news':

        result = news_collection.update_one(query, update)  # , upsert=False
    else:
        result = social_collection.update_one(query, update)  # , upsert=False

    if result.matched_count > 0:
        track_action('insight_added', {
            'Article_id': object_id,
            'page': data.get('page', ''),
        })
        return jsonify({"message": "Data updated successfully!"}), 200
    else:
        return jsonify({"message": "No matching document found to update."}), 404


@app.route('/api/saveapi', methods=['POST'])
def save_data():
    data = request.json  # Data received from the frontend
    document_id = data.get('_id')
    tag = data.get('tags', '')
    user = session.get('username')
    if not document_id:
        return jsonify({"message": "Document _id is missing."}), 400

    try:
        # Convert the `_id` to an ObjectId
        object_id = ObjectId(document_id)
    except:
        return jsonify({"message": "Invalid _id format."}), 400

    # Remove the `_id` from the data before updating, as `_id` cannot be modified
    data.pop('_id', None)
    query = {"_id": object_id}

    # Update the document by appending "c" to the tags array
    update = {"$push": {f"tags.{user}": tag}}
    # Update the existing document in the same collection
    
    if data.get('page', '') == 'news':
        result = news_collection.update_one(query, update)  # , upsert=False
    else:
        result = social_collection.update_one(query, update)  # , upsert=False

    if result.matched_count > 0:
        return jsonify({"message": "Data updated successfully!"}), 200
    else:
        return jsonify({"message": "No matching document found to update."}), 404


@app.route('/api/editeddata', methods=['POST'])
def editeddata():
    data = request.json  # Data received from the frontend
    project_id = data.get('project_id')
    document_id = data.get('_id')
    editeddata = data.get('content', '')
    user = session.get('username')
    company = session.get('company')
    
    if not document_id:
        return jsonify({"message": "Document _id is missing."}), 400

    try:

        object_id = ObjectId(document_id)
    except:
        return jsonify({"message": "Invalid _id format."}), 400
    data.pop('_id', None)
    query = {"_id": object_id}
    if project_id:
        update = {"$push": {f"editedContent.{company}.{user}.{project_id}": editeddata},
                  "$set": {company:{"QC_Done":{"active": True,
                                      "user":user,
                                      "company":company}}},
                  "$set": {"level": 1}}
    else:
        update = {"$push": {f"editedContent.{company}.{user}.{user}": editeddata},
                  "$set": {
                        f"{company}.QC_Done": {
                            "active": True,
                            "user": user,
                            "company": company
                        },
                        "level": 1
                    }
                }
    

    if data.get('page', '') == 'news':

        result = news_collection.update_one(query, update)  # , upsert=False
    else:
        result = social_collection.update_one(query, update)  # , upsert=False

    if result.matched_count > 0:
        track_action('content_edited', {
            'Article_id': object_id,
            'page': data.get('page', ''),
        })

        return jsonify({"message": "Data updated successfully!"}), 200
    else:
        return jsonify({"message": "No matching document found to update."}), 404

@app.route('/api/removenotes', methods=['POST'])
def remove_notes():
    data = request.json  # Data received from the frontend
    document_id = data.get('_id')
    note = data.get('notes', '')
    user = session.get('username')
    if not document_id:
        return jsonify({"message": "Document _id is missing."}), 400
    try:
        # Convert the `_id` to an ObjectId
        object_id = ObjectId(document_id)
    except:
        return jsonify({"message": "Invalid _id format."}), 400

    # Remove the `_id` from the data before updating, as `_id` cannot be modified
    data.pop('_id', None)
    query = {"_id": object_id}
    # Update the document by appending "c" to the tags array
    update = {"$pull": {f"notes.{user}": note}}
    # Update the existing document in the same collection
    if data.get('page', '') == 'news':
        result = news_collection.update_one(query, update)
    else:
        result = social_collection.update_one(query, update)

    if result.matched_count > 0:
        return jsonify({"message": "Data updated successfully!"}), 200
    else:
        return jsonify({"message": "No matching document found to update."}), 404

@app.route('/api/removeobservations', methods=['POST'])
def remove_observations():
    data = request.json  # Data received from the frontend
    document_id = data.get('_id')
    note = data.get('observations', '')
    user = session.get('username')
    if not document_id:
        return jsonify({"message": "Document _id is missing."}), 400
    try:
        # Convert the `_id` to an ObjectId
        object_id = ObjectId(document_id)
    except:
        return jsonify({"message": "Invalid _id format."}), 400

    # Remove the `_id` from the data before updating, as `_id` cannot be modified
    data.pop('_id', None)
    query = {"_id": object_id}
    # Update the document by appending "c" to the tags array
    update = {"$pull": {f"observations.{user}": note}}
    # Update the existing document in the same collection
    if data.get('page', '') == 'news':
        result = news_collection.update_one(query, update)
    else:
        result = social_collection.update_one(query, update)

    if result.matched_count > 0:
        return jsonify({"message": "Data updated successfully!"}), 200
    else:
        return jsonify({"message": "No matching document found to update."}), 404

@app.route('/api/removeinsights', methods=['POST'])
def remove_insights():
    data = request.json  # Data received from the frontend
    document_id = data.get('_id')
    note = data.get('insights', '')
    user = session.get('username')
    if not document_id:
        return jsonify({"message": "Document _id is missing."}), 400
    try:
        # Convert the `_id` to an ObjectId
        object_id = ObjectId(document_id)
    except:
        return jsonify({"message": "Invalid _id format."}), 400

    # Remove the `_id` from the data before updating, as `_id` cannot be modified
    data.pop('_id', None)
    query = {"_id": object_id}
    # Update the document by appending "c" to the tags array
    update = {"$pull": {f"insights.{user}": note}}
    # Update the existing document in the same collection
    if data.get('page', '') == 'news':
        result = news_collection.update_one(query, update)
    else:
        result = social_collection.update_one(query, update)

    if result.matched_count > 0:
        return jsonify({"message": "Data updated successfully!"}), 200
    else:
        return jsonify({"message": "No matching document found to update."}), 404



@app.route('/api/removetag', methods=['POST'])
def remove_tag():
    data = request.json  # Data received from the frontend
    document_id = data.get('_id')
    tag = data.get('tags', '')
    user = session.get('username')
    if not document_id:
        return jsonify({"message": "Document _id is missing."}), 400

    try:
        # Convert the `_id` to an ObjectId
        object_id = ObjectId(document_id)
    except:
        return jsonify({"message": "Invalid _id format."}), 400

    # Remove the `_id` from the data before updating, as `_id` cannot be modified
    data.pop('_id', None)
    query = {"_id": object_id}

    # Update the document by appending "c" to the tags array
    update = {"$pull": {f"tags.{user}": tag}}
    # Update the existing document in the same collection
    if data.get('page', '') == 'news':
        result = news_collection.update_one(query, update)  # , upsert=False
    else:
        result = social_collection.update_one(query, update)  # , upsert=False

    if result.matched_count > 0:
        return jsonify({"message": "Data updated successfully!"}), 200
    else:
        return jsonify({"message": "No matching document found to update."}), 404


###########################################################################################
###############################  Login ####################################################
###########################################################################################
###########################################################################################



@app.route('/register', methods=['GET', 'POST'])
def register_user():
    session['_flashes'] = []
    user = session.get('username')
    userdata = users_collection.find_one({"username": user})
    userlevel = userdata.get('level') if userdata else None
    
    if not user:
        return jsonify({"success": False, "message": "User not logged in"}), 401
    elif int(userlevel) <= 1:
        flash('You are not authorized to access this page.')
        user_ip = request.remote_addr
        app.logger.info(f"Register page try to accessed by {user} on {user_ip}")
        return render_template('page_403.html')
    if request.method == 'POST':
        
        username = request.form['username']
        password = request.form['password']
        name = request.form['name']
        email = request.form['email']
        dob = request.form['dob']
        mobile = request.form['mobile']
        level = request.form['level']
        company = request.form['cname']
        designation = request.form['designation']

        new_user = users_collection.find_one({"username": username})
        if new_user:
            flash('Username already exists!')
            return render_template('Register.html', error='Username already exists.')

        hashed_password = generate_password_hash(password)
        users_collection.insert_one({"username": username,
                                      "hashed_password": hashed_password,
                                        "password":password,
                                        "name":name,
                                        "email":email,
                                        "dob":dob,
                                        "mobile":mobile,
                                        "level":level,
                                        "company":company,
                                        "designation":designation,
                                        })
        user_ip = request.remote_addr
        app.logger.info(f"New User register {username} by {user_ip}")
        flash('Registration successful! Please login.')
        return redirect('/login')
    return render_template('register.html')




@app.route('/login', methods=['GET', 'POST'])
def login_user():  # Renamed from 'login' to 'login_user'
    if request.method == 'POST':
        session['_flashes'] = []  # Clear any existing flashes
        username = request.form['username']
        password = request.form['password']
        
        
        user = users_collection.find_one({"username": username})
        
        # if user and check_password_hash(user['hashed_password'], password):
        if user and user['password'] == password: 
            session['username'] = username
            session['level'] = user['level']
            companyName =user['company']
            session['company'] = company_collection["company"][companyName]
            user_ip = request.remote_addr
            app.logger.info(f"{username} logged in by {user_ip}")
            track_action('user_login')

            return redirect('/Dashboard')
        user_ip = request.remote_addr
        app.logger.info(f"{username} try to log in by {user_ip}")
        flash('Invalid username or password!')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session['_flashes'] = []
    
    app.logger.info(f"{session.get('username')} logged out")
    track_action('user_logout')
    session.pop('username', None)
    flash('You have been logged out!')
    return redirect('/login')


@app.route('/')
def home():
    return redirect('/login')


@app.route('/login')
def render_login_template():
    return render_template('Login.html')

@app.route('/register')
def render_register_template():
    return render_template('Register.html')

@app.route('/News')
def news():
    session['_flashes'] = []
   
    if 'username' in session and 'level' in session:
        username = session['username']
        level = session['level']
        companyid = session['company']
        user_data = users_collection.find_one({"username": username})
        try:
            designation = user_data.get('designation')
        except:
            designation = ''
        try:
            company = user_data.get('company')
        except:
            company = ''
        return render_template('Newsv2.html', username=username, level=level, companyid=companyid, company=company, designation=designation)
    flash('Please log in to access this page.')
    return redirect('/login')

@app.route('/SocialMedia')
def social():
    if 'username' in session and 'level' in session:
        username = session['username']
        level = session['level']
        companyid = session['company']
        user_data = users_collection.find_one({"username": username})
        try:
            designation = user_data.get('designation')
        except:
            designation = ''
        try:
            company = user_data.get('company')
        except:
            company = ''
        return render_template('SocialMediav2.html', username=username, level=level,company=company, designation=designation, companyid=companyid)
    flash('Please log in to access this page.')
    return redirect('/login')
    # return render_template('social_feed.html')

@app.route('/projects')
def projects():
    if 'username' in session and 'level' in session:
        username = session['username']
        level = session['level']
        companyid = session['company']
        user_data = users_collection.find_one({"username": username})
        try:
            designation = user_data.get('designation')
        except:
            designation = ''
        try:
            company = user_data.get('company')
        except:
            company = ''
        return render_template('projects.html', username=username, level=level, companyid=companyid, company=company, designation=designation)
    flash('Please log in to access this page.')
    return redirect('/login')

@app.route('/addcard')
def addcard():
    if 'username' in session and 'level' in session:
        username = session['username']
        level = session['level']
        companyid = session['company']
        user_data = users_collection.find_one({"username": username})
        try:
            designation = user_data.get('designation')
        except:
            designation = ''
        try:
            company = user_data.get('company')
        except:
            company = ''
        return render_template('add-card.html', username=username, designation=designation,company=company, level=level)
    flash('Please log in to access this page.')
    return redirect('/login')


@app.route('/parse-article')
def parse_article():
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "URL is required"}), 400
    
    try:
        # Safe default: Create a temp dir if needed (optional, for reliability on some systems)
        tmp_dir = os.path.join(tempfile.gettempdir(), '.newspaper_scraper', 'article_resources')
        os.makedirs(tmp_dir, exist_ok=True)
        # Set the newspaper3k configuration to use the temp directory
        try:
            article = Article(url)
            article.download()
            article.parse()
        except:
            try:
                scrapping_url = "https://api.scraperapi.com/?api_key=67eccd6cc9992b620d4f5f03d0e5b3a9&url=" + url
                article = Article(scrapping_url)
                article.download()
                article.parse()
            except:
                try:
                    scrapping_url = "https://api.scraperapi.com/?api_key=67eccd6cc9992b620d4f5f03d0e5b3a9&url=" + url + "&render=true"
                    article = Article(scrapping_url)
                    article.download()
                    article.parse()
                except:
                    try:
                        scrapping_url = "https://api.scraperapi.com/?api_key=67eccd6cc9992b620d4f5f03d0e5b3a9&url=" + url + "&premium=true"
                        article = Article(scrapping_url)
                        article.download()
                        article.parse()
                    except:
                        try:
                            scrapping_url = "https://api.scraperapi.com/?api_key=67eccd6cc9992b620d4f5f03d0e5b3a9&url=" + url + "&render=true&premium=true"
                            article = Article(scrapping_url)
                            article.download()
                            article.parse()
                        except:
                            scrapping_url = "https://api.scraperapi.com/?api_key=67eccd6cc9992b620d4f5f03d0e5b3a9&url=" + url + "&ultra_premium=true"
                            article = Article(scrapping_url)
                            article.download()
                            article.parse()
 
        

        return jsonify({
            "title": article.title,
            "text": article.text,
            "images": [article.top_image] if article.top_image else []
        })
    except Exception as e:
        return jsonify({"error": f"Restricted URL!!!, Please add data manually"}), 500



def extract_domain(url):
    parsed_url = urlparse(url)
    domain = parsed_url.netloc.replace("www.", "")
    return domain.lower()

def extract_base_url(url):
    parsed_url = urlparse(url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}/"
    return base_url

@app.route('/addcard', methods=['POST'])
def addcard_post():
    def add_posts_to_project(project_id, post_id):
        """Add multiple posts to a project."""
        username = session.get('username')
        if not username:
            return jsonify({"success": False, "message": "User not logged in"}), 401

        
       
        post_type = 'news'

        if not post_id or not post_type:
            return jsonify({"success": False, "message": "Post IDs and type are required"}), 400

        collection = news_collection if post_type == "news" else social_collection
        if ObjectId.is_valid(post_id):
            valid_post_ids = [ObjectId(post_id)] 

        # Validate posts
        posts = list(collection.find({"_id": {"$in": valid_post_ids}}))
        if len(posts) != len(valid_post_ids):
            return jsonify({"success": False, "message": "One or more posts not found"}), 404

        # Update project and posts
        projects_collection.update_one(
            {"_id": ObjectId(project_id)},
            {"$addToSet": {"posts": {"$each": [str(post["_id"]) for post in posts]}}}
        )

        collection.update_many(
            {"_id": {"$in": valid_post_ids}},
            {"$addToSet": {"projects": project_id}}
        )

        track_action('posts_added_to_project', {
            'project_id': project_id,
            'post_count': 1,
            'post_type': post_type
        })

        return jsonify({"success": True, "message": "Posts added to project successfully!"})
    data1 = request.json
    
    data = dict(data1)
    
    if 'username' in session:
        username = session['username']
        
        if data.get('page') == 'news':
            data['title'] = data.get('title', '').strip()
            data['content'] = data.get('content', '').strip()
            data['image'] = data.get('image', [])
            project_id = data.get('project', '').strip()

            filters_data = filters_collection.find_one({}, {'_id': 0})
            news_url = data.get("news_url")  # Field from form

            matched_publisian_id = "publisian_0"  # Default
            matched_name = "Others"

            if news_url:
                article_domain = extract_domain(news_url)

                for publisian in filters_data.get("publisian", []):
                    publisian_url = publisian.get("url", "")


                    if article_domain in publisian_url or publisian_url in article_domain:
                        matched_publisian_id = publisian["id"]
                        matched_name = publisian["name"]
                        break

            data["publisian"] = matched_publisian_id
            data["news_at"] = matched_name
            publisian = data.get("publisian")
            if publisian == 'publisian_0':
                otherpublisian = article_domain.split(".")[0]
                otherpublisianlower = otherpublisian.strip().lower()
                # Check if publisian already exists (case-insensitive)
                filters_data = filters_collection.find_one({}, {'_id': 0})
                # for publisian in filters_data["publisian"]:
                #     if publisian["name"].strip().lower() == otherpublisianlower:
                #         return data  # No change needed
                existing_ids = [int(p["id"].split("_")[1]) for p in filters_data["publisian"] if p["id"].startswith("publisian_")]
                next_id = max(existing_ids) + 1 if existing_ids else 0
                new_id = f"publisian_{next_id}"
                 # Add new publisian entry
                filters_data["publisian"].append({
                    "id": new_id,
                    "name": otherpublisian.strip(),
                    "url": extract_base_url(news_url)
                })
                filters_collection.update_one({}, {"$set": {"publisian": filters_data["publisian"]}})
                data['publisian'] = new_id
                data['news_at'] = otherpublisian
                # data.pop('otherpublisianurl')
                # data.pop('otherpublisian')
            input_date = data.get('published_date')
            # Convert to datetime object
            dt = datetime.strptime(input_date, "%Y-%m-%d")
            
            data['published_date'] = dt
            data['manual_added'] = True
            data.pop('page')
            result = news_collection.insert_one(data)
            result_id = str(result.inserted_id)
            add_posts_to_project(project_id, result_id)

        else: 
            person = data.get('name')
            if person == 'person_0':
                otherperson = data.get('othername')
                otherpersonlower = otherperson.strip().lower()
                # Check if person already exists (case-insensitive)
                filters_data = filters_collection.find_one({}, {'_id': 0})
                for person in filters_data["person"]:
                    if person["name"].strip().lower() == otherpersonlower:
                        flash('Person already exists.')
                        return data
                existing_ids = [int(p["id"].split("_")[1]) for p in filters_data["person"] if p["id"].startswith("person_")]
                next_id = max(existing_ids) + 1 if existing_ids else 0
                new_id = f"person_{next_id}"
                # Add new person entry
                filters_data["person"].append({
                    "id": new_id,
                    "name": otherperson.strip(),
                })
                filters_collection.update_one({}, {"$set": {"person": filters_data["person"]}})
                filters_data = filters_collection.find_one({}, {'_id': 0})
                data['person'] = new_id
                data['name'] = data.get('othername')
                data.pop('othername')
            else:
                data['person'] = data.get('name')
            person = data.get('person')
            pipeline = [
                {"$unwind": "$person"},
                {"$match": {"person.id": person}},
                {"$project": {"_id": 0, "name": "$person.name"}}
            ]
            result = filters_collection.aggregate(pipeline)
            findName = next(result, None)
            data['name'] = findName["name"]
            
            input_date = data.get('post_date')
            dt = datetime.strptime(input_date, "%Y-%m-%d")
            
            data['post_date'] = dt
            data.pop('page')
            data['manual_added'] = True
            social_collection.insert_one(data)
        
        app.logger.info(f"New Data Uploaded in Card by {username}")
        return jsonify({"message": "Data updated successfully!"}), 200
        
        
    flash('Please log in to access this page.')
    return redirect('/login')

@app.route('/Community')
def community():
    if 'username' in session and 'level' in session:
        username = session['username']
        level = session['level']
        return render_template('community.html', username=username, level=level)
    flash('Please log in to access this page.')
    return redirect('/login')


###########################################################################################
###############################  Dashboard  ###############################################
###########################################################################################
###########################################################################################



@app.route('/Dashboard')
def render_Dashboard_template():
    if 'username' in session and 'level' in session:
        username = session['username']
        level = session['level']
        companyid = session['company']
        user_data = users_collection.find_one({"username": username})
        try:
            designation = user_data.get('designation')
        except:
            designation = ''
        try:
            company = user_data.get('company')
        except:
            company = ''
        return render_template('Dashboardv2.html', username=username, level=level,companyid=companyid, designation=designation, company=company)
    flash('Please log in to access this page.')
    return redirect('/login')


@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    username = session.get('username')
    if not username:
        return jsonify({"success": False, "message": "User not logged in"}), 401

    try:
        # Get date range from query parameters
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        # Timezone for UTC comparison
        utc = pytz.UTC

        date_filter = {}
        if start_date_str and end_date_str:
            try:
                start_dt = datetime.strptime(start_date_str, '%d-%m-%Y').replace(tzinfo=utc)
                # Set end time to the last second of the day
                end_dt = datetime.strptime(end_date_str, '%d-%m-%Y') + timedelta(days=1, seconds=-1)
                end_dt = end_dt.replace(tzinfo=utc)

                date_filter = {
                    "$or": [
                        {"published_date": {"$gte": start_dt, "$lte": end_dt}},
                        {"post_date": {"$gte": start_dt, "$lte": end_dt}}
                    ]
                }
            except ValueError:
                return jsonify({"success": False, "message": "Invalid date format. Use DD-MM-YYYY"}), 400

        # Get today's date as a datetime object (with only date)
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=utc)
        today_end = today_start + timedelta(days=1, seconds=-1)

        
        filters_data = filters_collection.find_one({}, {'_id': 0})

        if not filters_data:
            return jsonify({"success": False, "message": "Filters not found"}), 404

        # Mappings
        country_map = {item["id"]: item["name"] for item in filters_data.get("country", [])}
        sector_map = {item["id"]: item["name"] for item in filters_data.get("sector", [])}
        site_map = {item["id"]: item["name"] for item in filters_data.get("site", [])}
        publication_map = {item["id"]: item["name"] for item in filters_data.get("publisian", [])}
        person_map = {item["id"]: item["name"] for item in filters_data.get("person", [])}

        # Counts
        news_count = news_collection.count_documents({})
        social_count = social_collection.count_documents({})

        today_news_count = news_collection.count_documents({
            "published_date": {"$gte": today_start, "$lte": today_end}
        })
        today_social_count = social_collection.count_documents({
            "post_date": {"$gte": today_start, "$lte": today_end}
        })

        def pipeline_group_by(field, collection, date_field=None):
            pipeline = [{"$match": {date_field: {"$exists": True}}}] if date_field else []
            if date_filter:
                pipeline.append({"$match": date_filter})
            pipeline.append({"$group": {"_id": f"${field}", "count": {"$sum": 1}}})
            return list(collection.aggregate(pipeline))

        # Time series data - query both collections separately and combine
        def get_time_series_data():
            # News aggregation
            news_pipeline = [
                {"$match": {"published_date": {"$exists": True}}},
                {"$match": date_filter} if date_filter else {"$match": {}},
                {"$project": {
                    "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$published_date"}},
                    "count": 1
                }},
                {"$group": {
                    "_id": "$date",
                    "news_count": {"$sum": 1},
                    "social_count": {"$sum": 0}  # News collection has no social posts
                }}
            ]

            # Social aggregation
            social_pipeline = [
                {"$match": {"post_date": {"$exists": True}}},
                {"$match": date_filter} if date_filter else {"$match": {}},
                {"$project": {
                    "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$post_date"}},
                    "count": 1
                }},
                {"$group": {
                    "_id": "$date",
                    "news_count": {"$sum": 0},  # Social collection has no news posts
                    "social_count": {"$sum": 1}
                }}
            ]

            # Execute both aggregations
            news_results = list(news_collection.aggregate(news_pipeline))
            social_results = list(social_collection.aggregate(social_pipeline))

            # Combine results
            combined = {}
            for item in news_results + social_results:
                date = item["_id"]
                if date not in combined:
                    combined[date] = {"_id": date, "news_count": 0, "social_count": 0}
                combined[date]["news_count"] += item["news_count"]
                combined[date]["social_count"] += item["social_count"]

            # Convert to list and sort by date
            return sorted(combined.values(), key=lambda x: x["_id"])

        time_series_data = get_time_series_data()

        # Aggregations
        country_news = pipeline_group_by("country", news_collection, "published_date")
        country_social = pipeline_group_by("country", social_collection, "post_date")
        person_social = pipeline_group_by("person", social_collection, "post_date")
        sector_news = pipeline_group_by("sector", news_collection, "published_date")
        publication_news = pipeline_group_by("publisian", news_collection, "published_date")
        site_social = pipeline_group_by("site", social_collection, "post_date")

        # Map names
        def map_names(data, name_map, label):
            return [{label: name_map.get(item["_id"], "Unknown"), "count": item["count"]} for item in data if
                    item["_id"]]

        # Publications per country (distinct count)
        pipeline_publication_country = [
            {"$match": {"published_date": {"$exists": True}}},
            {"$match": date_filter} if date_filter else {"$match": {}},
            {"$group": {
                "_id": {
                    "country": "$country",
                    "publication": "$publisian"
                }
            }},
            {"$group": {
                "_id": "$_id.country",
                "count": {"$sum": 1}
            }}
        ]
        publication_country_results = list(news_collection.aggregate(pipeline_publication_country))

        # Map country IDs to names
        publication_counts = {}
        for item in publication_country_results:
            country_id = item["_id"]
            country_name = country_map.get(country_id)
            if country_name:
                publication_counts[country_name] = item["count"]

        # Personalities per country (distinct count)
        pipeline_personality_country = [
            {"$match": {"post_date": {"$exists": True}}},
            {"$match": date_filter} if date_filter else {"$match": {}},
            {"$group": {
                "_id": {
                    "country": "$country",
                    "person": "$person"
                }
            }},
            {"$group": {
                "_id": "$_id.country",
                "count": {"$sum": 1}
            }}
        ]
        personality_country_results = list(social_collection.aggregate(pipeline_personality_country))

        # Map country IDs to names
        personality_counts = {}
        for item in personality_country_results:
            country_id = item["_id"]
            country_name = country_map.get(country_id)
            if country_name:
                personality_counts[country_name] = item["count"]

        pipeline_party_share = [
            {
                "$group": {
                    "_id": {
                        "country": "$country",
                        "party": "$party"
                    },
                    "party_share": {"$sum": "$party_share"}
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "country": "$_id.country",
                    "name": "$_id.party",
                    "party_share": "$party_share"
                }
            },
            {
                "$sort": {
                    "country": 1,
                    "name": 1
                }
            }
        ]
        party_share_results = list(party_share_history.aggregate(pipeline_party_share))
        for doc in party_share_results:
            doc["party_share"] = round(doc["party_share"], 4)
        # Response
        return jsonify({
            "news_count": news_count,
            "social_count": social_count,
            "today_news_count": today_news_count,
            "today_social_count": today_social_count,
            "time_series_data": time_series_data,
            "country_news": map_names(country_news, country_map, "country"),
            "country_social": map_names(country_social, country_map, "country"),
            "publication_counts": publication_counts,
            "personality_counts": personality_counts,
            "person_social": map_names(person_social, person_map, "person"),
            "sector_news": map_names(sector_news, sector_map, "sector"),
            "publication_news": map_names(publication_news, publication_map, "publisian"),
            "site_social": map_names(site_social, site_map, "site"),
            "Total_Project_count": projects_collection.count_documents({"owner": username}),
            "Total_publication_count": len(filters_data.get("publisian", [])),
            "Total_Social_media_person_count": len(filters_data.get("person", [])),
            "party_rating" : party_share_results,
            "success": True
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": "Internal server error", "error": str(e)}), 500


###########################################################################################
###############################  Bookmark  #################################################
###########################################################################################
###########################################################################################



@app.route('/api/bookmark/<post_id>', methods=['POST'])
def bookmark_post(post_id):
    """Handles bookmarking/unbookmarking posts for both News and Social Media."""
    username = session.get('username')
    if not username:
        return jsonify({"success": False, "message": "User not logged in"}), 401

    action = request.json.get('action')
    post_type = request.json.get('post_type')  # 'news' or 'social'

    if post_type not in ['news', 'social']:
        return jsonify({"success": False, "message": "Invalid post type"}), 400

    collection = news_collection if post_type == 'news' else social_collection
    post = collection.find_one({"_id": ObjectId(post_id)})

    if not post:
        return jsonify({"success": False, "message": "Post not found"}), 404

    if action == "add":
        collection.update_one(
            {"_id": ObjectId(post_id)},
            {"$addToSet": {"bookmark_users": username}}
        )
    elif action == "remove":
        collection.update_one(
            {"_id": ObjectId(post_id)},
            {"$pull": {"bookmark_users": username}}
        )

    return jsonify({"success": True})




@app.route('/News_Bookmarks')
def news_bookmarks():
    """Displays all bookmarked news posts."""
    username = session.get('username')
    if not username:
        flash("Please log in to access bookmarks")
        return redirect('/login')

    bookmarked_news = list(news_collection.find({"bookmark_users": username}))
    return render_template('News_Bookmarks.html', news=bookmarked_news, username=username)


@app.route('/Social_Bookmarks')
def social_bookmarks():
    """Displays all bookmarked social media posts."""
    username = session.get('username')
    if not username:
        flash("Please log in to access bookmarks")
        return redirect('/login')

    bookmarked_social = list(social_collection.find({"bookmark_users": username}))
    return render_template('Social_Bookmarks.html', social=bookmarked_social, username=username)


###########################################################################################
###############################  Projects #################################################
###########################################################################################
##########################################################################################

@app.route('/api/news/ids', methods=['GET'])
def get_news_ids():
    """Fetch only the IDs of all posts matching the query."""
    username = session.get('username')
    if not username:
        return jsonify({"success": False, "message": "User not logged in"}), 401

    # Extract query parameters
    country = request.args.get('country')
    publisian = request.args.get('publisian')
    sector = request.args.get('sector')
    filter_tags = request.args.get('filter_tag')  # Get tags from request
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    search = request.args.get('search')
    qcdone = request.args.get('qc_done')
    project_id = request.args.get('project_id')
    company = session.get('company')
    # Build the query
    query = {}
    if country:
        query["country"] = {"$in": country.split(",")}
    if sector:
        query["sector"] = {"$in": sector.split(",")}
    if publisian:
        query["publisian"] = {"$in": publisian.split(",")}
    if filter_tags:
        plain_tags = [t.strip() for t in filter_tags.split(",") if t.strip()]

        ai_wrapped_tags = [f'<span style="background-color: #26B99A; color: white;">{t}</span>' for t in plain_tags]
        user_wrapped_tags = [f'<span>{t}</span>' for t in plain_tags]

        query["$or"] = [
            {"AI_tags": {"$in": ai_wrapped_tags}},
            {f"tags.{username}": {"$in": user_wrapped_tags}}
        ]
    if qcdone== 'all':
        query[f'{company}.QC_Done.active'] = True
        query[f'{company}.QC_Done.company'] = company
    elif qcdone == username:
        query[f'{company}.QC_Done.user'] = username
        query[f'{company}.QC_Done.company'] = company
    elif qcdone == 'published':
        query[f'{company}.level'] = 2
        query[f'{company}.QC_Done.company'] = company
    if project_id:
        query["projects"] = project_id
    # Apply date range filter
    if start_date and end_date:
        try:

            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            query["published_date"] = {
                "$gte": start_date_obj,
                "$lt": end_date_obj  # Use $lt if you added +1 day to make it inclusive
            }


        except ValueError:
            return jsonify({"error": "Invalid date format"}), 400
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"content": {"$regex": search, "$options": "i"}},
        ]


    # Fetch only the IDs of matching posts
    post_ids = [str(post["_id"]) for post in news_collection.find(query, {"_id": 1})]
    return jsonify({"success": True, "post_ids": post_ids})

@app.route('/api/social/ids', methods=['GET'])
def get_social_ids():
    """Fetch only the IDs of all posts matching the query."""
    username = session.get('username')
    if not username:
        return jsonify({"success": False, "message": "User not logged in"}), 401

    # Extract query parameters
    country = request.args.get('country')
    person = request.args.get('person')
    site = request.args.get('site')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    search = request.args.get('search')
    project_id = request.args.get('project_id')
    qcdone = request.args.get('qc_done')
    company = session.get('company')
    filter_tags = request.args.get('filter_tag')  # Get tags from request

    # Build the query
    query = {}
    if country:
        query["country"] = {"$in": country.split(",")}
    if site:
        query["site"] = {"$in": site.split(",")}
    if person:
        query["person"] = {"$in": person.split(",")}
    if filter_tags:
        plain_tags = [t.strip() for t in filter_tags.split(",") if t.strip()]

        ai_wrapped_tags = [f'<span style="background-color: #26B99A; color: white;">{t}</span>' for t in plain_tags]
        user_wrapped_tags = [f'<span>{t}</span>' for t in plain_tags]

        query["$or"] = [
            {"AI_tags": {"$in": ai_wrapped_tags}},
            {f"tags.{username}": {"$in": user_wrapped_tags}}
        ]
    if qcdone== 'all':
        query[f'{company}.QC_Done.active'] = True
        query[f'{company}.QC_Done.company'] = company
    elif qcdone == username:
        query[f'{company}.QC_Done.user'] = username
        query[f'{company}.QC_Done.company'] = company
    elif qcdone == 'published':
        query[f'{company}.level'] = 2
        query[f'{company}.QC_Done.company'] = company
    if project_id:
        query["projects"] = project_id
    # Apply date range filter
    if start_date and end_date:
        try:

            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            query["post_date"] = {
                "$gte": start_date_obj,
                "$lt": end_date_obj  # Use $lt if you added +1 day to make it inclusive
            }

        except ValueError:
            return jsonify({"error": "Invalid date format"}), 400
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"content": {"$regex": search, "$options": "i"}},
        ]


    # Fetch only the IDs of matching posts
    post_ids = [str(post["_id"]) for post in social_collection.find(query, {"_id": 1})]
    return jsonify({"success": True, "post_ids": post_ids})


###################################################################################################
###################################################################################################
#################################  pdf Download  ###################################################
###################################################################################################
###################################################################################################

def generate_report_html(data, username, company):
    """Generate HTML content for reports (used for both PDF and DOC)"""

    post_ids = data.get("post_ids", [])
    filters = data.get("filters", {})
    date_range = data.get("dateRange", None)
    search_query = data.get("searchQuery", None)
    project_name = data.get("projectName", "Project: News")  # Default to NEWS if project name is missing
    project_id = data.get("project_id", None)
    try:
        project_name = project_name.split(":")[1].strip()
    except:
        project_name = project_name

    # Convert post_ids to ObjectId and fetch from database
    try:
        object_ids = [ObjectId(post_id) for post_id in post_ids]
        posts = list(news_collection.find({"_id": {"$in": object_ids}}))
    except Exception as e:
        return jsonify({"success": False, "message": f"Error fetching posts: {str(e)}"}), 500

    if not posts:
        return jsonify({"success": False, "message": "No matching posts found"}), 404

    # Generate HTML content for the PDF
    pdf_html = """
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px;}
            h1 { color: #333; text-align: center; font-size: 24px;}
            h2 { color: #333; font-size: 16px; margin-bottom: 5px; text-align: center; }
            h3 { color: #333; font-size: 18px; margin-bottom: 5px; }
            .header { margin-bottom: 40px; }
            .header span { display: block; margin-bottom: 5px; }
            .header img { text-align: center; font-size: 24px;}
            .post { margin-bottom: 40px; }
            .content { margin-top: 10px; font-size: 14px; line-height: 1.5; }
            .highlight { background-color: yellow; } /* Highlighted text */
            .notes, .insights, .observations { margin-top: 0px; padding: 0px;  margin: 0px;}
            .written_by { margin-top: 0px; padding: 0px;  margin: 0px;}
            ul { padding-left: 20px; margin: 0px; }
            li { margin: 0px; }
            .imagecontainer { display: flex; flex-wrap: wrap; margin-top: 10px; align-items: center; justify-content: center; }
        </style>
    </head>
    <body>
    """

    # Add header information
    pdf_html += f"""
    <div class="header">
        <img src="https://reinlabs.co.in/wp-content/uploads/2019/04/Untitled-design-1.png">
        <button id="download-pdf-btn" class="btn btn-primary" style="display:none; margin-left: 10px; font-size: smaller; float: inline-end; margin:10px;" onclick="createpdf()">
            <i class="fa fa-download"></i> Generate PDF
        </button>
        <h1><strong>{project_name}</strong></h1>
        <h2><strong>Generated By:</strong> {username}</h2>
        {"<span><strong>Date Range:</strong> " + date_range + "</span>" if date_range else ""}
        {"<span><strong>Search Query:</strong> " + search_query + "</span>" if search_query else ""}
        {"<span><strong>Country:</strong> " + filters.get('country') + "</span>" if filters.get('country') and filters.get('country') != "None" else ""}
        {"<span><strong>Sector:</strong> " + filters.get('sector') + "</span>" if filters.get('sector') and filters.get('sector') != "None" else ""}
        {"<span><strong>Publication:</strong> " + filters.get('publisian') + "</span>" if filters.get('publisian') and filters.get('publisian') != "None" else ""}
    </div>
    <hr>
    """

    # Add post data
    for post in posts:

        if project_id:
            try:
                content_data = post['editedContent'][company][username].get(project_id)[0]
            except Exception:
                content_data = post.get('content', 'No content available')
        else:
            qc_done_user = post.get(company, {}).get('QC_Done', {}).get('user')
            edited = post.get('editedContent', {}).get(company, {}).get(username, {}).get(username)

            if qc_done_user == username and edited:
                content_data = edited[0]
            else:
                content_data = post.get('content', 'No content available')

        written_by = (post.get('news_at'))

        publishdate = post.get('published_date', 'No date available')
        publishdate = str(publishdate).split(' ')[0]
        dt = datetime.strptime(publishdate, "%Y-%m-%d")
        # Format to desired output
        publishdate = dt.strftime("%d-%m-%Y")
       

        notes_html = "<ul>" + "".join(f"<li>{note}</li>" for note in post.get("notes", {}).get(username, [])) + "</ul>"
        observations_html = "<ul>" + "".join(
            f"<li>{observation}</li>" for observation in post.get("observations", {}).get(username, [])) + "</ul>"
        insights_html = "<ul>" + "".join(
            f"<li>{insight}</li>" for insight in post.get("insights", {}).get(username, [])) + "</ul>"

        onlineimages = post.get('image', [])
        uploadedimages = []
        postid = str(post.get('_id'))

        if project_id:
            try:
                uploadedimages = post.get('addedImages', {}).get(company, {}).get(project_id, {}).get(postid, [])
            except Exception:
                uploadedimages = []
        
        # Normalize onlineimages into the same structure as uploadedimages
        normalized_onlineimages = [
            {"path": img, "description": ""}
            for img in onlineimages
            if img and img.strip() != "" and img != "Not Available" and img != "n/a"
        ]
        
        # Ensure uploadedimages is also filtered
        normalized_uploadedimages = [
            img for img in uploadedimages
            if isinstance(img, dict) and img.get("path") and img["path"].strip() != "" and img[
                "path"] != "Not Available" and img["path"] != "n/a"
        ]

        # Combine both
        images = normalized_onlineimages + normalized_uploadedimages

        # Build HTML
        if images:
            image_html = ""
            for i, img in enumerate(images):
                if i % 5 == 0:
                    if i != 0:
                        image_html += "</tr>"  # Close previous row
                    image_html += "<tr>"  # Start a new row

                image_html += f'''
                    <td style="text-align: center; padding: 10px;">
                        <img src="{img["path"]}" alt="Full Preview" style="width:150px; height: 150px; object-fit: cover; cursor: pointer;">
                        {f'<p style="margin-top: 4px; font-size: 12px;">{img["description"]}</p>' if img.get("description") else ""}
                    </td>
                '''

            # Close the last row if not already closed
            if len(images) % 5 != 0:
                image_html += "</tr>"


        else:
            image_html = ""

        pdf_html += f"""
        <div class="post">
            <p><strong>Date:</strong> {publishdate}</p>
            <h3>{post.get('title', 'Untitled')}</h3>
            <div class="written_by">
                <strong>Written By:</strong>
                {written_by}
            </div>
            <div class="content">{content_data}</div>
            {'<table style="width: 100%; border-collapse: collapse;">' if image_html else ""}
                   {image_html} 
            {'</table>}' if image_html else ""}



            <div class="notes">
                {"<strong>Notes:</strong>" if len(post.get("notes", {}).get(username, [])) > 0 else ""}
                {notes_html}
            </div>
            <div class="observations">
                {"<strong>Observations:</strong>" if len(post.get("observations", {}).get(username, [])) > 0 else ""}
                {observations_html}
            </div>
            <div class="insights">
                {"<strong>Insights:</strong>" if len(post.get("insights", {}).get(username, [])) > 0 else ""}
                {insights_html}
            </div>

        </div>
        <hr>
        """

    pdf_html += "</body></html>"
    
    return pdf_html

def create_pdf_bytes(html_content):
    """Generate PDF bytes from HTML content"""
    pdf = BytesIO()
    pisa_status = pisa.CreatePDF(BytesIO(html_content.encode('utf-8')), dest=pdf)
    if pisa_status.err:
        return None
    pdf.seek(0)
    return pdf

@app.route('/api/news/view-pdf', methods=['POST'])
def create_pdf():
    """Generate and download a PDF containing selected posts and header information."""
    username = session.get('username')
    company = session.get('company')
    if not username:
        return jsonify({"success": False, "message": "User not logged in"}), 401

    data = request.json
    
    project_name = data.get("projectName", "Project: Project")  # Default to NEWS if project name is missing
    
    try:
        project_name = project_name.split(":")[1].strip()
    except:
        project_name = project_name

    try:
        # Generate HTML content
        html_content = generate_report_html(data, username, company)

        # Convert to PDF
        pdf =create_pdf_bytes(html_content)
        return Response(
            pdf,
            mimetype="application/pdf",
            headers={"Content-Disposition": "attachment; filename=selected_posts.pdf"}
        )

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500




@app.route('/api/news/view-doc', methods=['POST'])
def create_doc():
    """Generate DOC from HTML report"""
    username = session.get('username')
    company = session.get('company')
    if not username:
        return jsonify({"success": False, "message": "User not logged in"}), 401

    data = request.json
    post_ids = data.get("post_ids", [])
    filters = data.get("filters", {})
    date_range = data.get("dateRange", None)
    search_query = data.get("searchQuery", None)
    project_name = data.get("projectName", "Project: News")  # Default to NEWS if project name is missing
    project_id = data.get("project_id", None)
    try:
        project_name = project_name.split(":")[1].strip()
    except:
        project_name = project_name

    # Initialize variables for cleanup
    pdf_path = None
    docx_path = None
    try:
        # Generate HTML content
        html_content = generate_report_html(data, username, company)


        # Generate PDF in memory
        pdf_buffer = create_pdf_bytes(html_content)
        if not pdf_buffer:
            return jsonify({"success": False, "message": "Error generating PDF"}), 500

        # Create temporary PDF file
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
            tmp_pdf.write(pdf_buffer.getvalue())
            pdf_path = tmp_pdf.name

        # Create temporary DOCX file path
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp_docx:
            docx_path = tmp_docx.name

        # Convert PDF to DOCX
        cv = Converter(pdf_path)
        cv.convert(docx_path)
        cv.close()

        # Read DOCX content into memory
        with open(docx_path, "rb") as docx_file:
            docx_content = BytesIO(docx_file.read())
            

        # Return DOCX response
        return Response(
            docx_content,
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": "attachment; filename=selected_posts.docx"}
        )

    finally:
        # Clean up temporary files in all cases
        if pdf_path and os.path.exists(pdf_path):
            os.unlink(pdf_path)
        if docx_path and os.path.exists(docx_path):
            os.unlink(docx_path)


# Add this function for Social Media HTML generation
def generate_report_html_social(data, username, company):
    post_ids = data.get("post_ids", [])
    filters = data.get("filters", {})
    date_range = data.get("dateRange", None)
    search_query = data.get("searchQuery", None)

    project_name = data.get("projectName", "Project: News")  # Default to NEWS if project name is missing
    project_id = data.get("project_id", None)

    try:
        project_name = project_name.split(":")[1].strip()
    except:
        project_name = project_name

    if not post_ids:
        return jsonify({"success": False, "message": "No posts selected"}), 400

        # Convert post_ids to ObjectId and fetch from database
    try:
        object_ids = [ObjectId(post_id) for post_id in post_ids]
        posts = list(social_collection.find({"_id": {"$in": object_ids}}))
    except Exception as e:
        return jsonify({"success": False, "message": f"Error fetching posts: {str(e)}"}), 500

    if not posts:
        return jsonify({"success": False, "message": "No matching posts found"}), 404

    # Generate HTML content for the PDF
    pdf_html = """
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            h1 { color: #333; text-align: center; font-size: 24px;}
            h2 { color: #333; font-size: 16px; margin-bottom: 5px; text-align: center; }
            h3 { color: #333; font-size: 18px; margin-bottom: 5px; }
            .header { margin-bottom: 40px; }
            .header span { display: block; margin-bottom: 5px; }
            .header img { text-align: center; font-size: 24px;}
            .post { margin-bottom: 40px; }
            .content { margin-top: 10px; font-size: 14px; line-height: 1.5; }
            .highlight { background-color: yellow; } /* Highlighted text */
            .notes { margin-top: 0px; padding: 0px;  margin: 0px;}
            ul { padding-left: 20px; margin: 0px; }
            li { margin: 0px; }
        </style>
    </head>
    <body>
    """

    # Add header information
    pdf_html += f"""
    <div class="header">
        <img src="https://reinlabs.co.in/wp-content/uploads/2019/04/Untitled-design-1.png">
        <h1><strong>{project_name}</strong></h1>
        <h2><strong>Generated By:</strong> {username}</h2>
        {"<span><strong>Date Range:</strong> " + date_range + "</span>" if date_range else ""}
        {"<span><strong>Search Query:</strong> " + search_query + "</span>" if search_query else ""}
        {"<span><strong>Country Filter:</strong> " + filters.get('country') + "</span>" if filters.get('country') and filters.get('country') != "None" else ""}
        {"<span><strong>Site Filter:</strong> " + filters.get('site') + "</span>" if filters.get('site') and filters.get('site') != "None" else ""}
        {"<span><strong>Person Filter:</strong> " + filters.get('person') + "</span>" if filters.get('person') and filters.get('person') != "None" else ""}
    </div>
    <hr>
    """

    # Add post data
    for post in posts:
        person_Name = (post.get("name"))
        if project_id:
            try:
                content_data = post['editedContent'][company][username].get(project_id)[0]
            except Exception:
                content_data = post.get('content', 'No content available')
        else:
            qc_done_user = post.get(company, {}).get('QC_Done', {}).get('user')
            edited = post.get('editedContent', {}).get(company, {}).get(username, {}).get(username)

            if qc_done_user == username and edited:
                content_data = edited[0]
            else:
                content_data = post.get('content', 'No content available')

        notes_html = "<ul>" + "".join(f"<li>{note}</li>" for note in post.get("notes", {}).get(username, [])) + "</ul>"
        observations_html = "<ul>" + "".join(
            f"<li>{observation}</li>" for observation in post.get("observations", {}).get(username, [])) + "</ul>"
        insights_html = "<ul>" + "".join(
            f"<li>{insight}</li>" for insight in post.get("insights", {}).get(username, [])) + "</ul>"

        onlineimages = post.get('image', [])
        uploadedimages = []
        postid = str(post.get('_id'))

        if project_id:
            try:
                uploadedimages = post.get('addedImages', {}).get(company, {}).get(project_id, {}).get(postid, [])
            except Exception:
                uploadedimages = []
        print("Uploaded Images:", uploadedimages)
        print("Online Images:", onlineimages)
        # Normalize onlineimages into the same structure as uploadedimages
        normalized_onlineimages = [
            {"path": img, "description": ""}
            for img in onlineimages
            if img and img.strip() != "" and img != "Not Available" and img != "n/a"
        ]
        print("Normalized Online Images:", normalized_onlineimages)
        # Ensure uploadedimages is also filtered
        normalized_uploadedimages = [
            img for img in uploadedimages
            if isinstance(img, dict) and img.get("path") and img["path"].strip() != "" and img[
                "path"] != "Not Available" and img["path"] != "n/a"
        ]

        # Combine both
        images = normalized_onlineimages + normalized_uploadedimages

        # Build HTML
        if images:
            image_html = ""
            for i, img in enumerate(images):
                if i % 5 == 0:
                    if i != 0:
                        image_html += "</tr>"  # Close previous row
                    image_html += "<tr>"  # Start a new row

                image_html += f'''
                            <td style="text-align: center; padding: 10px;">
                                <img src="{img["path"]}" alt="Full Preview" style="width:150px; height: 150px; object-fit: cover; cursor: pointer;">
                                {f'<p style="margin-top: 4px; font-size: 12px;">{img["description"]}</p>' if img.get("description") else ""}
                            </td>
                        '''

            # Close the last row if not already closed
            if len(images) % 5 != 0:
                image_html += "</tr>"


        else:
            image_html = ""

        pdf_html += f"""
        <div class="post">
            <p><strong>Date:</strong> {post.get('post_date', 'No date available')}</p>
            <h3>{person_Name}</h3>
            <div class="content">{content_data}</div>
            <table style="width: 100%; border-collapse: collapse;">
                    {image_html}
            </table>
            
            <div class="notes">
                {"<strong>Notes:</strong>" if len(post.get("notes", {}).get(username, [])) > 0 else ""}
                {notes_html}
            </div>
            <div class="observations">
                {"<strong>Observations:</strong>" if len(post.get("observations", {}).get(username, [])) > 0 else ""}
                {observations_html}
            </div>
            <div class="insights">
                {"<strong>Insights:</strong>" if len(post.get("insights", {}).get(username, [])) > 0 else ""}
                {insights_html}
            </div>

        </div>
        <hr>
        """

    pdf_html += "</body></html>"
    return pdf_html

@app.route('/api/social/download-doc', methods=['POST'])
def download_doc_social():
    username = session.get('username')
    company = session.get('company')
    if not username:
        return jsonify({"success": False, "message": "User not logged in"}), 401

    data = request.json
    # Initialize variables for cleanup
    pdf_path = None
    docx_path = None
    try:
        # Generate HTML content
        html_content = generate_report_html_social(data, username, company)

        # Generate PDF in memory
        pdf_buffer = create_pdf_bytes(html_content)
        if not pdf_buffer:
            return jsonify({"success": False, "message": "Error generating PDF"}), 500

        # Create temporary files
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
            tmp_pdf.write(pdf_buffer.getvalue())
            pdf_path = tmp_pdf.name

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp_docx:
            docx_path = tmp_docx.name

        # Convert PDF to DOCX
        cv = Converter(pdf_path)
        cv.convert(docx_path)
        cv.close()

        # Read DOCX content
        with open(docx_path, "rb") as docx_file:
            docx_content = BytesIO(docx_file.read())

        return Response(
            docx_content,
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": "attachment; filename=selected_posts.docx"}
        )

    finally:
        # Clean up temporary files
        if pdf_path and os.path.exists(pdf_path):
            os.unlink(pdf_path)
        if docx_path and os.path.exists(docx_path):
            os.unlink(docx_path)

@app.route('/api/social/download-pdf', methods=['POST'])
def create_pdf_social():
    """Generate and download a PDF containing selected posts and header information."""
    username = session.get('username')
    company = session.get('company')
    if not username:
        return jsonify({"success": False, "message": "User not logged in"}), 401

    data = request.json
    post_ids = data.get("post_ids", [])
    filters = data.get("filters", {})
    date_range = data.get("dateRange", None)
    search_query = data.get("searchQuery", None)
    project_name = data.get("projectName", "Project: News")  # Default to NEWS if project name is missing
    project_id = data.get("project_id", None)
    try:
        project_name = project_name.split(":")[1].strip()
    except:
        project_name = project_name

    try:
        # Generate HTML content
        html_content = generate_report_html_social(data, username, company)

        # Convert to PDF
        pdf =create_pdf_bytes(html_content)
        return Response(
            pdf,
            mimetype="application/pdf",
            headers={"Content-Disposition": "attachment; filename=selected_posts.pdf"}
        )

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/view-pdf', methods=['get'])
def render_pdf_template():
    return render_template('pdfview.html')
###########################################################################################################
###########################################################################################################
#####################################  Requests Manegement ################################################
###########################################################################################################
###########################################################################################################


def is_valid_url(url):
    """Validate if the URL is properly formatted."""
    parsed = urlparse(url)
    return bool(parsed.netloc) and bool(parsed.scheme)

@app.route('/api/article-requests', methods=['GET','POST'])
def manage_article_requests():
    username = session.get('username')
    if not username:
        return jsonify({"success": False, "message": "User not logged in"}), 401

    if request.method == 'POST':
        data = request.json
        url = data.get("url")
        if not url:
            return jsonify({"success": False, "message": "URL is required"}), 400

        # Validate the URL
        if not is_valid_url(url):
            return jsonify({"success": False, "message": "Invalid URL provided"}), 400

        # Save the request to the database
        article_requests_collection.insert_one({
            "url": url,
            "status": "pending",  # pending, approved, rejected
            "requested_by": username,
            "requested_at": datetime.now(pytz.timezone('Asia/Kolkata')),
            "actioned_by": None,
            "actioned_at": None
        })
        return jsonify({"success": True, "message": "Article request submitted successfully!"})


    # GET request: Fetch all requests for the user or all requests if admin
    if username == "admin":
        requests = list(article_requests_collection.find({}))  # Admin can see all requests
    else:
        requests = list(article_requests_collection.find({"requested_by": username}))  # Users can only see their own requests

    for req in requests:
        req["_id"] = str(req["_id"])
    return jsonify(requests)

@app.route('/api/article-requests/<request_id>/action', methods=['POST'])
def action_article_request(request_id):
    username = session.get('username')
    if not username or username != "admin":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    data = request.json
    action = data.get("action")  # "approve" or "reject"
    if action not in ["approve", "reject"]:
        return jsonify({"success": False, "message": "Invalid action"}), 400

    # Update the request status
    article_requests_collection.update_one(
        {"_id": ObjectId(request_id)},
        {"$set": {
            "status": "approved" if action == "approve" else "rejected",
            "actioned_by": username,
            "actioned_at": datetime.now(pytz.timezone('Asia/Kolkata'))
        }}
    )
    return jsonify({"success": True, "message": f"Request {action}ed successfully!"})


@app.route('/api/article-requests/admin', methods=['GET'])
def get_admin_article_requests():
    username = session.get('username')
    if not username or username != "admin":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    requests = list(article_requests_collection.find({}))
    for req in requests:
        req["_id"] = str(req["_id"])
    return jsonify(requests)

@app.route('/ArticleRequests')
def article_requests():
    if 'username' in session:
        username = session['username']
        return render_template('ArticleRequests.html', username=username)
    flash('Please log in to access this page.')
    return redirect('/login')

@app.route('/reports')
def reports_page():
    if 'username' in session and 'level' in session:
        username = session['username']
        level = session['level']
        companyid = session['company']
        user_data = users_collection.find_one({"username": username})
        try:
            designation = user_data.get('designation')
        except:
            designation = ''
        try:
            company = user_data.get('company')
        except:
            company = ''
        return render_template(
            'Report-Management.html',
            username=username,
            companyid=companyid,
            company= company,
            level=level,
            designation=designation
        )
    flash('Please log in to access this page.')
    return redirect('/login')

@app.route('/api/article-requests/pending-count', methods=['GET'])
def get_pending_request_count():
    username = session.get('username')
    if username != "admin":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    count = article_requests_collection.count_documents({"status": "pending"})
    return jsonify({"success": True, "count": count})

###################################################################################################
###################################################################################################
################################  Audio   #########################################################
###################################################################################################
###################################################################################################


# Constants
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 1024

# Global variables
RECORDING = False
frames = []
audio = None
stream = None
current_recording_id = None
recordings = {}

# Lock for thread-safe access to global variables
recording_lock = threading.Lock()

def record_audio():
    global RECORDING, frames, stream
    while RECORDING:
        try:
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)
        except Exception as e:
            print(f"Error during recording: {e}")
            break

@app.route('/start_record', methods=['POST'])
def start_record():
    data = request.json
    post_id = data.get('post_id')
    username = data.get('username')

    if not post_id or not username:
        return jsonify(status="Missing post_id or username"), 400

    global RECORDING, frames, audio, stream, current_recording_id

    with recording_lock:
        if RECORDING:
            return jsonify(status="Already recording"), 400

        RECORDING = True
        frames = []
        audio = pyaudio.PyAudio()

        # List all audio devices
        print("Available audio devices:")
        for i in range(audio.get_device_count()):
            device_info = audio.get_device_info_by_index(i)
            print(f"{i}: {device_info['name']} (Input Channels: {device_info['maxInputChannels']})")

        # Select the default input device (or specify the correct index)
        input_device_index = None
        for i in range(audio.get_device_count()):
            device_info = audio.get_device_info_by_index(i)
            if device_info["maxInputChannels"] > 0:  # Check if it's an input device
                input_device_index = i
                break

        if input_device_index is None:
            raise Exception("No input device found!")

        print(f"Using input device: {input_device_index}")

        stream = audio.open(format=FORMAT, channels=CHANNELS,
                            rate=RATE, input=True,
                            frames_per_buffer=CHUNK,
                            input_device_index=input_device_index)

        print(f"Recording started for Post ID: {post_id}, User: {username}")

        # Correct order: post_id comes first
        current_recording_id = f"{post_id}_{username}_{str(uuid.uuid4())}"
        recordings[current_recording_id] = []

        # Start a new thread to record audio
        threading.Thread(target=record_audio).start()

    return jsonify(status="Recording started", recording_id=current_recording_id)

@app.route('/stop_record', methods=['POST'])
def stop_record():
    global RECORDING, frames, audio, stream, current_recording_id

    with recording_lock:
        if not RECORDING:
            return jsonify(status="No active recording"), 400

        RECORDING = False

        # Stop and close the stream
        if stream:
            stream.stop_stream()
            stream.close()
        if audio:
            audio.terminate()

        try:
            data = request.json
            post_id = data.get('post_id')
            username = data.get('username')
            post_type = data.get('post_type', 'news')  # Default to 'news' if not provided

            if not post_id or not username:
                return jsonify(status="Missing post_id or username"), 400

            # Determine the collection based on the post type
            if post_type == 'news':
                collection = news_collection
            elif post_type == 'social':
                collection = social_collection
            else:
                return jsonify(status="Invalid post type"), 400

            # Save voice note file without a title initially
            unique_id = str(uuid.uuid4())
            full_filename = f"static/voice_note_{post_id}_{username}_{unique_id}.wav"
            filename = full_filename.replace("static/", "")  # Remove `/static/`
            with wave.open(full_filename, 'wb') as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(audio.get_sample_size(FORMAT))
                wf.setframerate(RATE)
                wf.writeframes(b''.join(frames))

            # If `voice_notes_files` does not exist, initialize it
            post = collection.find_one({"_id": ObjectId(post_id)}, {"voice_notes_files": 1})
            if not post or "voice_notes_files" not in post or not isinstance(post["voice_notes_files"], dict):
                collection.update_one(
                    {"_id": ObjectId(post_id)},
                    {"$set": {"voice_notes_files": {}}}
                )

            # Add voice note filename without a title initially
            update_result = collection.update_one(
                {"_id": ObjectId(post_id)},
                {"$push": {f"voice_notes_files.{username}": {"filename": filename, "title": ""}}}
            )

            if update_result.modified_count == 0:
                print(f"Warning: No document updated for post_id {post_id}")

        except Exception as e:
            print(f"Error: {e}")
            return jsonify(status="Error saving recording"), 500

    return jsonify(status="Recording saved", file_url=filename, unique_id=unique_id)


@app.route('/update_recording_title', methods=['POST'])
def update_recording_title():
    username = session.get('username')
    if not username:
        return jsonify(status="Unauthorized"), 401

    data = request.json
    post_id = data.get('post_id')
    filename = data.get('filename')
    title = data.get('title')
    post_type = data.get('post_type', 'news')  # Default to 'news' if not provided

    if not post_id or not filename or not title:
        return jsonify(status="Missing post_id, filename, or title"), 400

    # Determine the collection based on the post type
    if post_type == 'news':
        collection = news_collection
    elif post_type == 'social':
        collection = social_collection
    else:
        return jsonify(status="Invalid post type"), 400

    # Check if the title already exists for this post and user
    existing_recording = collection.find_one(
        {
            "_id": ObjectId(post_id),
            f"voice_notes_files.{username}": {
                "$elemMatch": {"title": title}
            }
        }
    )

    if existing_recording:
        return jsonify(status="Title already exists for this post and user"), 400

    # Update the title for the recording
    update_result = collection.update_one(
        {"_id": ObjectId(post_id), f"voice_notes_files.{username}.filename": filename},
        {"$set": {f"voice_notes_files.{username}.$.title": title}}
    )

    if update_result.modified_count == 0:
        return jsonify(status="Failed to update title"), 400

    return jsonify(status="Title updated successfully")
@app.route('/get_recordings/<post_id>', methods=['GET'])
def get_recordings(post_id):
    username = session.get('username')  # Get logged-in user from session
    if not username:
        return jsonify(status="Unauthorized"), 401

    try:
        post_type = request.args.get('post_type', 'news')  # Default to 'news' if not provided

        if post_type == 'news':
            collection = news_collection
        elif post_type == 'social':
            collection = social_collection
        else:
            return jsonify(status="Invalid post type"), 400

        post = collection.find_one({"_id": ObjectId(post_id)}, {"voice_notes_files": 1})

        if not post or "voice_notes_files" not in post:
            return jsonify(recordings=[])

        # Regular users only see their own voice notes
        user_recordings = post["voice_notes_files"].get(username, [])
        return jsonify(recordings=user_recordings)

    except Exception as e:
        print("Error:", e)
        return jsonify(status="Invalid post ID"), 400


@app.route('/delete_recording/<filename>', methods=['DELETE'])
def delete_recording(filename):
    username = session.get('username')  # Get logged-in user from session
    if not username:
        return jsonify(status="Unauthorized"), 401

    post_type = request.args.get('post_type', 'news')  # Default to 'news' if not provided

    if post_type == 'news':
        collection = news_collection
    elif post_type == 'social':
        collection = social_collection
    else:
        return jsonify(status="Invalid post type"), 400

    # Remove file from storage
    file_path = os.path.join('static', filename)
    if os.path.exists(file_path):
        os.remove(file_path)

        # Remove file reference from the collection
        collection.update_one(
            {f"voice_notes_files.{username}.filename": filename},
            {"$pull": {f"voice_notes_files.{username}": {"filename": filename}}}
        )

        return jsonify(status="File deleted successfully")
    else:
        return jsonify(status="File not found"), 404

###############################################################################################
@app.route('/api/admin/usage-metrics', methods=['GET'])
def get_admin_usage_metrics():
    username = session.get('username')
    if not username or username != "admin":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    try:
        # Get date filter from query params (default to today)
        activity_date_str = request.args.get('activity_date', datetime.utcnow().strftime('%Y-%m-%d'))
        activity_date = datetime.strptime(activity_date_str, '%Y-%m-%d')
        activity_date_start = activity_date.replace(hour=0, minute=0, second=0, microsecond=0)
        activity_date_end = activity_date_start + timedelta(days=1)

        # Calculate date range (last 5 days) for the date-wise metrics
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        dates = [(today - timedelta(days=i)).strftime('%d-%m-%Y') for i in range(4, -1, -1)]

        # Get users who logged in today (for the user-wise table)
        pipeline = [
            {
                "$match": {
                    "action_type": "user_login",
                    "timestamp": {"$gte": activity_date_start, "$lt": activity_date_end}
                }
            },
            {"$group": {"_id": "$username"}},
            {"$sort": {"_id": 1}}
        ]
        today_active_users = [user['_id'] for user in usage_collection.aggregate(pipeline)]

        # Initialize result structure
        result = {
            "dates": dates,
            "user_names": today_active_users,  # Only today's active users
            "activity_date": activity_date_str,  # The date being shown for user activity
            "date_metrics": [],
            "user_metrics": []
        }

        # Define the metrics we want to track
        metric_types = [
            {"name": "Users logged in", "action": "user_login", "count_unique": True},
            {"name": "Projects created", "action": "project_created"},
            {"name": "Reports generated", "action": "report_downloaded"},
            {"name": "Articles added to projects", "action": "posts_added_to_project"},
            {"name": "Data changes", "actions": ["content_edited", "note_added", "observation_added", "insight_added"], "count_unique_posts": True},
            {"name": "Reports uploaded", "action": "report_uploaded"}
        ]

        # Helper function to safely get aggregation result
        def get_aggregation_count(pipeline, count_field="count"):
            try:
                result = list(usage_collection.aggregate(pipeline))
                return result[0].get(count_field, 0) if result else 0
            except Exception as e:
                return 0

        # Get date-wise metrics (unchanged)
        for metric in metric_types:
            metric_data = {"name": metric["name"], "counts": []}
            for date_str in dates:
                date = datetime.strptime(date_str, '%d-%m-%Y')
                next_day = date + timedelta(days=1)

                query = {"timestamp": {"$gte": date, "$lt": next_day}}

                if "actions" in metric:
                    query['$or'] = [{'action_type': action} for action in metric["actions"]]
                else:
                    query['action_type'] = metric["action"]

                if metric.get("count_unique"):
                    pipeline = [
                        {"$match": query},
                        {"$group": {"_id": "$username"}},
                        {"$count": "count"}
                    ]
                    count = get_aggregation_count(pipeline)
                elif metric.get("count_unique_posts"):
                    pipeline = [
                        {"$match": query},
                        {"$group": {"_id": "$details.Article_id"}},
                        {"$count": "unique_posts"}
                    ]
                    count = get_aggregation_count(pipeline, "unique_posts")
                else:
                    count = usage_collection.count_documents(query)

                metric_data["counts"].append(count)

            result["date_metrics"].append(metric_data)

        # Get user-wise metrics for the selected activity date
        for metric in metric_types:
            metric_data = {"name": metric["name"], "counts": []}
            for user in today_active_users:
                query = {
                    'username': user,
                    'timestamp': {'$gte': activity_date_start, '$lt': activity_date_end}
                }

                if "actions" in metric:
                    query['$or'] = [{'action_type': action} for action in metric["actions"]]
                else:
                    query['action_type'] = metric["action"]

                if metric.get("count_unique"):
                    # For logins, count all login actions (not unique)
                    count = usage_collection.count_documents(query)
                elif metric.get("count_unique_posts"):
                    pipeline = [
                        {"$match": query},
                        {"$group": {"_id": "$details.Article_id"}},
                        {"$count": "unique_posts"}
                    ]
                    count = get_aggregation_count(pipeline, "unique_posts")
                else:
                    count = usage_collection.count_documents(query)

                metric_data["counts"].append(count)

            result["user_metrics"].append(metric_data)

        return jsonify({"success": True, "data": result})

    except Exception as e:
        return jsonify({"success": False, "message": "Error generating metrics"}), 500
    
@app.route('/analytics')
def analytics_page():
    """
    Render the analytics page.
    """
    if 'username' not in session:
        return render_template('login.html')
    if 'username' in session and 'level' in session:
        username = session['username']
        level = session['level']
        companyid = session['company']
        user_data = users_collection.find_one({"username": username})
        try:
            designation = user_data.get('designation')
        except:
            designation = ''
        try:
            company = user_data.get('company')
        except:
            company = ''
    
        return render_template('analytics.html', username=username, level=level,companyid=companyid, designation=designation, company=company)

@app.errorhandler(404)
def page_not_found(e):
    return "404 - Page Not Found", 404

@app.errorhandler(500)
def internal_server_error(e):
    return "500 - Internal Server Error", 500




if __name__ == '__main__':
    # from waitress import serve  # Recommended for Windows
    # serve(app, host="0.0.0.0", port=5000, threads=16)
    app.run(debug=True)
