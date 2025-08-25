# dairy_farm_app/firebase_utils.py
import streamlit as st
import os
import json
import re
import pandas as pd
import firebase_admin
from datetime import datetime
from firebase_admin import credentials, firestore, auth
import requests

@st.cache_resource
def get_firebase_app():
    """Initialize and return the Firebase app and Firestore client."""
    if 'firebase_initialized' not in st.session_state:
        st.write("Attempting to initialize Firebase app...")  # Debug: Start of initialization
        try:
            # Get the Firebase config from Streamlit secret
            firebase_config_str = os.getenv("FIREBASE_CONFIG")
            if not firebase_config_str:
                st.write("FIREBASE_CONFIG secret not found in environment.")  # Debug: Missing secret
                st.session_state.firebase_initialized = False
                return None

            # Parse the JSON string into a dictionary
            config = json.loads(firebase_config_str)
            st.write("Parsed Firebase config successfully:", {k: v[:10] + "..." if isinstance(v, str) and len(v) > 10 else v for k, v in config.items()})  # Debug: Partial config

            # Validate required fields
            required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email', 'client_id', 'auth_uri', 'token_uri']
            missing_fields = [field for field in required_fields if field not in config]
            if missing_fields:
                st.write(f"Missing required fields in config: {missing_fields}")  # Debug: Missing fields
                st.session_state.firebase_initialized = False
                return None

            if not isinstance(config.get('private_key'), str) or not config['private_key'].startswith('-----BEGIN PRIVATE KEY-----'):
                st.write("Invalid 'private_key' format in config.")  # Debug: Invalid private key
                st.session_state.firebase_initialized = False
                return None

            if not re.match(r'^[a-z0-9-]{6,30}$', config['project_id']):
                st.write(f"Invalid 'project_id' format: {config['project_id']}")  # Debug: Invalid project ID
                st.session_state.firebase_initialized = False
                return None

            if not firebase_admin._apps:
                cred = credentials.Certificate(config)
                firebase_admin.initialize_app(cred)
                st.write("Firebase app initialized successfully.")  # Debug: Success
            else:
                st.write("Reusing existing Firebase app.")  # Debug: Reuse
            db = firestore.client()
            st.session_state.firebase_initialized = True
            return db
        except json.JSONDecodeError as e:
            st.write(f"JSON Decode Error: {str(e)} - Firebase config is not a valid JSON string.")  # Debug: JSON error
            st.session_state.firebase_initialized = False
            return None
        except Exception as e:
            st.write(f"Initialization failed with error: {str(e)}")  # Debug: General error
            st.session_state.firebase_initialized = False
            return None
    st.write("Returning cached Firestore client.")  # Debug: Cached client
    return firestore.client() if st.session_state.get('firebase_initialized', False) else None

db = get_firebase_app()

def initialize_firebase():
    """Compatibility function to initialize Firebase app."""
    return get_firebase_app()

def get_collection(collection_name):
    if not db:
        return pd.DataFrame()  # Return empty DataFrame silently (will remove error message later)
    try:
        st.write(f"Attempting to retrieve data from collection: {collection_name}")  # Debug: Collection access
        docs = db.collection(collection_name).stream()
        data = []
        for doc in docs:
            doc_data = doc.to_dict()
            if doc_data:
                doc_data['id'] = doc.id
                data.append(doc_data)
        df = pd.DataFrame(data)
        st.write(f"Retrieved data from {collection_name}: {df}")  # Debug: Retrieved data
        return df
    except Exception as e:
        st.write(f"Error reading from {collection_name}: {e}")  # Debug: Error details
        return pd.DataFrame()

def add_document(collection_name, data):
    if not db:
        return False
    try:
        db.collection(collection_name).add(data)
        return True
    except Exception as e:
        st.write(f"Error adding to {collection_name}: {e}")
        return False

def update_document(collection_name, doc_id, data):
    if not db:
        return False
    try:
        db.collection(collection_name).document(doc_id).update(data)
        return True
    except Exception as e:
        st.write(f"Error updating {collection_name}/{doc_id}: {e}")
        return False

def delete_document(collection_name, doc_id):
    if not db:
        return False
    try:
        db.collection(collection_name).document(doc_id).delete()
        return True
    except Exception as e:
        st.write(f"Error deleting {collection_name}/{doc_id}: {e}")
        return False

def log_audit_event(user, action, details=""):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    add_document("audit_log", {
        "timestamp": timestamp,
        "user": user,
        "action": action,
        "details": details
    })

def verify_id_token(id_token):
    """Verify a Firebase ID token and return user info."""
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except auth.AuthError as e:
        st.write(f"Authentication error: {str(e)}")
        return None

# Check connectivity and notify user
def is_online():
    try:
        requests.get("https://www.google.com", timeout=5)
        return True
    except:
        st.warning("Offline mode: Data will sync when connected.")
        return False

is_online()  # Run on app load to display status
