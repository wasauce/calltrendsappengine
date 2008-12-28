#!/usr/bin/env python
"""
CallTrends
Version 0.0.2

We use the webapp.py WSGI framework to handle CGI requests, using the
wsgiref module to wrap the webapp.py WSGI application in a CGI-compatible
container. See webapp.py for documentation on RequestHandlers and the URL
mapping at the bottom of this module.

We use Django templates, which are described at
http://www.djangoproject.com/documentation/templates/. We define a custom
Django template filter library in templatefilters.py for use in dilbertindex
templates.
"""

__author__ = '(Bill Ferrell)'

import cgi
import datetime
import htmlentitydefs
import math
import os
import re
import sgmllib
import sys
import time
import urllib
import logging
import wsgiref.handlers
import traceback
import random

# http://pygooglechart.slowchop.com/
import pygooglechart

import calltrendshelpers

from google.appengine.api import datastore
from google.appengine.api import datastore_types
from google.appengine.api import datastore_errors
from google.appengine.api import users
from google.appengine.api import memcache
from google.appengine.api import mail
from google.appengine.ext import webapp
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import login_required
from google.appengine.ext import search
from google.appengine.ext import bulkload
from google.appengine.ext import db

## Set logging level.
logging.getLogger().setLevel(logging.INFO)

# Add our custom Django template filters to the built in filters
template.register_template_library('templatefilters')

# Set to true to see stack traces and template debugging information
_DEBUG = True

class IndividualCallData(db.Model):
  """This is the AppEngine data model for the individual call data.
  All call data will be input into the database so that they can be updated,
  queried and controlled from a single location. This will allow for easy 
  growth
  """

  email = db.EmailProperty()
  number = db.PhoneNumberProperty()  #db.db.PhoneNumberProperty(required=True)
  numberlabel = db.StringProperty()
  numbertype = db.StringProperty()
  date = int
  duration = int
  incoming_type = int
  outgoing_type = int
  missed_type = int
  answered_type = int
  number_type = db.StringProperty()

class IndividualMetrics(db.Model):
  """
  This is the AppEngine data model for the individuals metrics. 
  All call data will be input into the database so that they can be updated,
  queried and controlled from a single location. This will allow for easy 
  growth.
  """
  email = db.EmailProperty()
  duration_10_seconds = int # indicates call was less than 10 seconds
  duration_30_seconds = int # indicates call was >9.999999 seconds but less than 30
  duration_1_min = int # call was greater than 30 but less than 1 min
  duration_5_min = int # call was greater than 1 min but less than 5 mins
  duration_10_min = int # call was greater than 5 mins but less than 10 mins
  duration_30_min = int # call was greater than 10 mins but less than 30 mins
  duration_1_hour = int # call was greater than 30 mins but less than 1 hr
  duration_greater_than_1_hr = int # call was greater than 1 hr
  total_incoming_type = int
  total_outgoing_type = int
  total_missed_type = int
  total_answered_type = int
  total_calls = int
  total_duration = int
#---Top 10 incoming  #Could be found by querying + offline processing
#---Top 10 missed    #Could be found by querying + offline processing
#---Top 10 outgoing
#---Number of minutes per day, week, month, year   #found by querying...
#---Number of calls per day, week, month, year    #found by querying...



class CollectiveCallData(db.Model):
  """
  This is the AppEngine data model for the collective call data
  All call data will be input into the databse so that they can be updated,
  queried and controlled from a single location. This will allow for easy 
  growth
  """

  version = int
  duration_10_seconds = int # indicates call was less than 10 seconds
  duration_30_seconds = int # indicates call was >9.999999 seconds but less than 30
  duration_1_min = int # call was greater than 30 but less than 1 min
  duration_5_min = int # call was greater than 1 min but less than 5 mins
  duration_10_min = int # call was greater than 5 mins but less than 10 mins
  duration_30_min = int # call was greater than 10 mins but less than 30 mins
  duration_1_hour = int # call was greater than 30 mins but less than 1 hr
  duration_greater_than_1_hr = int # call was greater than 1 hr
  total_incoming_type = int
  total_outgoing_type = int
  total_missed_type = int
  total_answered_type = int
  total_calls = int
  total_duration = int
  total_new = int # TODO: What is this?
  total_incoming_time = int
  total_outgoing_time = int
#---Number of minutes per day, week, month, year   / incoming vs outgoing # some of this will need to be calculated nightly
#---Number of calls per day, week, month, year / incoming vs outgoing # some of this will need to be calculated nightly. 


class BaseRequestHandler(webapp.RequestHandler):
  """The common class for all CallTrends requests"""

  def handle_exception(self, exception, debug_mode):
      exception_name = sys.exc_info()[0].__name__
      exception_details = str(sys.exc_info()[1])
      exception_traceback = ''.join(traceback.format_exception(*sys.exc_info()))
      logging.error(exception_traceback)
      exception_expiration = 600 # seconds 
      mail_admin = "wferrell@gmail.com" # must be an admin -- be sure to remove before committing
      sitename = "calltrends"
      throttle_name = 'exception-'+exception_name
      throttle = memcache.get(throttle_name)
      if throttle is None:
          memcache.add(throttle_name, 1, exception_expiration)
          subject = '[%s] exception [%s: %s]' % (sitename, exception_name,
                                                 exception_details)
          mail.send_mail_to_admins(sender=mail_admin,
                                   subject=subject,
                                   body=exception_traceback)

      values = {}
      template_name = 'error.html'
      #if users.is_current_user_admin():
      #    values['traceback'] = exception_traceback
      values['traceback'] = exception_traceback
      directory = os.path.dirname(os.environ['PATH_TRANSLATED'])
      path = os.path.join(directory, os.path.join('templates', template_name))
      self.response.out.write(template.render(path, values, debug=_DEBUG))

  def random_data(self):
    return [random.randint(1, 100) for a in xrange(50)]

  def generate(self, template_name, template_values={}):
    """Generates the given template values into the given template.

    Args:
        template_name: the name of the template file (e.g., 'index.html')
        template_values: a dictionary of values to expand into the template
    """
    # Create a chart object of 500x100 pixels
    logo_chart = pygooglechart.SparkLineChart(500, 100)
    logo_chart.add_data(self.random_data())
    logo_chart.add_fill_simple('224499')

    # Populate the values common to all templates
    values = {
      #'user': users.GetCurrentUser(),
      'debug': self.request.get('deb'),
      'logourl': logo_chart.get_url(),
    }
    values.update(template_values)
    directory = os.path.dirname(os.environ['PATH_TRANSLATED'])
    path = os.path.join(directory, os.path.join('templates', template_name))
    self.response.out.write(template.render(path, values, debug=_DEBUG))

class UnderConstructionHandler(BaseRequestHandler):
  """ Under Construction page handler. 

     Generates an underconstruction page
  """
  def get(self):
    logging.info('Visiting the undercontruction page')

    self.generate('underconstruction.html', {
      #'mytab': 'none',
    })

class HomePageHandler(BaseRequestHandler):
  """  Generates the start/home page.
  """

  def get(self, garbageinput=None):
    logging.info('Visiting the homepage')

    self.generate('index.html', {
      #'logourl': chart.get_url(),
    })

class AboutPageHandler(BaseRequestHandler):
  """ Generates the about page.

  """
  def get(self):
    logging.info('Visiting the about page')
    self.generate('about.html', {
      #'title': 'Getting Started',
    })


class FAQsPageHandler(BaseRequestHandler):
  """ Generates the FAQ page.
      CURRENTLY UNUSED
  """
  def get(self):
    logging.info('Visiting the FAQs page')
    self.generate('faqs.html', {
      #'title': 'Getting Started',
    })	

class DataInputHandler(BaseRequestHandler):
  """ Handler to process incoming CallTrends data.

  GET calls redirected
  POST calls will be processed and the data added to the database.
  """
  def get(self):
    """ Function for GET requests that redirects to the main page.
    The DataInputHandler should only be called via POST.
    """
    logging.info('Attempting to access DataInputHandler via GET')
    self.redirect("/index")


  def post(self):
    """ Post method to accept CallTrends data.
    
    """
    logging.info('Accessing DataInputHandler via POST')
    try:
      #calltrendshelpers.processFormData(self.request):
      self.response.out.write("SUCCESS")
    except:
      self.error(500)
      mail_admin = 'wferrell@gmail.com' # Pull this code out when posting.
      subject = 'CallTrends - DataInputHander Error'
      mail.send_mail_to_admins(sender=mail_admin,
                                 subject=subject,
                                 body=self.request)

class TestPageHandler(BaseRequestHandler):
  """ Generates the test page.

  """
  def get(self):
    logging.info('Visiting the test page')
    self.generate('test.html', {
      #'title': 'Getting Started',
    })

class MyStatsPageHandler(BaseRequestHandler):
  """ Generates the My Stats Page.
  """
  def get(self):
    logging.info('Visiting the My Stats page.')

    user = users.get_current_user()
    if user:
      #print "BILL READ THIS NOW" #QUERY HERE TO GET THE DATA TO OUTPUT AND GRAPH GRAPH GRAPH
      pass
    else:
      	self.redirect(users.create_login_url(self.request.uri))

    self.generate('mystats.html', {
      'logouturl': users.create_logout_url('/index'),
      #'':,
    })

class CommunityStatsPageHandler(BaseRequestHandler):
  """ Generates the Community Stats Page.

  """
  def get(self):
    logging.info('Visiting the Community Stats page.')
    self.generate('communitystats.html', {
      #'': ,
    })

class GettingStartedPageHandler(BaseRequestHandler):
  """ Generates the Getting Started Page.

  """
  def get(self):
    logging.info('Visiting the Getting Started Page.')
    self.generate('gettingstarted.html', {
      #'title': 'Getting Started',
    })

class QRCodePageHandler(BaseRequestHandler):
  """ Generates the QR Code Page.

  """
  def get(self):
    logging.info('Visiting the QR Code Page.')
    self.generate('QRcode.html', {
      #'title': 'Getting Started',
    })


class InitPageHandler(BaseRequestHandler):
  """ Init page handler -- initializes the databases.

  """
  def get(self):
    logging.info('Visiting the init page for setup.')
    self.redirect("/index")

# Map URLs to our RequestHandler classes above
_CALLTRENDS_URLS = [
# after each URL map we list the html template that is displayed
   ('/', HomePageHandler), #index.html
   ('/index', HomePageHandler), #index.html
   ('/about', AboutPageHandler), #about.html
#   ('/faqs', FAQsPageHandler), #faqs.html -Took this out -- not needed.
   ('/datain', DataInputHandler), #submitdata.html
   ('/test', TestPageHandler), #test.html
   ('/mystats', MyStatsPageHandler), #mystats.html
   ('/communitystats', CommunityStatsPageHandler), #communitystats.html
#   ('/gettingstarted', GettingStartedPageHandler), #gettingstarted.html
   ('/init', InitPageHandler), # This is a redirect.
   ('/QRcode', QRCodePageHandler), #QRcode.html
#   ('/download', DownloadHandler), # This will allow the user to download the data.
   ('/.*$', HomePageHandler), #index.html
]

def main():
  application = webapp.WSGIApplication(_CALLTRENDS_URLS, debug=_DEBUG)
  run_wsgi_app(application)

if __name__ == '__main__':
  main()