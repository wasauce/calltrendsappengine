#!/usr/bin/env python
""" CallTrends helper functions."""

__author__ = 'Bill Ferrell'

import logging

## Set logging level.
logging.getLogger().setLevel(logging.INFO)

def processFormData(request):
  """Inputs data in the db from the Andorid App.

  Args:
    request: The post request containing a single call's data.
  Returns:
    Nothing
  """
  current_email = cgi.escape(self.request.get('email'))
  logging.info('name is %s' % entry.name)
  #Now query the DB to see if we have an existing record.
  ind_metrics = db.GqlQuery("SELECT * FROM IndividualMetrics WHERE email = :1",
                            current_email)
  if not ind_metrics == None:
    if request.get('duration') < 10:
      ind_metrics.duration_10_seconds += 1
    if request.get('duration') < 30:
      ind_metrics.duration_30_seconds += 1
    if request.get('duration') < 60:
      ind_metrics.duration_1_min += 1
    if request.get('duration') < (60*5):
      ind_metrics.duration_5_min += 1
    if request.get('duration') < (60*10):
      ind_metrics.duration_10_min += 1
    if request.get('duration') < (60*30):
      ind_metrics.duration_30_min += 1
    if request.get('duration') < (60*60):
      ind_metrics.duration_1_hour += 1
    if request.get('duration') >= (60*60):
      ind_metrics.duration_greater_than_1_hr += 1
    if request.get('incoming') == 1:
      ind_metrics.total_incoming_type += 1
    if request.get('outgoing') == 1:
      ind_metrics.total_outgoing_type += 1
    if request.get('missed') == 1:
      ind_metrics.total_missed_type += 1
    if request.get('missed') == 0:
      ind_metrics.total_answered_type += 1
    ind_metrics.total_calls += 1
    ind_metrics.total_duration += request.get('duration')
    ind_metrics.put()
  else:
  	new_ind_metrics = IndividualMetrics()
	new_ind_metrics.email = cgi.escape(self.request.get('email'))
    if request.get('duration') < 10:
      new_ind_metrics.duration_10_seconds += 1
    elif request.get('duration') < 30:
      new_ind_metrics.duration_30_seconds += 1
    elif request.get('duration') < 60:
      new_ind_metrics.duration_1_min += 1
    elif request.get('duration') < (60*5):
      new_ind_metrics.duration_5_min += 1
    elif request.get('duration') < (60*10):
      new_ind_metrics.duration_10_min += 1
    elif request.get('duration') < (60*30):
      new_ind_metrics.duration_30_min += 1
    elif request.get('duration') < (60*60):
      new_ind_metrics.duration_1_hour += 1
    elif request.get('duration') >= (60*60):
      new_ind_metrics.duration_greater_than_1_hr += 1
    if request.get('incoming') == 1:
      new_ind_metrics.total_incoming_type += 1
    if request.get('outgoing') == 1:
      new_ind_metrics.total_outgoing_type += 1
    if request.get('missed') == 1:
      new_ind_metrics.total_missed_type += 1
    if request.get('missed') == 0:
      new_ind_metrics.total_answered_type += 1
    new_ind_metrics.total_calls += 1
    new_ind_metrics.total_duration += request.get('duration')	
	new_ind_metrics.put()
	
    new_ind_entry = IndividualCallData()
    new_ind_entry.email = cgi.escape(self.request.get('email'))
    new_ind_entry.number = cgi.escape(self.request.get('phonenumber'))
    new_ind_entry.numberlabel = cgi.escape(self.request.get('numberlabel'))
    new_ind_entry.numbertype = cgi.escape(self.request.get('numbertype'))
    new_ind_entry.date = cgi.escape(self.request.get('date'))
    new_ind_entry.duration = cgi.escape(self.request.get('duration'))
    new_ind_entry.incoming_type = cgi.escape(self.request.get('incoming_type'))
    new_ind_entry.outgoing_type = cgi.escape(self.request.get('outgoing_type'))
    new_ind_entry.missed_type = cgi.escape(self.request.get('missed_type'))
    new_ind_entry.answered_type = cgi.escape(self.request.get('answered_type'))
    new_ind_entry.number_type = cgi.escape(self.request.get('number_type'))
	new_ind_metrics.put()

    version = 1
    g_data = db.GqlQuery("SELECT * FROM CollectiveCallData WHERE version = :1",
                         version)
    if request.get('duration') < 10:
      g_data.duration_10_seconds += 1
    elif request.get('duration') < 30:
      g_data.duration_30_seconds += 1
    elif request.get('duration') < 60:
      g_data.duration_1_min += 1
    elif request.get('duration') < (60*5):
      g_data.duration_5_min += 1
    elif request.get('duration') < (60*10):
      g_data.duration_10_min += 1
    elif request.get('duration') < (60*30):
      g_data.duration_30_min += 1
    elif request.get('duration') < (60*60):
      g_data.duration_1_hour += 1
    elif request.get('duration') >= (60*60):
      g_data.duration_greater_than_1_hr += 1
    if request.get('incoming') == 1:
      g_data.total_incoming_type += 1
      g_data.total_incoming_time += request.get('duration')
    if request.get('outgoing') == 1:
      g_data.total_outgoing_type += 1
      g_data.total_outgoing_time += request.get('duration')
    if request.get('missed') == 1:
      g_data.total_missed_type += 1
    if request.get('missed') == 0:
      g_data.total_answered_type += 1
    g_data.total_calls += 1
    g_data.total_duration += request.get('duration')
