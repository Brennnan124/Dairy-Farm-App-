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
        try:
            # Get the Firebase config from Streamlit secret
            firebase_config_str = os.getenv("FIREBASE_CONFIG")
            if not firebase_config_str:
                st.error("FIREBASE_CONFIG secret not found. Please set it in Streamlit Secrets.")
                st.session_state.firebase_initialized = False
                return None

            # Parse the JSON string into a dictionary
            config = json.loads(firebase_config_str)
            st.write("Parsed Firebase config:", config)  # Debug: Log the parsed config

            # Validate required fields
            required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email', 'client_id', 'auth_uri', 'token_uri']
            missing_fields = [field for field in required_fields if field not in config]
            if missing_fields:
                st.error(f"Invalid Firebase config: Missing fields: {', '.join(missing_fields)}.")
                st.session_state.firebase_initialized = False
                return None

            if not isinstance(config.get('private_key'), str) or not config['private_key'].startswith('-----BEGIN PRIVATE KEY-----'):
                st.error("Invalid 'private_key' in Firebase config.")
                st.session_state.firebase_initialized = False
                return None

            if not re.match(r'^[a-z0-9-]{6,30}$', config['project_id']):
                st.error(f"Invalid 'project_id' in Firebase config: {config['project_id']}.")
                st.session_state.firebase_initialized = False
                return None

            if not firebase_admin._apps:
                cred = credentials.Certificate(config)  # Use the parsed config dictionary
                firebase_admin.initialize_app(cred)
                st.write("Firebase app initialized successfully")  # Debug: Confirm initialization
                db = firestore.client()
                st.session_state.firebase_initialized = True
                return db
            st.session_state.firebase_initialized = True
            st.write("Reusing existing Firebase app")  # Debug: Reuse check
            return firestore.client()
        except json.JSONDecodeError:
            st.error("Firebase config is not a valid JSON string.")
            st.session_state.firebase_initialized = False
            return None
        except ValueError as e:
            st.error(f"Firebase initialization error: {str(e)}")
            st.session_state.firebase_initialized = False
            return None
        except Exception as e:
            st.error(f"Firebase initialization error: {str(e)}")
            st.session_state.firebase_initialized = False
            return None
    return firestore.client() if st.session_state.firebase_initialized else None

db = get_firebase_app()

def initialize_firebase():
    """Compatibility function to initialize Firebase app."""
    return get_firebase_app()

def get_collection(collection_name):
    if not db:
        st.error("Firestore client not initialized")
        return pd.DataFrame()  # Return empty DataFrame with error message
    try:
        st.write(f"Attempting to retrieve data from collection: {collection_name}")  # Debug: Log collection access
        docs = db.collection(collection_name).stream()
        data = []
        for doc in docs:
            doc_data = doc.to_dict()
            if doc_data:
                doc_data['id'] = doc.id
                data.append(doc_data)
        df = pd.DataFrame(data)
        st.write(f"Retrieved data from {collection_name}: {df}")  # Debug: Log retrieved data
        return df
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
        st.error(f"Authentication error: {str(e)}")
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
