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
from db import UserActivityTagIndex

class BuildTagIndexTask(webapp.RequestHandler):
    def post(self):
        map_id = self.request.get('map_id')
        
        user_maps = UserMaps.all().filter('map_id =', map_id).get()
        if user_maps is None:
            logging.error('map_id not found.')
            return
        
        user_activity_list = UserActivity.all().filter('user_maps =', user_maps.key()).fetch(100)
        if len(user_activity_list) > 0:
            index = {}
            for user_activity in user_activity_list:
                if user_activity.tags is not None:
                    for tag in user_activity.tags.split(','):
                        if len(tag) > 0:
                            #logging.info('Tag: %s' % tag)
                            if tag in index:
                                activity_id_list = index[tag]
                                activity_id_list.append(str(user_activity.key().id()))
                            else:
                                activity_id_list = []
                                activity_id_list.append(str(user_activity.key().id()))
                                index[tag] = activity_id_list
            
            user_activity_tag_index_list = UserActivityTagIndex.all().filter('user_maps =', user_maps.key()).fetch(500)
            if len(user_activity_tag_index_list) > 0:
                logging.info('Clear Index: %d' % len(user_activity_tag_index_list))
                for user_activity_tag_index in user_activity_tag_index_list:
                    user_activity_tag_index.delete()
                    
            for tag, activity_id_list in index.items():
                user_activity_tag_index_list = UserActivityTagIndex()
                user_activity_tag_index_list.user_maps = user_maps.key()
                user_activity_tag_index_list.tag = tag
                user_activity_tag_index_list.user_activity_id_list = ','.join(activity_id_list)
                user_activity_tag_index_list.put()
                
            logging.info('Add Index: %d' % len(index))
            
application = webapp.WSGIApplication(
                                     [('/task/build_tag_index', BuildTagIndexTask)],
                                     debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()