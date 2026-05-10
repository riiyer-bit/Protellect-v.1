import streamlit as st, hashlib
from datetime import datetime

def _hash(pw): return hashlib.sha256(pw.encode()).hexdigest()

_DEFAULTS = {
    "demo@protellect.com":{"password":_hash("protellect2024"),"name":"Demo User","plan":"free","searches_used":0,"max_searches":10,"lab_profile":None,"onboarded":False},
    "pro@protellect.com":{"password":_hash("pro2024"),"name":"Dr. Researcher","plan":"pro","searches_used":0,"max_searches":500,"lab_profile":None,"onboarded":False},
}

def _db():
    if "users_db" not in st.session_state: st.session_state.users_db=_DEFAULTS.copy()
    return st.session_state.users_db

def current_user(): return st.session_state.get("current_user")
def is_logged_in(): return current_user() is not None

def login(email,password):
    db=_db()
    if email not in db: return False,"No account found."
    if db[email]["password"]!=_hash(password): return False,"Incorrect password."
    st.session_state.current_user={**db[email],"email":email}; return True,"ok"

def register(email,password,name):
    db=_db()
    if email in db: return False,"Email already registered."
    if len(password)<8: return False,"Password must be 8+ characters."
    db[email]={"password":_hash(password),"name":name,"plan":"free","searches_used":0,"max_searches":10,"lab_profile":None,"onboarded":False}
    st.session_state.current_user={**db[email],"email":email}; return True,"ok"

def logout():
    for k in ["current_user","domain","subdomain","lab_profile","onboarding_done","analysis_cache"]: st.session_state.pop(k,None)

def save_lab_profile(profile):
    u=current_user()
    if not u: return
    db=_db(); e=u["email"]; db[e]["lab_profile"]=profile; db[e]["onboarded"]=True
    st.session_state.current_user["lab_profile"]=profile; st.session_state.current_user["onboarded"]=True
    st.session_state.lab_profile=profile; st.session_state.onboarding_done=True

def can_search():
    u=current_user()
    if not u: return False
    if u.get("plan")=="pro": return True
    return u.get("searches_used",0)<u.get("max_searches",10)

def decrement_search():
    u=current_user()
    if not u or u.get("plan")=="pro": return
    db=_db(); e=u["email"]; db[e]["searches_used"]=db[e].get("searches_used",0)+1
    st.session_state.current_user["searches_used"]=db[e]["searches_used"]
