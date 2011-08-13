# -*- coding: utf-8 -*- 

import os
import logging
import datetime

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import template
from google.appengine.api import urlfetch
from google.appengine.api import users
from google.appengine.api import mail
from google.appengine.ext import db
from google.appengine.api import images
from google.appengine.api import memcache

from db import UserPrefs
from db import UserMaps
from db import UserActivity
from db import MarkerIcon

class HomePage(webapp.RequestHandler):
    def get(self):
        
        user = users.get_current_user()
        user_prefs = UserPrefs.all().filter('google_account =', user).get()
        if user_prefs is None:
            return self.error(404)
        
        user_maps = UserMaps.all().filter('user_prefs =', user_prefs.key()).fetch(100)

        template_values = {
            'map_list': user_maps
        }
        
        path = os.path.join(os.path.dirname(__file__), 'templates/user/home.html')
        self.response.out.write(template.render(path, template_values))

class IconPage(webapp.RequestHandler):
    def get(self):
        user = users.get_current_user()
        user_prefs = UserPrefs.all().filter('google_account =', user).get()
        if user_prefs is None:
            return self.error(404)
        
        marker_icon_list = MarkerIcon.all().filter('user_prefs =', user_prefs.key()).filter('visible =', True).fetch(100)
        
        icon_list = []
        #icon_list.append({'id':None, 'name':'Default'})
        for marker_icon in marker_icon_list:
            icon_list.append({'id':marker_icon.key().id(), 'name':marker_icon.name})

        template_values = {
            'icon_list': icon_list
        }
        
        path = os.path.join(os.path.dirname(__file__), 'templates/user/icon.html')
        self.response.out.write(template.render(path, template_values))
        
    def post(self):
        user = users.get_current_user()
        user_prefs = UserPrefs.all().filter('google_account =', user).get()
        if user_prefs is None:
            return self.error(404)
        
        mode = self.request.get('mode')
        
        if mode == 'add':
            name = self.request.get('name')
            icon = self.request.get('icon')
            
            marker_icon = MarkerIcon()
            marker_icon.name = name
            marker_icon.icon = db.Blob(icon)
            marker_icon.user_prefs = user_prefs.key()
            marker_icon.visible = True
            marker_icon.put()
            
        elif mode == 'delete':
            id = self.request.get('id')
            
            marker_icon = MarkerIcon.get_by_id(int(id))
            if marker_icon is not None:
                marker_icon.visible = False
                marker_icon.put()
        
        self.redirect('/icon')

class CreatePage(webapp.RequestHandler):
    def get(self):

        template_values = {
            'map_id': '',
            'map_title': '',
            'message': None
        }
        
        path = os.path.join(os.path.dirname(__file__), 'templates/user/create.html')
        self.response.out.write(template.render(path, template_values))
        
    def post(self):
        
        map_id = self.request.get('map_id')
        map_title = self.request.get('map_title')
        
        if map_title == '':
            map_title = map_id
        
        user = users.get_current_user()
        
        user_prefs = UserPrefs.all().filter('google_account =', user).get()
        if user_prefs is None:
            user_prefs = UserPrefs()
            user_prefs.google_account = user
            user_prefs.put()
        
        user_maps = UserMaps.all().filter('map_id =', map_id).get()
        if user_maps is None and map_id != '':
            user_maps = UserMaps()
            user_maps.map_id = map_id
            user_maps.map_title = map_title
            user_maps.user_prefs = user_prefs
            user_maps.put()
            
            self.redirect('/map/%s' % map_id)
            
        else:
            template_values = {
                'map_id': map_id,
                'map_title': map_title,
                'message': 'そのマップIDは使用できませんできした。'
            }
        
            path = os.path.join(os.path.dirname(__file__), 'templates/user/create.html')
            self.response.out.write(template.render(path, template_values))
            
application = webapp.WSGIApplication(
                                     [('/user/create', CreatePage),
                                      ('/user/home', HomePage),
                                      ('/user/icon', IconPage)],
                                     debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
    