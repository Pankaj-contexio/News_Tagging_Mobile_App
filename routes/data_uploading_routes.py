from flask import Blueprint, request, render_template, redirect, url_for, flash
import pandas as pd
import re
import os
from werkzeug.utils import secure_filename
from models import news_collection, social_collection

data_uploading_bp = Blueprint('data_uploading', __name__)

UPLOAD_FOLDER = './uploads'
ALLOWED_EXTENSIONS = {'xlsx'}

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@data_uploading_bp.route('/upload_excel', methods=['GET', 'POST'])
def upload_excel():
    if request.method == 'POST':
        if 'excel_file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['excel_file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            # Process the uploaded Excel file
            summary, skipped_path = process_excel(filepath)
            flash(f"Upload complete. {summary}")
            if skipped_path:
                flash(f"Skipped records saved to: {skipped_path}")
            return redirect(request.url)
        else:
            flash('Invalid file type. Only .xlsx allowed.')
            return redirect(request.url)
    return render_template('upload_excel.html')

def process_excel(filepath):
    # MongoDB setup
    

    data = pd.read_excel(filepath)
    data.columns = data.columns.str.strip().str.lower()
    data = data.fillna('Not Available')
    data = data.replace(['', 'N/A', 'n/a', None], 'Not Available', regex=True)

    def is_valid_published_date(value):
        if value == 'Not Available':
            return False
        try:
            date = pd.to_datetime(value, errors='raise')
            value_str = str(value)
            pattern = r"^\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:\d{2}|Z)?)?$"
            return bool(re.match(pattern, value_str))
        except Exception:
            return False

    allowed_countries = {'country_1', 'country_2', 'country_3', 'country_4', 'country_5', 'country_150'}
    def is_valid_country(value):
        if value == 'Not Available':
            return False
        value = str(value).strip()
        return value in allowed_countries

    allowed_sectors = {'sector_1', 'sector_2', 'sector_3', 'sector_4'}
    def is_valid_sector(value):
        if value == 'Not Available':
            return False
        value = str(value).strip()
        return value in allowed_sectors

    allowed_publisian = {'publisian_1', 'publisian_2', 'publisian_3', 'publisian_4','publisian_5','publisian_6','publisian_7','publisian_8',
                        'publisian_9', 'publisian_10', 'publisian_11', 'publisian_12', 'publisian_13', 'publisian_14','publisian_15','publisian_16',
                        'publisian_17', 'publisian_18', 'publisian_19', 'publisian_20', 'publisian_21', 'publisian_22','publisian_23','publisian_24','publisian_25','publisian_26'}
    def is_valid_publisian(value):
        if value == 'Not Available':
            return False
        value = str(value).strip()
        return value in allowed_publisian

    skipped_records = []
    inserted_count = 0
    skipped_count = 0

    for index, row in data.iterrows():
        if 'post_link' in row and row['post_link'] != 'Not Available':
            news_url = row['post_link']
            if 'post_date' in row and not is_valid_published_date(row['post_date']):
                reason = f"Invalid published_date: {row['post_date']}"
                skipped_records.append({'news_url': news_url, 'reason': reason})
                skipped_count += 1
                continue
            if 'country' in row:
                country_cleaned = str(row['country']).strip()
                if not is_valid_country(country_cleaned):
                    reason = f"Invalid country: {row['country']}"
                    skipped_records.append({'news_url': news_url, 'reason': reason})
                    skipped_count += 1
                    continue
                else:
                    row['country'] = country_cleaned
            else:
                reason = "Missing country field"
                skipped_records.append({'news_url': news_url, 'reason': reason})
                skipped_count += 1
                continue
            if not news_collection.find_one({'post_link': news_url}):
                document = row.to_dict()
                if 'image' in row and pd.notna(row['image']):
                    document['image'] = [img.strip() for img in str(row['image']).split(',')]
                else:
                    document['image'] = []
                if 'post_date' in document and document['post_date'] != 'Not Available':
                    document['post_date'] = pd.to_datetime(document['post_date'])
                news_collection.insert_one(document)
                inserted_count += 1
            else:
                reason = "Duplicate news_url"
                skipped_records.append({'news_url': news_url, 'reason': reason})
                skipped_count += 1
        else:
            reason = "Missing news_url"
            skipped_records.append({'news_url': row.get('post_link', ''), 'reason': reason})

    
    skipped_path = None
    if skipped_records:
        skipped_df = pd.DataFrame(skipped_records)
        skipped_path = os.path.join(UPLOAD_FOLDER, 'skipped_records.xlsx')
        skipped_df.to_excel(skipped_path, index=False)
    summary = f"Total Inserted: {inserted_count}, Total Skipped: {skipped_count}"
    return summary, skipped_path