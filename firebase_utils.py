import streamlit as st
import json
import re
import pandas as pd
import firebase_admin
from datetime import datetime
from firebase_admin import credentials, firestore, auth
import requests

@st.cache_resource
def get_firebase_app():
    """Initialize and return the Firebase app and Firestore client for Streamlit Cloud."""
    if 'firebase_initialized' not in st.session_state:
        try:
            # Use Streamlit secrets (no local file fallback for Cloud)
            if "firebase_config" not in st.secrets:
                st.error("Firebase config not found in Streamlit Secrets on Cloud.")
                st.session_state.firebase_initialized = False
                return None

            config = st.secrets["firebase_config"]
            # Ensure private_key is a string with proper newlines
            if isinstance(config.get("private_key"), str):
                config["private_key"] = config["private_key"].replace("\\n", "\n").replace("\n", "\n")
            else:
                st.error("Invalid 'private_key' type in Firebase config.")
                st.session_state.firebase_initialized = False
                return None

            # Validate required fields
            required_fields = [
                'type', 'project_id', 'private_key_id', 'private_key',
                'client_email', 'client_id', 'auth_uri', 'token_uri'
            ]
            missing_fields = [field for field in required_fields if field not in config]
            if missing_fields:
                st.error(f"Invalid Firebase config: Missing fields: {', '.join(missing_fields)}.")
                st.session_state.firebase_initialized = False
                return None

            if not config['private_key'].startswith('-----BEGIN PRIVATE KEY-----'):
                st.error("Invalid 'private_key' format in Firebase config.")
                st.session_state.firebase_initialized = False
                return None

            if not re.match(r'^[a-z0-9-]{6,30}$', config['project_id']):
                st.error(f"Invalid 'project_id' in Firebase config: {config['project_id']}.")
                st.session_state.firebase_initialized = False
                return None

            if not firebase_admin._apps:
                cred = credentials.Certificate(config)  # Use dict from secrets
                firebase_admin.initialize_app(cred)
                st.session_state.firebase_initialized = True
            else:
                st.session_state.firebase_initialized = True

            return firestore.client()
        except Exception as e:
            st.error(f"Firebase initialization error on Cloud: {str(e)}.")
            st.session_state.firebase_initialized = False
            return None
    return firestore.client() if st.session_state.firebase_initialized else None

db = get_firebase_app()

def initialize_firebase():
    """Compatibility function to initialize Firebase app."""
    return get_firebase_app()

def get_collection(collection_name):
    if not db:
        st.error("Firebase not initialized on Cloud.")
        return pd.DataFrame()  # Return empty DataFrame
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
        st.error(f"Error reading from {collection_name} on Cloud: {e}")
        return pd.DataFrame()

def add_document(collection_name, data):
    if not db:
        return False
    try:
        db.collection(collection_name).add(data)
        return True
    except Exception as e:
        st.error(f"Error adding to {collection_name} on Cloud: {e}")
        return False

def update_document(collection_name, doc_id, data):
    if not db:
        return False
    try:
        db.collection(collection_name).document(doc_id).update(data)
        return True
    except Exception as e:
        st.error(f"Error updating {collection_name}/{doc_id} on Cloud: {e}")
        return False

def delete_document(collection_name, doc_id):
    if not db:
        return False
    try:
        db.collection(collection_name).document(doc_id).delete()
        return True
    except Exception as e:
        st.error(f"Error deleting {collection_name}/{doc_id} on Cloud: {e}")
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
        st.error(f"Authentication error on Cloud: {str(e)}")
        return None

# Check connectivity and notify user
def is_online():
    try:
        requests.get("https://www.google.com", timeout=5)
        return True
    except:
        st.warning("Offline mode on Cloud: Data will sync when connected.")
        return False

is_online()  # Run on app load to display status
