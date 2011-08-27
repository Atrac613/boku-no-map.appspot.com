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
from google.appengine.api import taskqueue

from db import UserPrefs
from db import UserMaps
from db import UserActivity
from db import MarkerIcon

class MapViewPage(webapp.RequestHandler):
    def get(self, map_id):
        
        user_maps = UserMaps.all().filter('map_id =', map_id).filter('visible =', True).get()
        if user_maps is None:
            return self.error(404)
        
        map_title = user_maps.map_title
        
        lat = ''
        lng = ''
        if user_maps.home_geo is not None:
            lat = user_maps.home_geo.lat
            lng = user_maps.home_geo.lon
        
        user_activity_list = UserActivity.all().filter('user_maps =', user_maps.key()).order('-created_at').fetch(200)
        activity_list = []
        activity_id_list = []
        available_icon_list = []
        for user_activity in user_activity_list:
            
            icon_id = ''
            if user_activity.icon is not None:
                icon_id = user_activity.icon.key().id()
                available_icon_list.append({'id': icon_id, 'name': user_activity.icon.name})
            
            created_at = user_activity.created_at + datetime.timedelta(hours=9)
                
            activity_list.append({'id': user_activity.key().id(), 'name': user_activity.name, 'tags': user_activity.tags, 'icon': icon_id, 'lat': user_activity.geo.lat, 'lng': user_activity.geo.lon, 'created_at': created_at.strftime('%Y-%m-%d %H:%M:%S (JST)')})
            
            activity_id_list.append(str(user_activity.key().id()))
        
        user = users.get_current_user()
        if user:
            url = users.create_logout_url('/map/%s' % map_id)
        else:
            url = users.create_login_url('/map/%s' % map_id)
        
        icon_list = None
        map_owner = False
        if user is not None:
            user_prefs = UserPrefs.all().filter('google_account =', user).get()
            if user_prefs is not None:
                user_maps = UserMaps.all().filter('map_id =', map_id).filter('user_prefs =', user_prefs.key()).get()
                if user_maps is not None:
                    map_owner = True
                    marker_icon_list = MarkerIcon.all().filter('user_prefs =', user_prefs.key()).filter('visible =', True).fetch(100)
                    icon_list = []
                    for marker_icon in marker_icon_list:
                        icon_list.append({'id': marker_icon.key().id(), 'name': marker_icon.name})
        
        mode = self.request.get('mode')
        
        template_values = {
            'map_title': map_title,
            'map_id': map_id,
            'lat': lat,
            'lng': lng,
            'activity_list': activity_list,
            'activity_id_list': ','.join(activity_id_list),
            'icon_list': icon_list,
            'available_icon_list': available_icon_list,
            'map_owner': map_owner,
            'login': user and True or False,
            'url': url,
            'mode': mode
        }
        
        path = os.path.join(os.path.dirname(__file__), 'templates/map/map.html')
        self.response.out.write(template.render(path, template_values))
        
    def post(self, map_id):
        
        user = users.get_current_user()
        if user is None:
            return self.redirect(users.create_login_url(self.request.uri))
        
        user_prefs = UserPrefs.all().filter('google_account =', user).get()
        if user_prefs is None:
            return self.redirect('/map/%s' % map_id)
        
        user_maps = UserMaps.all().filter('map_id =', map_id).filter('visible =', True).filter('user_prefs =', user_prefs.key()).get()
        if user_maps is None:
            return self.redirect('/map/%s' % map_id)
        
        mode = self.request.get('mode')
        
        if mode == 'set_home':
            lat = self.request.get('lat')
            lng = self.request.get('lng')
            
            user_maps.home_geo = db.GeoPt(lat, lon=lng)
            user_maps.put()
        elif mode == 'set_marker':
            name = self.request.get('name')
            tags = self.request.get('tags')
            icon = self.request.get('icon')
            
            marker_icon = None
            if icon != '':
                marker_icon = MarkerIcon.get_by_id(int(icon))
            
            tags = tags.replace(u'、', ',').replace(' ', ',').replace(u'　', ',')
            
            lat = self.request.get('lat')
            lng = self.request.get('lng')
            
            user_activity = UserActivity()
            user_activity.name = name
            user_activity.tags = tags
            user_activity.geo = db.GeoPt(lat, lon=lng)
            user_activity.user_prefs = user_prefs.key()
            user_activity.user_maps = user_maps.key()
            
            if marker_icon is not None:
                user_activity.icon = marker_icon.key()
            
            user_activity.put()
            
            try:
                taskqueue.add(url='/task/build_tag_index', params={'map_id': map_id})
            except:
                logging.error('Taskqueue add failed.')
                
        elif mode == 'delete':
            user_maps.visible = False
            user_maps.put()
            return self.redirect('/user/home')
            
        return self.redirect('/map/%s' % map_id)
        
class MapEditPage(webapp.RequestHandler):
    def get(self, map_id):
        
        user_maps = UserMaps.all().filter('visible =', True).filter('map_id =', map_id).get()
        if user_maps is None:
            return self.error(404)
        
        lat = ''
        lng = ''
        if user_maps.home_geo is not None:
            lat = user_maps.home_geo.lat
            lng = user_maps.home_geo.lon
        
        marker_id = self.request.get('marker_id')
        user = users.get_current_user()
        
        user_activity = UserActivity.get_by_id(int(marker_id))
        if user_activity is None:
            return self.error(404)
        
        if user_activity.user_prefs.google_account != user:
            return self.redirect('/map/%s' % map_id)
        
        icon_id = ''
        if user_activity.icon is not None:
            icon_id = user_activity.icon.key().id()
        
        activity_list = []
        activity_list.append({'id': user_activity.key().id(), 'name': user_activity.name, 'tags': user_activity.tags, 'icon': icon_id, 'lat': user_activity.geo.lat, 'lng': user_activity.geo.lon})
        
        if user:
            url = users.create_logout_url('/map/%s' % map_id)
        else:
            url = users.create_login_url('/map/%s' % map_id)
        
        icon_list = None
        map_owner = False
        if user is not None:
            user_prefs = UserPrefs.all().filter('google_account =', user).get()
            if user_prefs is not None:
                user_maps = UserMaps.all().filter('map_id =', map_id).filter('user_prefs =', user_prefs.key()).get()
                if user_maps is not None:
                    map_owner = True
                    marker_icon_list = MarkerIcon.all().filter('user_prefs =', user_prefs.key()).filter('visible =', True).fetch(100)
                    icon_list = []
                    for marker_icon in marker_icon_list:
                        icon_list.append({'id': marker_icon.key().id(), 'name': marker_icon.name})
        
        template_values = {
            'map_title': user_maps.map_title,
            'map_id': map_id,
            'lat': lat,
            'lng': lng,
            'activity_list': activity_list,
            'icon_list': icon_list,
            'map_owner': map_owner,
            'login': user and True or False,
            'url': url
        }
        
        path = os.path.join(os.path.dirname(__file__), 'templates/map/map_edit.html')
        self.response.out.write(template.render(path, template_values))
        
    def post(self, map_id):
        user_maps = UserMaps.all().filter('visible =', True).filter('map_id =', map_id).get()
        if user_maps is None:
            return self.error(404)
        
        marker_id = self.request.get('marker_id')
        user = users.get_current_user()
        
        user_activity = UserActivity.get_by_id(int(marker_id))
        if user_activity is None:
            return self.error(404)
        
        if user_activity.user_prefs.google_account != user:
            return self.redirect('/map/%s' % map_id)
        
        name = self.request.get('name')
        tags = self.request.get('tags')
        icon = self.request.get('icon')
        
        marker_icon = None
        if icon != '':
            marker_icon = MarkerIcon.get_by_id(int(icon))
        
        tags = tags.replace(u'、', ',').replace(' ', ',').replace(u'　', ',')
        
        lat = self.request.get('lat')
        lng = self.request.get('lng')
        
        user_activity.name = name
        user_activity.tags = tags
        user_activity.geo = db.GeoPt(lat, lon=lng)
        
        if marker_icon is not None:
            user_activity.icon = marker_icon.key()
        
        user_activity.put()
        
        memcache.delete('marker_data_%s' % marker_id)
        
        self.redirect('/map/%s' % map_id)
        
class MapEditTitlePage(webapp.RequestHandler):
    def get(self, map_id):
        user_maps = UserMaps.all().filter('visible =', True).filter('map_id =', map_id).get()
        if user_maps is None:
            return self.error(404)
        
        user = users.get_current_user()
        
        if user_maps.user_prefs.google_account != user:
            return self.redirect('/map/%s' % map_id)
        
        template_values = {
            'map_title': user_maps.map_title,
            'map_id': map_id
        }
        
        path = os.path.join(os.path.dirname(__file__), 'templates/map/map_edit_title.html')
        self.response.out.write(template.render(path, template_values))
        
    def post(self, map_id):
        mode = self.request.get('mode')
        
        user_maps = UserMaps.all().filter('visible =', True).filter('map_id =', map_id).get()
        if user_maps is None:
            return self.error(404)
        
        user = users.get_current_user()
        
        if user_maps.user_prefs.google_account != user:
            return self.redirect('/map/%s' % map_id)
        
        if mode == 'modify':
            map_title = self.request.get('map_title')
            user_maps.map_title = map_title
            user_maps.put()
            
        self.redirect('/map/%s' % map_id)
        
application = webapp.WSGIApplication(
                                     [('/map/([^/]+)?', MapViewPage),
                                      ('/map/edit/([^/]+)?', MapEditPage),
                                      ('/map/edit_title/([^/]+)?', MapEditTitlePage)],
                                     debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
    