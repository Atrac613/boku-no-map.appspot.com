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
        
application = webapp.WSGIApplication(
                                     [('/api/get_icon', GetIconAPI)],
                                     debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
    