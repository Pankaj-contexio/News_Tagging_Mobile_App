from pymongo import MongoClient
from urllib.parse import urlparse
import pandas as pd
from pymongo import MongoClient
import re

# # Connect to the MongoDB client into Main database
# client = MongoClient('mongodb+srv://user1:123pass@cluster0.7jwr3.mongodb.net/')  # Replace with your MongoDB URI
# db = client['database']  # Replace with your database name
# collection = db['NEWS_MAIN']  # Replace with your collection name

#####local database upload for test #####
# Connect to the MongoDB client
client = MongoClient('mongodb://localhost:27017/')  # Replace with your MongoDB URI
db = client['News_Tagging']  # Replace with your database name
collection = db['NewsFeed']  # Replace with your collection name


##########################################

########################################################################
# Step 2: Read Excel data
data = pd.read_excel(r"D:\IT\Workspace\SpringBoot_Deployment_War\1. Active Wars\News_Tagging\DataUploading\Bangla_china_news_07_07_2025.xlsx")

# Print columns to verify the correct names
print("Columns in DataFrame:", data.columns)

# Normalize column names
data.columns = data.columns.str.strip().str.lower()  # convert to lower case and strip spaces


# Replace blank-like values with 'Not Available'
data = data.fillna('Not Available')  # First replace NaN
data = data.replace(['', 'N/A', 'n/a', None], 'Not Available') #'na' 'NA' regex=True


# Print columns to verify
print("Columns in DataFrame after cleaning:", data.columns)

# Helper function to validate published_date
def is_valid_published_date(value):
    if value == 'Not Available':
        return False
    try:
        date = pd.to_datetime(value, errors='raise')

        # Now check if original value looks like ONLY date
        value_str = str(value)

        # Allow formats like "2025-04-11" or "2025-04-11T00:00:00.000+00:00"
        pattern = r"^\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:\d{2}|Z)?)?$"

        if re.match(pattern, value_str):
            return True
        else:
            return False
    except Exception:
        return False

# Helper function to validate country
allowed_countries = {'country_1', 'country_2', 'country_3', 'country_4', 'country_5', 'country_101', 'country_150', 'country_45'}
def is_valid_country(value):
    if value == 'Not Available':
        return False
    value = str(value).strip()  # Remove extra spaces
    return value in allowed_countries


# Helper function to validate sector
allowed_sectors = {'sector_1', 'sector_2', 'sector_3', 'sector_4', 'sector_5'}
def is_valid_sector(value):
    if value == 'Not Available':
        return False
    value = str(value).strip()
    return value in allowed_sectors

# Helper function to validate sector
allowed_publisian = {'publisian_1', 'publisian_2', 'publisian_3', 'publisian_4','publisian_5','publisian_6','publisian_7','publisian_8',
                    'publisian_9', 'publisian_10', 'publisian_11', 'publisian_12', 'publisian_13', 'publisian_14','publisian_15','publisian_16',
                    'publisian_17', 'publisian_18', 'publisian_19', 'publisian_20', 'publisian_21', 'publisian_22','publisian_23','publisian_24',
                     'publisian_25','publisian_26', 'publisian_27', 'publisian_28', 'publisian_29','publisian_30','publisian_31','publisian_32',
                     'publisian_33','publisian_34', 'publisian_39', 'publisian_41', 'publisian_42', 'publisian_43', 'publisian_44', 'publisian_45', 'publisian_46', 'publisian_47', 'publisian_48',
                     'publisian_49', 'publisian_50', 'publisian_51'
                     , 'publisian_52', 'publisian_53', 'publisian_54', 'publisian_55', 'publisian_56', 'publisian_57', 'publisian_58', 'publisian_59',
                     'publisian_60', 'publisian_61', 'publisian_62', 'publisian_63', 'publisian_64', 'publisian_65', 'publisian_66',
                     'publisian_67', 'publisian_68', 'publisian_69', 'publisian_70', 'publisian_71', 'publisian_72', 'publisian_73', 'publisian_74'
                     , 'publisian_75', 'publisian_76', 'publisian_77', 'publisian_78', 'publisian_79', 'publisian_80', 'publisian_81'
                     , 'publisian_82', 'publisian_83', 'publisian_84', 'publisian_85', 'publisian_86', 'publisian_87', 'publisian_88',
                     'publisian_89', 'publisian_90', 'publisian_91', 'publisian_92'
                     , 'publisian_', 'publisian_', 'publisian_', 'publisian_', 'publisian_', 'publisian_', 'publisian_', 'publisian_', 'publisian_', 'publisian_', 'publisian_'}

def is_valid_publisian(value):
    if value == 'Not Available':
        return False
    value = str(value).strip()
    return value in allowed_publisian


skipped_records = []

# Counters
inserted_count = 0
skipped_count = 0

# Check for existing URLs and upload new records
for index, row in data.iterrows():
    if 'news_url' in row and row['news_url'] != 'Not Available':  # Check if the column exists
        news_url = row['news_url']

        # Validate published_date
        if 'published_date' in row and not is_valid_published_date(row['published_date']):
            reason = f"Invalid published_date: {row['published_date']}"
            skipped_records.append({'news_url': news_url, 'reason': reason})
            print(f"Skipped (Invalid published_date) at row {index}: {news_url}")
            skipped_count += 1
            continue  # Skip this record

        # Validate country
        if 'country' in row:
            # Clean spaces before checking
            country_cleaned = str(row['country']).strip()
            if not is_valid_country(country_cleaned):
                reason = f"Invalid country: {row['country']}"
                skipped_records.append({'news_url': news_url, 'reason': reason})
                print(f"Skipped (Invalid country) at row {index}: {news_url} - Country: {row['country']}")
                skipped_count += 1
                continue
            else:
                row['country'] = country_cleaned  # update row with cleaned value
        else:
            reason = "Missing country field"
            skipped_records.append({'news_url': news_url, 'reason': reason})
            print(f"Skipped (Missing country field) at row {index}: {news_url}")
            skipped_count += 1
            continue

        # Validate sector
        if 'sector' in row:
            sector_cleaned = str(row['sector']).strip()
            if not is_valid_sector(sector_cleaned):
                reason = f"Invalid sector: {row['sector']}"
                skipped_records.append({'news_url': news_url, 'reason': reason})
                print(f"Skipped (Invalid sector) at row {index}: {news_url} - Sector: {row['sector']}")
                skipped_count += 1
                continue
            else:
                row['sector'] = sector_cleaned
        else:
            reason = "Missing sector field"
            skipped_records.append({'news_url': news_url, 'reason': reason})
            print(f"Skipped (Missing sector field) at row {index}: {news_url}")
            skipped_count += 1
            continue

        # Validate sector
        if 'publisian' in row:
            publisian_cleaned = str(row['publisian']).strip()
            if not is_valid_publisian(publisian_cleaned):
                reason = f"Invalid publisian: {row['publisian']}"
                skipped_records.append({'news_url': news_url, 'reason': reason})
                print(f"Skipped (Invalid publisian) at row {index}: {news_url} - Publisian: {row['publisian']}")
                skipped_count += 1
                continue
            else:
                row['publisian'] = publisian_cleaned
        else:
            reason = "Missing publisian field"
            skipped_records.append({'news_url': news_url, 'reason': reason})
            print(f"Skipped (Missing sector field) at row {index}: {news_url}")
            skipped_count += 1
            continue

        # Check if news_url exists in the MongoDB collection
        if not collection.find_one({'news_url': news_url}):
            # Prepare the document to insert
            document = row.to_dict()
            
            ############################## upload video and image in array format #############
            if 'image' in row and pd.notna(row['image']):
                document['image'] = [img.strip() for img in str(row['image']).split(',')]
            else:
                document['image'] = []

            if 'video' in row and pd.notna(row['video']):
                document['video'] = [vid.strip() for vid in str(row['video']).split(',')]
            else:
                document['video'] = []

            
            #######################################################################################

            # Convert published_date to datetime object
            if 'published_date' in document and document['published_date'] != 'Not Available':
                document['published_date'] = pd.to_datetime(document['published_date'])
            
            
            collection.insert_one(document)
            print(f'Inserted: {news_url}')

        else:
            reason = "Duplicate news_url"
            skipped_records.append({'news_url': news_url, 'reason': reason})
            print(f"Skipped Already exists (Duplicate news_url) at row {index}: {news_url}")
            skipped_count += 1
            #print(f'Already exists: {news_url}')
        
    else:
        reason = "Missing news_url"
        skipped_records.append({'news_url': row['news_url'], 'reason': reason})
        print("Column 'news_url' not found in the current row.")

# Close the connection
client.close()

# Create log file with skipped records
skipped_df = pd.DataFrame(skipped_records)
skipped_df.to_excel(r'./skipped_records.xlsx', index=False)  # Save to Excel
# skipped_df.to_csv(r'./skipped_records.csv', index=False)  # Alternatively, save to CSV


# Summary
print("\nSummary:")
print(f"Total Inserted: {inserted_count}")
print(f"Total Skipped: {skipped_count}")
