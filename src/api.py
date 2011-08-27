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

from django.utils import simplejson 

from db import UserPrefs
from db import UserMaps
from db import UserActivity
from db import MarkerIcon
from db import UserActivityTagIndex

class GetIconAPI(webapp.RequestHandler):
    def get(self):
      
        image_key = self.request.get('id')
        logging.info('image_key: %s' % image_key)
        if image_key == '':
            return self.error(404)
        
        thumbnail = memcache.get('cached_icon_%s' % image_key)
        if thumbnail is None:
            marker_icon = MarkerIcon.get_by_id(int(image_key))
            
            if marker_icon is None:
                return self.error(404)
            
            thumbnail = marker_icon.icon
            memcache.add('cached_icon_%s' % image_key, thumbnail, 3600)
            
            logging.info('Image from DB. image_key: %s' % image_key)
        else:
            logging.info('Image from memcache. image_key: %s' % image_key)
        
        self.response.headers['Content-Type'] = 'image/png'
        self.response.out.write(thumbnail)
        
class GetMarkerDataAPI(webapp.RequestHandler):
    def get(self):
        
        marker_id = self.request.get('id')
        
        data = memcache.get('marker_data_%s' % marker_id)
        if data is None:
            user_activity = UserActivity.get_by_id(int(marker_id))
            if user_activity is None:
                return self.error(404)
            
            icon_id = ''
            if user_activity.icon is not None:
                icon_id = user_activity.icon.key().id()
                
            created_at = user_activity.created_at + datetime.timedelta(hours=9)
            
            data = {'id': user_activity.key().id(), 'name': user_activity.name, 'tags': user_activity.tags, 'icon': icon_id, 'lat': user_activity.geo.lat, 'lng': user_activity.geo.lon, 'created_at': created_at.strftime('%Y-%m-%d %H:%M:%S (JST)')}
        
            memcache.add('marker_data_%s' % marker_id, data, 3600)
            logging.info('Add memcache.')
            
        else:
            logging.info('Load memcache.')
        
        json = simplejson.dumps(data, ensure_ascii=False)
        self.response.content_type = 'application/json'
        self.response.out.write(json)
        
class GetTagIndexAPI(webapp.RequestHandler):
    def get(self):
        
        map_id = self.request.get('id')
        
        data = memcache.get('tag_index_%s' % map_id)
        if data is None:
            user_maps = UserMaps.all().filter('visible =', True).filter('map_id =', map_id).get()
            if user_maps is None:
                logging.error('map_id not found.')
                return self.error(404)
            
            user_activity_tag_index_list = UserActivityTagIndex.all().filter('user_maps =', user_maps.key()).fetch(100)
            if len(user_activity_tag_index_list) <= 0:
                logging.error('Tag index not found.')
                return self.error(404)
            
            data = []
            for user_activity_tag_index in user_activity_tag_index_list:
                data.append({'id': user_activity_tag_index.key().id(), 'tag': user_activity_tag_index.tag, 'count': user_activity_tag_index.count})
            
            memcache.add('tag_index_%s' % map_id, data, 3600)
            logging.info('Add memcache.')
            
        else:
            logging.info('Load memcache.')
        
        json = simplejson.dumps(data, ensure_ascii=False)
        self.response.content_type = 'application/json'
        self.response.out.write(json)
        
class GetMarkerIdFromIndexAPI(webapp.RequestHandler):
    def get(self):
        
        index_id = self.request.get('id')
        
        data = memcache.get('tag_id_list_%s' % index_id)
        if data is None:
            user_activity_tag_index = UserActivityTagIndex.get_by_id(int(index_id))
            if user_activity_tag_index is None:
                logging.error('Tag index not found.')
                return self.error(404)
            
            data = []
            for marker_id in user_activity_tag_index.user_activity_id_list.split(','):
                data.append(marker_id)
            
            memcache.add('tag_id_list_%s' % index_id, data, 3600)
            logging.info('Add memcache.')
            
        else:
            logging.info('Load memcache.')
        
        json = simplejson.dumps(data, ensure_ascii=False)
        self.response.content_type = 'application/json'
        self.response.out.write(json)
        
application = webapp.WSGIApplication(
                                     [('/api/get_icon', GetIconAPI),
                                      ('/api/get_marker_data', GetMarkerDataAPI),
                                      ('/api/get_tag_index', GetTagIndexAPI),
                                      ('/api/get_marker_id_from_index', GetMarkerIdFromIndexAPI)],
                                     debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
    