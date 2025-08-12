from flask import Blueprint, request, session, redirect, render_template, flash, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from models import users_collection,projects_collection, s3_client
from werkzeug.utils import secure_filename
import os
from bson.objectid import ObjectId
import boto3
from botocore.exceptions import ClientError
# routes/image_routes.py
document_bp = Blueprint('document_bp', __name__)

ALLOWED_EXTENSIONS = {'pdf', 'docx', 'xlsx', 'txt', 'pptx', 'ppt', 'jpg', 'jpeg', 'png', 'gif'}
S3_BUCKET = 'newstagging'
S3_FOLDER = 'uploaded_documents'


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@document_bp.route('/upload', methods=['POST'])
def upload():
    username = session['username']
    companyid = session['company']
    if 'doc' not in request.files:
        return 'No file part'
    file = request.files['doc']
    if file.filename == '':
        return 'No selected file'
    project_id = request.form.get('project_id', 'default')
    description = request.form.get('description', '')

    
    if file and allowed_file(file.filename):
        stored_filename = secure_filename(file.filename)
        s3_key = f"{S3_FOLDER}/{companyid}/{username}/{project_id}/{stored_filename}"
        
        # Check for duplicate in S3
        try:
            s3_client.head_object(Bucket=S3_BUCKET, Key=s3_key)
            return jsonify({"error": "File name already exists"}), 400
        except ClientError as e:
            if e.response['Error']['Code'] != '404':
                return jsonify({"error": "Error checking S3"}), 500
        
        
        try:
            object_id = ObjectId(project_id)
        except:
            return jsonify({"message": "Invalid _id format."}), 400
        

        # original_filename = secure_filename(file.filename)
        # Upload to S3
        s3_client.upload_fileobj(file, S3_BUCKET, s3_key)
        file_url = f"https://{S3_BUCKET}.s3.ap-south-1.amazonaws.com/{s3_key}"
        query = {"_id": object_id}
        update = {
        "$push": {
            f"addedDocuments.{companyid}.{username}.{project_id}": {
                "file_name": stored_filename,
                "path": file_url,
                "description": description
            }
        }
    }
        result = projects_collection.update_one(query, update)  # , upsert=False
        current_app.logger.info(f"Updated project {project_id} with new document: {stored_filename} by {username}")
        return jsonify({"file_name":stored_filename,"file_url": file_url, "file_description": description}), 200
    else:
        print(f"File with extension {file.filename.split('.')[-1]} is not allowed")
        return jsonify({"error": "File with extension pdf, docx, xlsx, txt are allowed"}), 500


@document_bp.route('/list-documents/<project_id>')
def list_images(project_id):
    username = session['username']
    companyid = session['company']
    try:
        object_id = ObjectId(project_id)
    except:
        return jsonify({"message": "Invalid _id format."}), 400
    
    try:
        query = {"_id": object_id}
        project = projects_collection.find_one(query)
        if not project:
            return jsonify({"message": "Project not found"}), 404
        documents = project.get('addedDocuments', {}).get(companyid, {}).get(username, {}).get(project_id, [])
        return jsonify(documents), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@document_bp.route('/delete', methods=['POST'])
def delete_image():
    data = request.json
    companyid = session['company']
    username = session['username']
    description = data.get('file_description')
    file_url = data.get('file_url')
    fileName = data.get('file_name')
    project_id = data.get('project_id', 'default')
    
    try:
        object_id = ObjectId(project_id)
    except:
        return jsonify({"message": "Invalid _id format."}), 400
    print(f"Deleting image with URL: {file_url} for  project_id: {project_id}")
    query = {"_id": object_id}
    update = {
        "$pull": {
            f"addedDocuments.{companyid}.{username}.{project_id}": {
                "file_name": fileName,
                "path": file_url,
                "description": description
            }
        }
    }
    projects_collection.update_one(query, update)

    prefix = f"https://{S3_BUCKET}.s3.ap-south-1.amazonaws.com/"
    if file_url.startswith(prefix):
        key = file_url[len(prefix):]
    else:
        # if you stored relative paths, adjust accordingly:
        key = file_url.lstrip('/')
    print(f"Deleting S3 object with key: {key}")
    try:
        s3_client.delete_object(Bucket=S3_BUCKET, Key=key)
    except Exception as e:
        # optionally log the error, but we've already removed the DB reference
        current_app.logger.error(f"S3 delete failed for {key}: {e}")
    current_app.logger.info(f"Document deleted from project {project_id} by {username}: {fileName}")
    return jsonify({"message": "Document deleted successfully."})

@document_bp.route('/download/<project_id>/<filename>')
def download_file(project_id, filename):
    if 'username' not in session:
        return render_template('login.html')
    username = session['username']
    companyid = session['company']
    try:
        object_id = ObjectId(project_id)
    except:
        return "Invalid project ID format", 400
    # Find the project
    project = projects_collection.find_one({"_id": object_id})
    if not project:
        return "Project not found", 404
    # Find the document in the project
    document = project.get('addedDocuments', {}).get(companyid, {}).get(username, {}).get(project_id, [])
    if not document:
        return "No documents found for this project", 404
    report = next((doc for doc in document if doc['file_name'] == filename), None)
    base_url = f"https://{S3_BUCKET}.s3.ap-south-1.amazonaws.com/"
    path = report.get('path', '')
    if not path.startswith(base_url):
        return "Invalid document path", 400
    # Extract the S3 key from the path
    s3_key = path[len(base_url):]
    

    if not report:
        return "File not found", 404

    
    if not s3_key:
        return "S3 file path not found", 500

    # Generate signed URL valid for 1 hour
    try:
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_BUCKET, 'Key': s3_key},
            ExpiresIn=3600
        )
    except ClientError as e:
        return str(e), 500
    current_app.logger.info(f"Document downloaded by {username}: {filename} from project {project_id}")
    return redirect(url)