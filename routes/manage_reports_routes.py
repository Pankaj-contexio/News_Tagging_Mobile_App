from flask import Flask, jsonify, request, render_template, redirect, url_for, session, flash,Response, send_file,send_from_directory, Blueprint
import boto3
from botocore.exceptions import ClientError
from werkzeug.utils import secure_filename
from datetime import datetime
from bson.objectid import ObjectId
from models import Report_collection, s3_client
from routes.tracking import track_action

##########################################################################################################
##########################################################################################################
####################################### Report Management ################################################
##########################################################################################################
##########################################################################################################
reports_bp = Blueprint('reports', __name__)
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'csv'}


S3_BUCKET = 'newstagging'
S3_FOLDER = 'uploaded_reports'




def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS






@reports_bp.route('/api/upload_report', methods=['POST'])
def upload_report():
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    report_type = request.form.get('report_type')
    report_date = request.form.get('report_date')
    country = request.form.get('country')
    sector = request.form.get('sector')
    file = request.files.get('file')


    if not file or file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "File type not allowed"}), 400

    if not report_type or not report_date:
        return jsonify({"error": "Missing report type or date"}), 400

    # company_dir = secure_filename(session['company'])
    # user_dir = secure_filename(session['username'])
    # save_dir = os.path.join(app.config['UPLOAD_FOLDER'], company_dir, user_dir)
    # os.makedirs(save_dir, exist_ok=True)

        # Handle date based on report type
    if report_type == 'weekly' or report_type == 'monthly':
        try:
            date_range = report_date.split(' to ')
            if len(date_range) != 2:
                return jsonify({"error": "Invalid date range format"}), 400
            start_date = datetime.strptime(date_range[0].strip(), '%Y-%m-%d')
            end_date = datetime.strptime(date_range[1].strip(), '%Y-%m-%d')
        except ValueError:
                return jsonify({"error": "Invalid date range format"}), 400


    else:  # weekly or monthly
        try:
            report_date_obj = datetime.strptime(report_date, '%Y-%m-%d')
            start_date = end_date = report_date_obj
        except ValueError:
            return jsonify({"error": "Invalid date format for daily report"}), 400


    stored_filename = secure_filename(file.filename)
    s3_key = f"{S3_FOLDER}/{session['company']}/{session['username']}/{stored_filename}"

    # # Check for duplicate in S3
    # try:
    #     s3_client.head_object(Bucket=S3_BUCKET, Key=s3_key)
    #     return jsonify({"error": "File name already exists"}), 400
    # except ClientError as e:
    #     if e.response['Error']['Code'] != '404':
    #         return jsonify({"error": "Error checking S3"}), 500

    original_filename = secure_filename(file.filename)
    # Upload to S3
    s3_client.upload_fileobj(file, S3_BUCKET, s3_key)

    # #  Check in both DB and file system for duplicate
    # existing_report = Report_collection.find_one({
    #     "company": session['company'],
    #     "user": session['username'],
    #     "original_filename": original_filename
    # })
    # if existing_report or os.path.exists(file_path):
    #     return jsonify({"error": "File name already exists"}), 400
    #
    # # ✅ Save only after passing all checks
    # file.save(file_path)

    report_data = {
        "original_filename": original_filename,
        "stored_filename": original_filename,
        "report_type": report_type,
        "report_date": start_date,  # Store start date
        "report_end_date": end_date if report_type in ['weekly', 'monthly'] else None,  # Store end date for range
        "upload_date": datetime.utcnow(),
        "country": country,
        "sector": sector,
        "uploaded_by": session['username'],
        "company": session['company'],
        "s3_key": s3_key
    }

    track_action('report_uploaded', {
        'report_type': report_type,
        'file_name': stored_filename,
    })

    Report_collection.insert_one(report_data)

    return jsonify({"success": True, "message": "File uploaded successfully"}), 200


@reports_bp.route('/api/get_reports', methods=['GET'])
def get_reports():
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    # Get pagination and filter parameters
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('pageSize', 10))
    report_type = request.args.get('type')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    search_term = request.args.get('search')

    # Build query
    query = {"company": session['company']}

    if search_term:
        search_regex = {'$regex': f'.*{search_term}.*', '$options': 'i'}  # Case-insensitive regex
        query['$or'] = [
            {'original_filename': search_regex},
            {'report_type': search_regex},
            {'country': search_regex},
            {'sector': search_regex},
            {'uploaded_by': search_regex}
        ]

    total_count = Report_collection.count_documents(query)

    # Calculate skip value
    skip = (page - 1) * page_size

    reports = list(Report_collection.find(query)
                   .sort("upload_date", -1)
                   .skip(skip)
                   .limit(page_size))

    # Prepare response
    report_list = []
    for report in reports:

        
        date_display = report["report_date"].strftime('%Y-%m-%d')
        if report.get("report_end_date"):
            date_display += f" to {report['report_end_date'].strftime('%Y-%m-%d')}"

        report_list.append({
            "id": str(report["_id"]),
            "original_filename": report["original_filename"],
            "uploaded_by": report["uploaded_by"],
            "report_type": report["report_type"].capitalize(),
            "report_date": date_display,
            "upload_date": report["upload_date"].strftime('%Y-%m-%d %H:%M'),
            "country": report.get("country", ""),
            "sector": report.get("sector", ""),
            "path": f"/download/{report['stored_filename']}"
        })

    return jsonify({
        "reports": report_list,
        "totalCount": total_count
    })

@reports_bp.route('/download/<filename>')
def download_file(filename):
    if 'username' not in session:
        return redirect(url_for('login'))

    report = Report_collection.find_one({
        "stored_filename": filename,
        "company": session['company']
    })

    if not report:
        return "File not found", 404

    s3_key = report.get('s3_key')
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

    return redirect(url)
@reports_bp.route('/api/delete_report/<report_id>', methods=['DELETE'])
def delete_report(report_id):
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    report = Report_collection.find_one({"_id": ObjectId(report_id)})
    if not report:
        return jsonify({"error": "Report not found"}), 404

    if session['level'] != 'admin' and report['uploaded_by'] != session['username']:
        return jsonify({"error": "Access denied"}), 403

    s3_key = report.get('s3_key')
    if s3_key:
        try:
            s3_client.delete_object(Bucket=S3_BUCKET, Key=s3_key)
        except ClientError as e:
            print(f"S3 delete error: {e}")

    Report_collection.delete_one({"_id": ObjectId(report_id)})
    return jsonify({"success": True, "message": "Report deleted successfully"})