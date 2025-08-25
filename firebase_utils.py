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
        st.write("Attempting to initialize Firebase with secrets...")
        try:
            if "firebase_config" not in st.secrets:
                st.error("Firebase config not found in Streamlit Secrets on Cloud.")
                st.session_state.firebase_initialized = False
                return None

            config = st.secrets["firebase_config"]
            st.write("Loaded config:", {k: v[:10] + "..." if k == "private_key" else v for k, v in config.items()})  # Debug partial config

            # Ensure private_key is a string with proper newlines
            if isinstance(config.get("private_key"), str):
                private_key = config["private_key"].replace("\\n", "\n").replace("\n", "\n")
                if not private_key.startswith("-----BEGIN PRIVATE KEY-----"):
                    st.error("Invalid 'private_key' format after processing.")
                    st.session_state.firebase_initialized = False
                    return None
                config["private_key"] = private_key
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

            if not re.match(r'^[a-z0-9-]{6,30}$', config['project_id']):
                st.error(f"Invalid 'project_id' in Firebase config: {config['project_id']}.")
                st.session_state.firebase_initialized = False
                return None

            if not firebase_admin._apps:
                st.write("Initializing Firebase app...")
                cred = credentials.Certificate(config)
                firebase_admin.initialize_app(cred)
                st.write("Firebase app initialized successfully.")
                st.session_state.firebase_initialized = True
            else:
                st.write("Firebase app already initialized, reusing.")
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
        st.write(f"Attempting to fetch data from collection: {collection_name}")
        docs = db.collection(collection_name).stream()
        data = []
        for doc in docs:
            doc_data = doc.to_dict()
            if doc_data:
                doc_data['id'] = doc.id
                data.append(doc_data)
        df = pd.DataFrame(data)
        st.write(f"Successfully loaded {len(df)} rows from {collection_name}")
        return df
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
