#!/usr/bin/env python

"""main.py - This file contains handlers that are called by taskqueue and/or
cronjobs."""
import logging
import webapp2
from google.appengine.api import mail, app_identity
from api import HangmanApi

from models import User, Game


class SendReminderEmail(webapp2.RequestHandler):
    def get(self):
        """Send a reminder email to each User with an email about games.
        Called every hour using a cron job"""
        app_id = app_identity.get_application_id()
        users = User.query(User.email is None)
        for user in users:
            games = Game.query(Game.user == user.key).\
                filter(not Game.game_over).\
                fetch()
            if games:
                logging.info('This is the number of games: ' + str(len(games)))
                subject = 'Reminder - Unfinished Game!'
                body = 'Hello {0}, you have an unfinished Hangman game!'\
                       '\nKey(s) are:'.format(user.name)
                for g in games:
                    body += "\n" + str(g.key.urlsafe())
                logging.info("BODY: " + body)
                # This will send test emails, the arguments to send_mail are:
                # from, to, subject, body
                mail.send_mail('noreply@{}.appspotmail.com'.format(app_id),
                               user.email,
                               subject,
                               body)


class UpdateAverageMovesRemaining(webapp2.RequestHandler):
    def post(self):
        """Update game listing announcement in memcache."""
        HangmanApi._cache_average_strikes()
        self.response.set_status(204)


app = webapp2.WSGIApplication([
    ('/crons/send_reminder', SendReminderEmail),
    ('/tasks/cache_average_strikes', UpdateAverageMovesRemaining),
], debug=True)
