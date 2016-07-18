"""models.py - This file contains the class definitions for the Datastore
entities used by the Game. Because these classes are also regular Python
classes they can include methods (such as 'to_form' and 'new_game')."""

import random
import json
from datetime import date
from protorpc import messages
from google.appengine.ext import ndb

with open("wordlist.txt") as f:
    wordList = f.read().splitlines()


class User(ndb.Model):
    """User profile"""
    name = ndb.StringProperty(required=True)
    email = ndb.StringProperty()
    games_played = ndb.IntegerProperty(required=True, default=0)
    career_points = ndb.IntegerProperty(required=True, default=0)
    performance = ndb.ComputedProperty(lambda self: self.career_points /
                                       self.games_played if self.games_played >
                                       0 else 0)

    def to_form(self):
        """Returns a UserForm representation of the User"""
        return UserForm(name=self.name,
                        games_played=self.games_played,
                        career_points=self.career_points,
                        performance=float(self.performance))


class Game(ndb.Model):
    """Game object"""
    target_string = ndb.StringProperty(required=True)
    shown_string = ndb.StringProperty(required=True)
    guessed_letters = ndb.StringProperty(required=True, default="")
    correct_letters = ndb.StringProperty(required=True, default="")
    strikes_remaining = ndb.IntegerProperty(required=True, default=6)
    game_over = ndb.BooleanProperty(required=True, default=False)
    user = ndb.KeyProperty(required=True, kind='User')
    history = ndb.JsonProperty(required=True, default=[])

    @classmethod
    def new_game(cls, user):
        """Creates and returns a new game - strikes always 6:
        1 head, 1 body, 2 legs, 2 arms"""
        targString = wordList[random.randint(0, len(wordList) - 1)]
        blankString = '_' * len(targString)
        game = Game(user=user,
                    target_string=targString,
                    shown_string=blankString)
        game.put()
        return game

    def to_form(self, message):
        """Returns a GameForm representation of the Game"""
        form = GameForm()
        form.urlsafe_key = self.key.urlsafe()
        form.user_name = self.user.get().name
        form.strikes_remaining = self.strikes_remaining
        form.shown_string = self.shown_string
        form.guessed_letters = self.guessed_letters
        form.game_over = self.game_over
        form.message = message
        return form

    def history_to_form(self):
        """Returns a GameHistoryForm representation of the Game"""
        return GameHistoryForm(urlsafe_key=self.key.urlsafe(),
                               game_over=self.game_over,
                               user_name=self.user.get().name,
                               history=json.dumps(self.history, sort_keys=True,
                                                  indent=2,
                                                  separators=(',', ': '))
                               )

    def end_game(self, won=False):
        """Ends the game - if won is True, the player won. - if won is False,
        the player lost."""
        self.game_over = True
        self.put()
        # Add the game to the score 'board'
        score = Score(user=self.user, date=date.today(),
                      won=won,
                      points=self.strikes_remaining)
        score.put()


class Score(ndb.Model):
    """Score object"""
    user = ndb.KeyProperty(required=True, kind='User')
    date = ndb.DateProperty(required=True)
    won = ndb.BooleanProperty(required=True)
    points = ndb.IntegerProperty(required=True)

    def to_form(self):
        return ScoreForm(user_name=self.user.get().name, won=self.won,
                         date=str(self.date), points=self.points)


class GameForm(messages.Message):
    """GameForm for outbound game state information"""
    urlsafe_key = messages.StringField(1, required=True)
    strikes_remaining = messages.IntegerField(2, required=True)
    shown_string = messages.StringField(3, required=True)
    guessed_letters = messages.StringField(4, required=True)
    game_over = messages.BooleanField(5, required=True)
    message = messages.StringField(6, required=True)
    user_name = messages.StringField(7, required=True)


class GameForms(messages.Message):
    """Return multiple GameForms"""
    items = messages.MessageField(GameForm, 1, repeated=True)


class NewGameForm(messages.Message):
    """Used to create a new game"""
    user_name = messages.StringField(1, required=True)


class MakeMoveForm(messages.Message):
    """Used to make a move in an existing game"""
    guess = messages.StringField(1, required=True)


class ScoreForm(messages.Message):
    """ScoreForm for outbound Score information"""
    user_name = messages.StringField(1, required=True)
    date = messages.StringField(2, required=True)
    won = messages.BooleanField(3, required=True)
    points = messages.IntegerField(4, required=True)


class ScoreForms(messages.Message):
    """Return multiple ScoreForms"""
    items = messages.MessageField(ScoreForm, 1, repeated=True)


class StringMessage(messages.Message):
    """StringMessage-- outbound (single) string message"""
    message = messages.StringField(1, required=True)


class UserForm(messages.Message):
    """UserForm for outbound User information"""
    name = messages.StringField(1, required=True)
    games_played = messages.IntegerField(2, required=True)
    career_points = messages.IntegerField(3, required=True)
    performance = messages.FloatField(4, required=True)


class UserForms(messages.Message):
    """Return multiple UserForms"""
    items = messages.MessageField(UserForm, 1, repeated=True)


class GameHistoryForm(messages.Message):
    """GameHistoryForm for outound Game History information"""
    urlsafe_key = messages.StringField(1, required=True)
    game_over = messages.BooleanField(2, required=True)
    user_name = messages.StringField(3, required=True)
    history = messages.StringField(4, required=True)
