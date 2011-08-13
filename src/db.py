# -*- coding: utf-8 -*-
from google.appengine.ext import db
#from google.appengine.ext import blobstore

class UserPrefs(db.Model):
    api_key = db.StringProperty()
    account = db.StringProperty()
    google_account = db.UserProperty()
    created_at = db.DateTimeProperty(auto_now_add=True)
    updated_at = db.DateTimeProperty(auto_now_add=True)
    
class MarkerIcon(db.Model):
    user_prefs = db.ReferenceProperty(UserPrefs)
    name = db.StringProperty()
    icon = db.BlobProperty()
    visible = db.BooleanProperty()
    created_at = db.DateTimeProperty(auto_now_add=True)
    
class UserMaps(db.Model):
    user_prefs = db.ReferenceProperty(UserPrefs)
    map_id = db.StringProperty()
    map_title = db.StringProperty()
    home_geo = db.GeoPtProperty()
    created_at = db.DateTimeProperty(auto_now_add=True)
    
class UserActivity(db.Model):
    user_prefs = db.ReferenceProperty(UserPrefs)
    user_maps = db.ReferenceProperty(UserMaps)
    name = db.StringProperty()
    geo = db.GeoPtProperty()
    tags = db.TextProperty()
    photo = db.BlobProperty()
    icon = db.ReferenceProperty(MarkerIcon)
    created_at = db.DateTimeProperty(auto_now_add=True)
    
    