# dairy_farm_app/pages/knowledge_base.py
import streamlit as st

knowledge_base = {
    "Milking Procedures": """
    ## Best Practices for Milking
    
    **1. Preparation:**
    - Clean udders with sanitizing solution
    - Wear gloves during milking
    - Ensure milking equipment is sterilized
    
    **2. Milking Process:**
    - Milk at consistent times (Morning, Lunch, Evening)
    - Handle teats gently
    - Check for mastitis signs before milking
    
    **3. Post-Milking:**
    - Apply teat dip
    - Record milk quantities immediately
    - Clean equipment after each session
    """,
    
    "Feed Management": """
    ## Feed Handling Guidelines
    
    **1. Storage:**
    - Keep feed in dry, rodent-proof containers
    - Use FIFO (First-In First-Out) system
    - Maintain temperature below 25°C
    
    **2. Distribution:**
    - Feed lactating cows 3 times daily
    - Provide 5-7kg of dairy meal per cow
    - Ensure constant access to clean water
    
    **3. Quality Control:**
    - Check for mold before feeding
    - Monitor feed consumption patterns
    - Adjust rations based on milk production
    """,
    
    "Health Monitoring": """
    ## Animal Health Protocols
    
    **Common Symptoms to Watch:**
    - Reduced milk production
    - Loss of appetite
    - Lameness or difficulty moving
    - Swollen udders
    
    **Preventive Measures:**
    - Vaccinate every 6 months
    - Regular deworming (every 3 months)
    - Hoof trimming quarterly
    
    **Emergency Procedures:**
    - Isolate sick animals immediately
    - Contact veterinarian if symptoms persist
    - Disinfect equipment after treatment
    """,
    
    "Artificial Insemination": """
    ## AI Best Practices
    
    **1. Heat Detection:**
    - Observe for mounting behavior
    - Check for clear mucus discharge
    - Monitor restlessness and reduced appetite
    
    **2. Timing:**
    - Inseminate 12 hours after first heat signs
    - Morning heat → evening AI
    - Evening heat → next morning AI
    
    **3. Procedure:**
    - Thaw semen properly (37°C for 45 seconds)
    - Use clean, sterile equipment
    - Record all details for tracking
    
    **4. Post-AI Care:**
    - Monitor for return to heat
    - Conduct pregnancy check at 45 days
    - Record calving dates for future reference
    """
}

def knowledge_base_page():
    st.title("📚 Knowledge Base")
    st.write("Best practices and guidelines for farm management")
    
    topic = st.selectbox("Select Topic", list(knowledge_base.keys()))
    
    if topic in knowledge_base:
        st.markdown(knowledge_base[topic])
    
    st.markdown("---")
    st.subheader("Quick Reference Guides")
    st.download_button("Download Milking Procedures", data=knowledge_base["Milking Procedures"], file_name="milking_guide.txt")
    st.download_button("Download Feed Management", data=knowledge_base["Feed Management"], file_name="feed_guide.txt")
    st.download_button("Download Health Protocols", data=knowledge_base["Health Monitoring"], file_name="health_guide.txt")
    st.download_button("Download AI Procedures", data=knowledge_base["Artificial Insemination"], file_name="ai_guide.txt")