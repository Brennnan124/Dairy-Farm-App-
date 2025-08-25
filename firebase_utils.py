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
            if "firebase_config" not in st.secrets:
                st.error("Firebase config not found in Streamlit Secrets on Cloud.")
                st.session_state.firebase_initialized = False
                return None

            config = st.secrets["firebase_config"]

            # Manually create a new config dict with modified private_key
            modified_config = {
                "type": config.get("type"),
                "project_id": config.get("project_id"),
                "private_key_id": config.get("private_key_id"),
                "private_key": config.get("private_key", "").replace("\\n", "\n") if isinstance(config.get("private_key"), str) else "",
                "client_email": config.get("client_email"),
                "client_id": config.get("client_id"),
                "auth_uri": config.get("auth_uri"),
                "token_uri": config.get("token_uri"),
                "auth_provider_x509_cert_url": config.get("auth_provider_x509_cert_url"),
                "client_x509_cert_url": config.get("client_x509_cert_url"),
                "universe_domain": config.get("universe_domain")
            }
            if not modified_config["private_key"].startswith("-----BEGIN PRIVATE KEY-----"):
                st.error("Invalid 'private_key' format after processing.")
                st.session_state.firebase_initialized = False
                return None

            # Validate required fields
            required_fields = [
                'type', 'project_id', 'private_key_id', 'private_key',
                'client_email', 'client_id', 'auth_uri', 'token_uri'
            ]
            missing_fields = [field for field in required_fields if not modified_config.get(field)]
            if missing_fields:
                st.error(f"Invalid Firebase config: Missing fields: {', '.join(missing_fields)}.")
                st.session_state.firebase_initialized = False
                return None

            if not re.match(r'^[a-z0-9-]{6,30}$', modified_config['project_id']):
                st.error(f"Invalid 'project_id' in Firebase config: {modified_config['project_id']}.")
                st.session_state.firebase_initialized = False
                return None

            if not firebase_admin._apps:
                cred = credentials.Certificate(modified_config)
                firebase_admin.initialize_app(cred)
                st.session_state.firebase_initialized = True
            else:
                st.session_state.firebase_initialized = True

            return firestore.client()
        except Exception as e:
            st.error(f"Firebase initialization error on Cloud: {str(e)}")
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
        return pd.DataFrame()
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

def is_online():
    try:
        requests.get("https://www.google.com", timeout=5)
        return True
    except:
        st.warning("Offline mode on Cloud: Data will sync when connected.")
        return False

is_online()  # Run on app load to display status
