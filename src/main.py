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

class IndexPage(webapp.RequestHandler):
    def get(self):

        template_values = {
        }
        
        path = os.path.join(os.path.dirname(__file__), 'templates/index.html')
        self.response.out.write(template.render(path, template_values))

application = webapp.WSGIApplication(
                                     [('/', IndexPage)],
                                     debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
    