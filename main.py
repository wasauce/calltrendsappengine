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
  date = db.IntegerProperty() #Should change this potentially....
  duration = db.IntegerProperty()
  incoming_type = db.IntegerProperty()
  outgoing_type = db.IntegerProperty()
  missed_type = db.IntegerProperty()
  answered_type = db.IntegerProperty()
  creation_time = db.DateTimeProperty(auto_now_add=True)

class IndividualMetrics(db.Model):
  """
  This is the AppEngine data model for the individuals metrics. 
  All call data will be input into the database so that they can be updated,
  queried and controlled from a single location. This will allow for easy 
  growth.
  """
  email = db.EmailProperty()
  duration_10_seconds = db.IntegerProperty() # indicates call was less than 10 seconds
  duration_30_seconds = db.IntegerProperty() # indicates call was >9.999999 seconds but less than 30
  duration_1_min = db.IntegerProperty() # call was greater than 30 but less than 1 min
  duration_5_min = db.IntegerProperty() # call was greater than 1 min but less than 5 mins
  duration_10_min = db.IntegerProperty() # call was greater than 5 mins but less than 10 mins
  duration_30_min = db.IntegerProperty() # call was greater than 10 mins but less than 30 mins
  duration_1_hour = db.IntegerProperty() # call was greater than 30 mins but less than 1 hr
  duration_greater_than_1_hr = db.IntegerProperty() # call was greater than 1 hr
  total_incoming_type = db.IntegerProperty()
  total_outgoing_type = db.IntegerProperty()
  total_missed_type = db.IntegerProperty()
  total_answered_type = db.IntegerProperty()
  total_calls = db.IntegerProperty()
  total_duration = db.IntegerProperty()
  total_incoming_time = db.IntegerProperty()
  total_outgoing_time = db.IntegerProperty()
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

  version = db.IntegerProperty()
  duration_10_seconds = db.IntegerProperty() # indicates call was less than 10 seconds
  duration_30_seconds = db.IntegerProperty() # indicates call was >9.999999 seconds but less than 30
  duration_1_min = db.IntegerProperty() # call was greater than 30 but less than 1 min
  duration_5_min = db.IntegerProperty() # call was greater than 1 min but less than 5 mins
  duration_10_min = db.IntegerProperty() # call was greater than 5 mins but less than 10 mins
  duration_30_min = db.IntegerProperty() # call was greater than 10 mins but less than 30 mins
  duration_1_hour = db.IntegerProperty() # call was greater than 30 mins but less than 1 hr
  duration_greater_than_1_hr = db.IntegerProperty() # call was greater than 1 hr
  total_incoming_type = db.IntegerProperty()
  total_outgoing_type = db.IntegerProperty()
  total_missed_type = db.IntegerProperty()
  total_answered_type = db.IntegerProperty()
  total_calls = db.IntegerProperty()
  total_duration = db.IntegerProperty()
  total_new = db.IntegerProperty() # TODO: What is this?
  total_incoming_time = db.IntegerProperty()
  total_outgoing_time = db.IntegerProperty()
#---Number of minutes per day, week, month, year   / incoming vs outgoing # some of this will need to be calculated nightly
#---Number of calls per day, week, month, year / incoming vs outgoing # some of this will need to be calculated nightly. 

class CollectiveCharts(db.Model):
  """This is the AppEngine data model to store collective charts."""
  pass


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


def processFormData(request):
  """Inputs data in the db from the Andorid App.

  Args:
    request: The post request containing a single call's data.
  Returns:
    Nothing
  """
  current_email = cgi.escape(request.get('email'))
  #Now query the DB to see if we have an existing record.
  ind_metrics_gql = db.GqlQuery("SELECT * FROM IndividualMetrics WHERE email = :1",
                                current_email)
  if ind_metrics_gql.count() > 0:
    ind_metrics = ind_metrics_gql[0]
  else:
    ind_metrics = None
  if ind_metrics:
    logging.info('ind_metrics: %s' % dir(ind_metrics))
    if request.get('duration') < 10:
      if ind_metrics.duration_10_seconds:
        ind_metrics.duration_10_seconds += 1
      else:
        ind_metrics.duration_10_seconds = 1
    if request.get('duration') < 30:
      if ind_metrics.duration_30_seconds:
        ind_metrics.duration_30_seconds += 1
      else:
        ind_metrics.duration_30_seconds = 1
    if request.get('duration') < 60:
      if ind_metrics.duration_1_min:
        ind_metrics.duration_1_min += 1
      else:
        ind_metrics.duration_1_min = 1
    if request.get('duration') < (60*5):
      if ind_metrics.duration_5_min:
        ind_metrics.duration_5_min += 1
      else:
        ind_metrics.duration_5_min = 1
    if request.get('duration') < (60*10):
      if ind_metrics.duration_10_min:
        ind_metrics.duration_10_min += 1
      else:
        ind_metrics.duration_10_min = 1
    if request.get('duration') < (60*30):
      if ind_metrics.duration_30_min:
        ind_metrics.duration_30_min += 1
      else:
        ind_metrics.duration_30_min = 1
    if request.get('duration') < (60*60):
      if ind_metrics.duration_1_hour:
       ind_metrics.duration_1_hour += 1
      else:
        ind_metrics.duration_1_hour = 1
    if request.get('duration') >= (60*60):
      if ind_metrics.duration_greater_than_1_hr:
        ind_metrics.duration_greater_than_1_hr += 1
      else:
        ind_metrics.duration_greater_than_1_hr = 1
    if request.get('incoming') == 1:
      if ind_metrics.total_incoming_type:
        ind_metrics.total_incoming_type += 1
      else:
        ind_metrics.total_incoming_type = 1
    if request.get('outgoing') == 1:
      if ind_metrics.total_outgoing_type:
        ind_metrics.total_outgoing_type += 1
      else:
        ind_metrics.total_outgoing_type = 1
    if request.get('missed') == 1:
      if ind_metrics.total_missed_type:
        ind_metrics.total_missed_type += 1
      else:
        ind_metrics.total_missed_type = 1
    if request.get('missed') == 0:
      if ind_metrics.total_answered_type:
        ind_metrics.total_answered_type += 1
      else:
        ind_metrics.total_answered_type = 1      
    if ind_metrics.total_calls:
      ind_metrics.total_calls += 1
    else:
      ind_metrics.total_calls = 1
    if ind_metrics.total_duration:
      ind_metrics.total_duration += int(request.get('duration'))
    else:
      ind_metrics.total_duration = int(request.get('duration'))
    ind_metrics.put()
  else:
    new_ind_metrics = IndividualMetrics()
    new_ind_metrics.email = cgi.escape(request.get('email'))
    if request.get('duration') < 10:
      new_ind_metrics.duration_10_seconds = 1
    elif request.get('duration') < 30:
      new_ind_metrics.duration_30_seconds = 1
    elif request.get('duration') < 60:
      new_ind_metrics.duration_1_min = 1
    elif request.get('duration') < (60*5):
      new_ind_metrics.duration_5_min = 1
    elif request.get('duration') < (60*10):
      new_ind_metrics.duration_10_min = 1
    elif request.get('duration') < (60*30):
      new_ind_metrics.duration_30_min = 1
    elif request.get('duration') < (60*60):
      new_ind_metrics.duration_1_hour = 1
    elif request.get('duration') >= (60*60):
      new_ind_metrics.duration_greater_than_1_hr = 1
    if request.get('incoming') == 1:
      new_ind_metrics.total_incoming_type = 1
    if request.get('outgoing') == 1:
      new_ind_metrics.total_outgoing_type = 1
    if request.get('missed') == 1:
      new_ind_metrics.total_missed_type = 1
    if request.get('missed') == 0:
      new_ind_metrics.total_answered_type = 1
    new_ind_metrics.total_calls = 1
    new_ind_metrics.total_duration = request.get('duration')	
    new_ind_metrics.put()

  new_ind_entry = IndividualCallData()
  new_ind_entry.email = db.Email(cgi.escape(request.get('email')))
  new_ind_entry.number = db.PhoneNumber(cgi.escape(request.get('phonenumber')))
  new_ind_entry.numberlabel = cgi.escape(request.get('numberlabel'))
  new_ind_entry.numbertype = cgi.escape(request.get('numbertype'))
  new_ind_entry.date = int(cgi.escape(request.get('date')))
  new_ind_entry.duration = int(cgi.escape(request.get('duration')))
  new_ind_entry.incoming_type = int(cgi.escape(request.get('incoming_type')))
  new_ind_entry.outgoing_type = int(cgi.escape(request.get('outgoing_type')))
  new_ind_entry.missed_type = int(cgi.escape(request.get('missed_type')))
  new_ind_entry.answered_type = int(cgi.escape(request.get('answered_type')))
  new_ind_entry.put()

  version = 1
  g_data_gql = db.GqlQuery("SELECT * FROM CollectiveCallData WHERE version = :1",
                       version)
  if g_data_gql.count() > 0:
    g_data = ind_metrics_gql[0]
  else:
    g_data = CollectiveCallData()
  if request.get('duration') < 10:
    if g_data.duration_10_seconds:
      g_data.duration_10_seconds += 1
    else:
      g_data.duration_10_seconds = 1
  elif request.get('duration') < 30:
    if g_data.duration_30_seconds:
      g_data.duration_30_seconds += 1
    else:
      g_data.duration_30_seconds = 1
  elif request.get('duration') < 60:
    if g_data.duration_1_min:
      g_data.duration_1_min += 1
    else:
      g_data.duration_1_min = 1
  elif request.get('duration') < (60*5):
    if g_data.duration_5_min:
      g_data.duration_5_min += 1
    else:
      g_data.duration_5_min = 1
  elif request.get('duration') < (60*10):
    if g_data.duration_10_min:
      g_data.duration_10_min += 1
    else:
      g_data.duration_10_min = 1
  elif request.get('duration') < (60*30):
    if g_data.duration_30_min:
      g_data.duration_30_min += 1
    else:
      g_data.duration_30_min = 1
  elif request.get('duration') < (60*60):
    if g_data.duration_1_hour:
      g_data.duration_1_hour += 1
    else:
      g_data.duration_1_hour = 1
  elif request.get('duration') >= (60*60):
    if g_data.duration_greater_than_1_hr:
      g_data.duration_greater_than_1_hr += 1
    else:
      g_data.duration_greater_than_1_hr = 1
  if request.get('incoming') == 1:
    if g_data.total_incoming_type:
      g_data.total_incoming_type += 1
      g_data.total_incoming_time += int(request.get('duration'))
    else:
      g_data.total_incoming_type = 1
      g_data.total_incoming_time = int(request.get('duration'))      
  if request.get('outgoing') == 1:
    if g_data.total_outgoing_type:
      g_data.total_outgoing_type += 1
      g_data.total_outgoing_time += int(request.get('duration'))
    else:
      g_data.total_outgoing_type = 1
      g_data.total_outgoing_time = int(request.get('duration'))      
  if request.get('missed') == 1:
    if g_data.total_missed_type:
      g_data.total_missed_type += 1
    else:
      g_data.total_missed_type = 1
  if request.get('missed') == 0:
    if g_data.total_answered_type:
      g_data.total_answered_type += 1
    else:
      g_data.total_answered_type = 1
  if g_data.total_calls:
    g_data.total_calls += 1
  else:
    g_data.total_calls = 1
  if g_data.total_duration:
    g_data.total_duration += int(request.get('duration'))
  else:
    g_data.total_duration = int(request.get('duration'))
  g_data.put()


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
    logging.info('Request: %s' % self.request)
    processFormData(self.request)
    self.response.out.write("OK")

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
      'nickname': user.nickname(),
#      'total_duration':,
#      'total_calls':,
#      'total_answered_type':,
#      'total_missed_type':,
#      'total_incoming_type':,
#      'total_outgoing_type':,
#      'total_incoming_time':,
#      'total_outgoing_time':,
#      'duration_10_seconds':,
#      'duration_30_seconds':,
#      'duration_1_min':,
#      'duration_5_min':,
#      'duration_10_min':,
#      'duration_30_min':,
#      'duration_1_hour':,
#      'duration_greater_than_1_hr':,
    })

class CommunityStatsPageHandler(BaseRequestHandler):
  """ Generates the Community Stats Page.

  """
  def get(self):
    logging.info('Visiting the Community Stats page.')
    self.generate('communitystats.html', {
	#      'total_duration':,
	#      'total_calls':,
	#      'total_answered_type':,
	#      'total_missed_type':,
	#      'total_incoming_type':,
	#      'total_outgoing_type':,
	#      'total_incoming_time':,
	#      'total_outgoing_time':,
	#      'duration_10_seconds':,
	#      'duration_30_seconds':,
	#      'duration_1_min':,
	#      'duration_5_min':,
	#      'duration_10_min':,
	#      'duration_30_min':,
	#      'duration_1_hour':,
	#      'duration_greater_than_1_hr':,
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

class InitPageHandler():
  """ Init page handler -- initializes the databases.

  """
  def get(self):
    logging.info('Visiting the init page for setup.')
    self.redirect("/index")
    user = users.get_current_user()
    if user.is_current_user_admin():
      #INSERT CODE TO RUN HERE
      print "Ran init code"
    else:
      self.redirect("/index")


# Map URLs to our RequestHandler classes above
_CALLTRENDS_URLS = [
# after each URL map we list the html template that is displayed
   ('/', HomePageHandler), #index.html
   ('/index', HomePageHandler), #index.html
   ('/about', AboutPageHandler), #about.html
#   ('/faqs', FAQsPageHandler), #faqs.html -Took this out -- not needed.
   ('/datain', DataInputHandler),
   ('/test', TestPageHandler), #test.html
   ('/mystats', MyStatsPageHandler), #mystats.html
   ('/communitystats', CommunityStatsPageHandler), #communitystats.html
#   ('/gettingstarted', GettingStartedPageHandler), #gettingstarted.html
   ('/init', InitPageHandler), # This is a redirect.
   ('/QRcode', QRCodePageHandler), #QRcode.html
#   ('/download', DownloadHandler), # This will allow the user to download the data. Host this on Google Code.
   ('/.*$', HomePageHandler), #index.html  #REPLACE -- with code from other apps
]

def main():
  application = webapp.WSGIApplication(_CALLTRENDS_URLS, debug=_DEBUG)
  run_wsgi_app(application)

if __name__ == '__main__':
  main()
