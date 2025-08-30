# dairy_farm_app/firebase_utils.py
import streamlit as st
import os
import json
import re
import pandas as pd
import firebase_admin
from datetime import datetime
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
import pyrebase
import requests

load_dotenv()

firebase_config = {
    "apiKey": os.getenv("FIREBASE_API_KEY"),
    "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
    "projectId": os.getenv("FIREBASE_PROJECT_ID"),
    "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
    "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
    "appId": os.getenv("FIREBASE_APP_ID"),
    "databaseURL": ""
}

try:
    firebase = pyrebase.initialize_app(firebase_config)
    auth_client = firebase.auth()
except Exception as e:
    st.error(f"Failed to initialize Firebase client: {e}")
    auth_client = None

@st.cache_resource
def get_firebase_app():
    """Initialize and return the Firebase app and Firestore client."""
    if 'firebase_initialized' not in st.session_state:
        try:
            if not os.path.exists("firebase_config.json"):
                st.error("Firebase configuration file 'firebase_config.json' not found.")
                st.session_state.firebase_initialized = False
                return None
            
            if not os.access("firebase_config.json", os.R_OK):
                st.error("Cannot read 'firebase_config.json'. Check file permissions.")
                st.session_state.firebase_initialized = False
                return None

            with open("firebase_config.json", 'r') as f:
                config = json.load(f)
            
            required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email', 'client_id', 'auth_uri', 'token_uri']
            missing_fields = [field for field in required_fields if field not in config]
            if missing_fields:
                st.error(f"Invalid 'firebase_config.json': Missing fields: {', '.join(missing_fields)}.")
                st.session_state.firebase_initialized = False
                return None
            
            if not isinstance(config.get('private_key'), str) or not config['private_key'].startswith('-----BEGIN PRIVATE KEY-----'):
                st.error("Invalid 'private_key' in 'firebase_config.json'.")
                st.session_state.firebase_initialized = False
                return None
            
            if not re.match(r'^[a-z0-9-]{6,30}$', config['project_id']):
                st.error(f"Invalid 'project_id' in 'firebase_config.json': {config['project_id']}.")
                st.session_state.firebase_initialized = False
                return None

            if not firebase_admin._apps:
                cred = credentials.Certificate("firebase_config.json")
                firebase_admin.initialize_app(cred)
                db = firestore.client()
                st.session_state.firebase_initialized = True
                return db
            st.session_state.firebase_initialized = True
            return firestore.client()
        except json.JSONDecodeError:
            st.error("firebase_config.json is not a valid JSON file.")
            st.session_state.firebase_initialized = False
            return None
        except ValueError as e:
            st.error(f"Firebase initialization error: {str(e)}.")
            st.session_state.firebase_initialized = False
            return None
        except Exception as e:
            st.error(f"Firebase initialization error: {str(e)}.")
            st.session_state.firebase_initialized = False
            return None
    return firestore.client() if st.session_state.firebase_initialized else None

db = get_firebase_app()

def initialize_firebase():
    """Compatibility function to initialize Firebase app."""
    return get_firebase_app()

def get_collection(collection_name):
    if not db:
        return pd.DataFrame()  # Return empty DataFrame silently
    try:
        docs = db.collection(collection_name).stream()
        data = []
        for doc in docs:
            doc_data = doc.to_dict()
            if doc_data:
                doc_data['id'] = doc.id
                data.append(doc_data)
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error reading from {collection_name}: {e}")
        return pd.DataFrame()

def add_document(collection_name, data):
    if not db:
        return False
    try:
        db.collection(collection_name).add(data)
        return True
    except Exception as e:
        st.error(f"Error adding to {collection_name}: {e}")
        return False

def update_document(collection_name, doc_id, data):
    if not db:
        return False
    try:
        db.collection(collection_name).document(doc_id).update(data)
        return True
    except Exception as e:
        st.error(f"Error updating {collection_name}/{doc_id}: {e}")
        return False

def delete_document(collection_name, doc_id):
    if not db:
        return False
    try:
        db.collection(collection_name).document(doc_id).delete()
        return True
    except Exception as e:
        st.error(f"Error deleting {collection_name}/{doc_id}: {e}")
        return False

def get_document(collection_name, document_id):
    """Get a single document from Firestore"""
    if not db:
        return None
    try:
        doc_ref = db.collection(collection_name).document(document_id)
        doc = doc_ref.get()
        if doc.exists:
            return doc.to_dict()
        else:
            return None
    except Exception as e:
        st.error(f"Error getting document: {e}")
        return None

def set_document(collection_name, document_id, data):
    """Set a document in Firestore (creates or overwrites)"""
    if not db:
        return False
    try:
        doc_ref = db.collection(collection_name).document(document_id)
        doc_ref.set(data)
        return True
    except Exception as e:
        st.error(f"Error setting document: {e}")
        return False

def log_audit_event(user, action, details=""):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    add_document("audit_log", {
        "timestamp": timestamp,
        "user": user,
        "action": action,
        "details": details
    })

# Check connectivity and notify user
def is_online():
    try:
        requests.get("https://www.google.com", timeout=5)
        return True
    except:
        st.warning("Offline mode: Data will sync when connected.")
        return False

is_online()  # Run on app load to display status
