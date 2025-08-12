from flask import Blueprint, request, session, redirect, render_template, flash, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from models import users_collection, news_collection, social_collection, projects_collection
from werkzeug.utils import secure_filename
import os
from bson.objectid import ObjectId
from datetime import datetime, timedelta
from copy import deepcopy
from routes.tracking import track_action

projects_bp = Blueprint('projects', __name__)

def get_data_from_db(collection, query, skip=0, limit=20, sort=None):
    """Fetch data from MongoDB with pagination and filters."""
    data = list(collection.find(query).sort(sort).skip(skip).limit(limit))
    for document in data:
        document['_id'] = str(document['_id'])
    return data
@projects_bp.route('/', methods=['GET', 'POST'])
def manage_projects():
    """Create a new project folder or retrieve all projects for the logged-in user."""
    username = session.get('username')
    if not username:
        return jsonify({"success": False, "message": "User not logged in"}), 401

    if request.method == 'POST':
        data = request.json
        project_name = data.get("name")

        if not project_name:
            return jsonify({"success": False, "message": "Project name is required"}), 400

        existing_project = projects_collection.find_one({"name": project_name, "owner": username})
        if existing_project:
            return jsonify({"success": False, "message": "Project already exists"}), 400

        project_id = projects_collection.insert_one({"name": project_name, "owner": username}).inserted_id
        current_app.logger.info(f"Project created: {project_name} by {username}")
        track_action('project_created', {'project_id': str(project_id), 'project_name': project_name})

        return jsonify({"success": True, "project_id": str(project_id)})

    # Retrieve projects with post count
    projects = list(projects_collection.find({"owner": username}, {"_id": 1, "name": 1}))
    for project in projects:
        project["_id"] = str(project["_id"])
        project["post_count"] = (
            news_collection.count_documents({"projects": project["_id"]}) +
            social_collection.count_documents({"projects": project["_id"]})
        )

    return jsonify(projects)



@projects_bp.route('/<project_id>', methods=['GET'])
def get_project_data(project_id):
    username = session.get('username')
    if not username:
        return jsonify({"success": False, "message": "User not logged in"}), 401
    project_id = request.args.get('project_id')
    session['project_id'] = project_id
    level = request.args.get('level')
    country = request.args.get('country')
    publisian = request.args.get('publisian')
    sector = request.args.get('sector')
    site = request.args.get('site')
    person = request.args.get('person')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    search = request.args.get('search')  # Get search query
    skip = int(request.args.get('skip', 0))
    limit = int(request.args.get('limit', 20))
    qcdone = request.args.get('qc_done')
    filter_tags = request.args.get('filter_tag')  # Get tags from request
    query = {}
    query2 = {}
    if project_id:
        query["projects"] = project_id
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
    # Apply search query with case-insensitive regex
    if search:
        query["$or"] = [  # Search in multiple fields
            {"title": {"$regex": search, "$options": "i"}},  # Case-insensitive search in title
            {"content": {"$regex": search, "$options": "i"}}  # Case-insensitive search in content
        ]
    query2 = deepcopy(query)  # Create a copy of the query for the second collection
    # Apply date range filter
    if start_date and end_date:
        try:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")+ timedelta(days=1)
            query["published_date"] = {
                "$gte": start_date_obj,
                "$lt": end_date_obj  # Use $lt if you added +1 day to make it inclusive
            }
            query2["post_date"] = {
                "$gte": start_date_obj,
                "$lt": end_date_obj
            }
            
        except ValueError:
            return jsonify({"error": "Invalid date format"}), 400
    
    
    try:
        project = projects_collection.find_one({"_id": ObjectId(project_id), "owner": username})
        if not project:
            return jsonify({"success": False, "message": "Project not found"}), 404

        post_ids = project.get("posts", [])
        query["_id"] = {"$in": [ObjectId(pid) for pid in post_ids if ObjectId.is_valid(pid)]}
        query2["_id"] = {"$in": [ObjectId(pid) for pid in post_ids if ObjectId.is_valid(pid)]}
        # Fetch news and social posts separately
        news_posts = get_data_from_db(news_collection, query, skip=skip, limit=limit, sort=[("published_date", -1)])
        social_posts = get_data_from_db(social_collection, query2, skip=skip, limit=limit, sort=[("post_date", -1)])

        # count the totla number of posts
        total_news_posts = news_collection.count_documents(query)
        total_social_posts = social_collection.count_documents(query2)
        total_posts = total_news_posts + total_social_posts
        
        all_posts = news_posts + social_posts
        for post in all_posts:
            post['_id'] = str(post['_id'])

        return jsonify({
            "all_posts": all_posts,
            "total_posts": total_posts,
            "project": {
                "_id": str(project["_id"]),
                "name": project["name"],
                "owner": project["owner"],
                # "posts": post_ids
            }
        })

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    

@projects_bp.route('/<project_id>/remove', methods=['POST'])
def remove_posts_from_project(project_id):
    """Add multiple posts to a project."""
    username = session.get('username')
    if not username:
        return jsonify({"success": False, "message": "User not logged in"}), 401

    data = request.json
    post_ids = data.get("post_ids", [])  # List of post IDs
    post_type = data.get("post_type")

    if not post_ids or not post_type:
        return jsonify({"success": False, "message": "Post IDs and type are required"}), 400

    collection = news_collection if post_type == "news" else social_collection
    valid_post_ids = [ObjectId(post_id) for post_id in post_ids if ObjectId.is_valid(post_id)]

    # Validate posts
    posts = list(collection.find({"_id": {"$in": valid_post_ids}}))
    if len(posts) != len(valid_post_ids):
        return jsonify({"success": False, "message": "One or more posts not found"}), 404

    # Update project and posts
    projects_collection.update_one(
    {"_id": ObjectId(project_id)},
    {"$pull": {"posts": {"$in": [str(post["_id"]) for post in posts]}}}
    )


    collection.update_many(
        {"_id": {"$in": valid_post_ids}},
        {"$pull": {"projects": project_id}}
    )
    current_app.logger.info(f"Posts removed from project {project_id} by {username}")
    return jsonify({"success": True, "message": "Posts remove from project successfully!"})


@projects_bp.route('/<project_id>/posts', methods=['POST'])
def add_posts_to_project(project_id):
    """Add multiple posts to a project."""
    username = session.get('username')
    if not username:
        return jsonify({"success": False, "message": "User not logged in"}), 401

    data = request.json
    post_ids = data.get("post_ids", [])  # List of post IDs
    post_type = data.get("post_type")

    if not post_ids or not post_type:
        return jsonify({"success": False, "message": "Post IDs and type are required"}), 400

    collection = news_collection if post_type == "news" else social_collection
    valid_post_ids = [ObjectId(post_id) for post_id in post_ids if ObjectId.is_valid(post_id)]

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
        'post_count': len(post_ids),
        'post_type': post_type
    })

    return jsonify({"success": True, "message": "Posts added to project successfully!"})


@projects_bp.route('/<project_id>/remove_post', methods=['POST'])
def remove_post_from_project(project_id):
    """Remove a post from a project without deleting the project itself."""
    username = session.get('username')
    if not username:
        return jsonify({"success": False, "message": "User not logged in"}), 401

    try:
        data = request.json
        post_id = data.get("post_id")
        post_type = data.get("post_type")

        if not post_id or not post_type:
            return jsonify({"success": False, "message": "Post ID and type required"}), 400

        collection = news_collection if post_type == "news" else social_collection
        post = collection.find_one({"_id": ObjectId(post_id)})

        if not post:
            return jsonify({"success": False, "message": "Post not found"}), 404

        # Remove post reference from the project
        projects_collection.update_one(
            {"_id": ObjectId(project_id)},
            {"$pull": {"posts": post_id}}
        )

        # Remove project reference from the post document
        collection.update_one(
            {"_id": ObjectId(post_id)},
            {"$pull": {"projects": project_id}}
        )

        return jsonify({"success": True, "message": "Post removed from project!"})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    


@projects_bp.route('/<project_id>/delete', methods=['DELETE'])
def delete_project(project_id):
    """Delete a project and remove its reference from posts."""
    username = session.get('username')
    if not username:
        return jsonify({"success": False, "message": "User not logged in"}), 401

    try:
        project = projects_collection.find_one({"_id": ObjectId(project_id), "owner": username})
        if not project:
            return jsonify({"success": False, "message": "Project not found"}), 404

        # Remove project ID from posts in news and social collections
        news_collection.update_many(
            {"projects": project_id},
            {"$pull": {"projects": project_id}}
        )
        social_collection.update_many(
            {"projects": project_id},
            {"$pull": {"projects": project_id}}
        )

        # Delete the project from the projects collection
        projects_collection.delete_one({"_id": ObjectId(project_id)})
        current_app.logger.info(f"Project deleted: {project['name']} by {username}")
        session.pop('project_id', None)  # Clear project_id from session if it was
        return jsonify({"success": True, "message": "Project deleted successfully!"})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    

@projects_bp.route('/ids', methods=['GET'])
def get_news_ids():
    """Fetch only the IDs of all posts matching the query."""
    username = session.get('username')
    if not username:
        return jsonify({"success": False, "message": "User not logged in"}), 401

    # Extract query parameters
    country = request.args.get('country')
    publisian = request.args.get('publisian')
    sector = request.args.get('sector')
    person = request.args.get('person')
    site = request.args.get('site')
    filter_tags = request.args.get('filter_tag')  # Get tags from request
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    search = request.args.get('search')
    qcdone = request.args.get('qc_done')
    project_id = request.args.get('project_id')
    company = session.get('company')
    # Build the query
    query = {}
    query2 = {}
    if country:
        query["country"] = {"$in": country.split(",")}
    if sector:
        query["sector"] = {"$in": sector.split(",")}
    if publisian:
        query["publisian"] = {"$in": publisian.split(",")}
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
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"content": {"$regex": search, "$options": "i"}},
        ]
    # Apply date range filter
    query2 = deepcopy(query)  # Create a copy of the query for the second collection
    if start_date and end_date:
        try:

            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            query["published_date"] = {
                "$gte": start_date_obj,
                "$lt": end_date_obj  # Use $lt if you added +1 day to make it inclusive
            }
            query2["post_date"] = {
                "$gte": start_date_obj,
                "$lt": end_date_obj
            }

        except ValueError:
            return jsonify({"error": "Invalid date format"}), 400
    


    # Fetch only the IDs of matching posts
    post_ids1 = [str(post["_id"]) for post in news_collection.find(query, {"_id": 1})]
    post_ids2 = [str(post["_id"]) for post in social_collection.find(query2, {"_id": 1})]
    post_ids = post_ids1 + post_ids2
    return jsonify({"success": True, "post_ids": post_ids})