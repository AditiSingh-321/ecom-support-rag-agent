import os
import streamlit as st
import requests
from datetime import datetime

# API Configuration from environment
FLASK_API_BASE_URL = os.getenv("FLASK_API_BASE_URL", "http://localhost:5000/api").rstrip("/")
RASA_ENDPOINT = os.getenv("RASA_ENDPOINT", "http://localhost:5005/webhooks/rest/webhook")

# UI Configuration
st.set_page_config(
    page_title="E-Commerce AI Support",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stTextInput>div>div>input {
        border-radius: 20px;
        padding: 12px;
    }
    .stButton>button {
        border-radius: 20px;
        padding: 8px 20px;
        background: #2563eb;
        color: white;
    }
    .chat-message {
        padding: 14px 18px;
        border-radius: 12px;
        margin: 12px 0;
        font-size: 15px;
        line-height: 1.5;
        box-shadow: 0 2px 5px rgba(0,0,0,0.25);
    }
    .user-message {
        background: #1e293b;
        color: #f8fafc !important;
        border-left: 4px solid #3b82f6;
    }
    .user-message strong {
        color: #60a5fa !important;
    }
    .bot-message {
        background: #0f172a;
        color: #f1f5f9 !important;
        border-left: 4px solid #10b981;
    }
    .bot-message strong {
        color: #34d399 !important;
    }
    .meta-tag {
        font-size: 0.82em;
        color: #94a3b8 !important;
        margin-top: 8px;
        padding-top: 6px;
        border-top: 1px solid rgba(255, 255, 255, 0.1);
    }
    .msg-timestamp {
        font-size: 0.75em;
        color: #64748b !important;
        display: block;
        margin-top: 4px;
    }
</style>
""", unsafe_allow_html=True)

# Session State Initialization
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# Header Section
st.title("🛒 Smart E-Commerce Support Agent")
st.markdown("---")

# Sidebar Configuration
with st.sidebar:
    st.header("Navigation")
    action = st.radio(
        "Select Service:",
        ["AI Assistant Chat", "Order Tracking", "Product Availability"],
        index=0
    )
    
    st.markdown("---")
    st.subheader("Chat Backend Mode")
    chat_mode = st.radio(
        "Routing Engine:",
        ["Agentic RAG (Flask Backend)", "Rasa Dialogue Manager"],
        index=0
    )

    st.markdown("---")
    st.markdown("**Sample Order IDs:**")
    st.code("ORD-1001\nORD-1002\nORD-1003\n#123")
    st.markdown("**Sample Products:**")
    st.code("Laptop Pro\nGalaxy S21\nNoise-Cancelling Headphones")
    
    st.markdown("---")
    st.markdown("**Need Help?**")
    st.markdown("📞 Contact Support: support@ecom.ai")
    st.markdown("📧 Email: contact@ecom.ai")

# API Helper Functions
def handle_api_call(endpoint, method='GET', params=None):
    try:
        with st.spinner("Processing..."):
            if method == 'GET':
                response = requests.get(endpoint, timeout=10)
            elif method == 'POST':
                response = requests.post(endpoint, json=params, timeout=25)
            
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {str(e)}")
        return None

# Chat Interface
if action == "AI Assistant Chat":
    st.subheader("💬 AI Support Assistant")
    
    # Chat Container
    chat_container = st.container()
    
    # Display Chat History
    with chat_container:
        for msg in st.session_state.chat_history:
            css_class = "user-message" if msg['sender'] == 'user' else "bot-message"
            meta_html = ""
            if msg.get("meta"):
                meta_html = f"<div class='meta-tag'>{msg['meta']}</div>"
            st.markdown(
                f"<div class='chat-message {css_class}'>"
                f"<strong>{msg['sender'].title()}:</strong> {msg['content']}<br>"
                f"{meta_html}"
                f"<span class='msg-timestamp'>{msg['timestamp']}</span>"
                "</div>", 
                unsafe_allow_html=True
            )
    
    # Input Section
    user_input = st.text_input(
        "Type your message:", 
        placeholder="e.g. Where is my order ORD-1001? Or what is the return policy?",
        key="chat_input"
    )
    
    col1, col2 = st.columns([1, 0.1])
    with col1:
        if st.button("Send Message", key="send_button"):
            if user_input.strip():
                now_str = datetime.now().strftime("%H:%M:%S")
                # Add user message to history
                st.session_state.chat_history.append({
                    "sender": "user",
                    "content": user_input,
                    "timestamp": now_str
                })
                
                # Route based on selected mode
                if chat_mode == "Agentic RAG (Flask Backend)":
                    rag_response = handle_api_call(
                        f"{FLASK_API_BASE_URL}/rag/query",
                        method='POST',
                        params={"query": user_input}
                    )
                    if rag_response:
                        answer = rag_response.get("answer", "No answer received.")
                        sources = [s.get("source", "") for s in rag_response.get("sources", []) if s.get("source")]
                        tools = [t.get("tool", "") for t in rag_response.get("tool_calls", [])]
                        confidence = rag_response.get("confidence", 0.0)
                        
                        meta_parts = []
                        if confidence:
                            meta_parts.append(f"Confidence: {confidence:.2f}")
                        if tools:
                            meta_parts.append(f"Tools Used: {', '.join(tools)}")
                        if sources:
                            meta_parts.append(f"Sources: {', '.join(sources)}")
                        
                        meta_info = " | ".join(meta_parts)
                        st.session_state.chat_history.append({
                            "sender": "bot",
                            "content": answer,
                            "meta": meta_info,
                            "timestamp": datetime.now().strftime("%H:%M:%S")
                        })
                    else:
                        st.session_state.chat_history.append({
                            "sender": "bot",
                            "content": "Sorry, I am having trouble connecting to the Agentic RAG service.",
                            "timestamp": datetime.now().strftime("%H:%M:%S")
                        })
                else:
                    # Rasa endpoint
                    bot_response = handle_api_call(
                        RASA_ENDPOINT,
                        method='POST',
                        params={"sender": "user", "message": user_input}
                    )
                    
                    if bot_response:
                        for message in bot_response:
                            st.session_state.chat_history.append({
                                "sender": "bot",
                                "content": message.get("text", "I didn't understand that"),
                                "timestamp": datetime.now().strftime("%H:%M:%S")
                            })
                    else:
                        st.session_state.chat_history.append({
                            "sender": "bot",
                            "content": "Sorry, could not connect to Rasa server. Switch to 'Agentic RAG (Flask Backend)' in sidebar to test directly.",
                            "timestamp": datetime.now().strftime("%H:%M:%S")
                        })
                
                # Rerun to update display
                st.rerun()

# Order Tracking Section
elif action == "Order Tracking":
    st.subheader("📦 Real-Time Order Tracking")
    
    with st.form("order_tracking_form"):
        order_id = st.text_input(
            "Order ID:",
            placeholder="e.g. ORD-1001, ORD-1002, ORD-1003, #123",
            max_chars=30
        )
        
        if st.form_submit_button("Track Order", use_container_width=True):
            if not order_id.strip():
                st.error("Please enter a valid order ID")
            else:
                result = handle_api_call(f"{FLASK_API_BASE_URL}/orders/{order_id.strip()}")
                if result:
                    if result.get("status") == "Not found":
                        st.warning(f"Order '{order_id}' was not found in the records.")
                    else:
                        with st.expander("Order Details", expanded=True):
                            cols = st.columns(3)
                            cols[0].metric("Order ID", result.get('order_id', order_id))
                            cols[1].metric("Order Status", result.get('status', 'Unknown'))
                            cols[2].metric("Estimated Delivery", result.get('delivery_date') or result.get('eta', 'N/A'))
                            
                            loc = result.get('location')
                            if loc and isinstance(loc, dict) and 'lat' in loc and 'lng' in loc:
                                st.map({
                                    'latitude': [loc.get('lat', 0)],
                                    'longitude': [loc.get('lng', 0)]
                                })

# Product Availability Section
elif action == "Product Availability":
    st.subheader("📊 Product Stock Checker")
    
    with st.form("stock_check_form"):
        product_name = st.text_input(
            "Product Name:",
            placeholder="e.g. Laptop Pro, Galaxy S21, Noise-Cancelling Headphones",
            key="product_input"
        )
        
        if st.form_submit_button("Check Availability", use_container_width=True):
            if not product_name.strip():
                st.error("Please enter a product name")
            else:
                result = handle_api_call(f"{FLASK_API_BASE_URL}/products/{product_name.strip()}/stock")
                if result:
                    stock_val = result.get('stock')
                    if stock_val == "Not found":
                        st.warning(f"Product '{product_name}' was not found in our catalog.")
                    else:
                        cols = st.columns(3)
                        cols[0].metric("Product Name", result.get('product_name', product_name))
                        cols[1].metric("Available Stock", stock_val)
                        cols[2].metric("Restock ETA", result.get('restock_date', 'N/A'))
                        
                        try:
                            numeric_stock = int(stock_val)
                            st.progress(min(numeric_stock / 50.0, 1.0))
                        except (ValueError, TypeError):
                            pass
