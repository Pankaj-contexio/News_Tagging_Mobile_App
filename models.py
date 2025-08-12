from pymongo import MongoClient
import boto3
import os
from dotenv import load_dotenv
load_dotenv()  # Loads variables from .env into environment
# Now you can access them
aws_key = os.getenv('AWS_ACCESS_KEY_ID')
aws_secret = os.getenv('AWS_SECRET_ACCESS_KEY')
MongoDB_URI = os.getenv('DATABASE_URL')
client = MongoClient(MongoDB_URI)
# db = client['database']
# news_collection = db['NEWS_MAIN']
# social_collection = db['SOCIAL_MAIN']
# users_collection = db['users']
# projects_collection = db['projects']
# article_requests_collection = db['article_requests']
# filters_collection = db['NewsfeedFilters']
# tags_collection = db['tags']
# Report_collection = db['ReportsData']
# analytics_collection = db['analytics_data']
# party_share_history = db['party_share_history']
# usage_collection = db['usage_metrics']
# foreignRelations = db['ForeignRelations']
db = client['News_Tagging']  # Replace with your database name
news_collection = db['NewsFeed']
filters_collection = db['filters']
social_collection = db['SocialFeed']
users_collection = db['users']
projects_collection = db['projects']
article_requests_collection = db['article_requests']
tags_collection = db['tags']
Report_collection = db['ReportsData']
analytics_collection = db['analytics_data']
party_share_history = db['party_share_history']
usage_collection = db['usage_metrics']
foreignRelations = db['ForeignRelations']

s3_client = boto3.client('s3',
                        aws_access_key_id=aws_key,
                        aws_secret_access_key=aws_secret,
                        region_name='ap-south-1')