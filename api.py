# -*- coding: utf-8 -*-`
"""api.py - Create and configure the Game API exposing the resources.
This can also contain game logic. For more complex games it would be wise to
move game logic to another file. Ideally the API will be simple, concerned
primarily with communication to/from the API's users."""

import logging
import endpoints
from protorpc import remote, messages
from google.appengine.api import memcache
from google.appengine.api import taskqueue

from models import (
    User, Game, Score,
    NewGameForm, GameForm, GameForms, GameHistoryForm,
    MakeMoveForm, ScoreForms, UserForms,
    StringMessage
)
from utils import get_by_urlsafe

NEW_GAME_REQUEST = endpoints.ResourceContainer(NewGameForm)
GET_GAME_REQUEST = endpoints.ResourceContainer(
    urlsafe_game_key=messages.StringField(1),)
MAKE_MOVE_REQUEST = endpoints.ResourceContainer(
    MakeMoveForm,
    urlsafe_game_key=messages.StringField(1),)
USER_REQUEST = endpoints.ResourceContainer(user_name=messages.StringField(1),
                                           email=messages.StringField(2))
NUMBER_RESULTS_REQUEST = endpoints.ResourceContainer(
    num_results=messages.IntegerField(1),)

MEMCACHE_STRIKES_REMAINING = 'STRIKES_REMAINING'


@endpoints.api(name='hangman', version='v1')
class HangmanApi(remote.Service):
    """Game API"""
    @endpoints.method(request_message=USER_REQUEST,
                      response_message=StringMessage,
                      path='user',
                      name='create_user',
                      http_method='POST')
    def create_user(self, request):
        """Create a User. Requires a unique username"""
        if User.query(User.name == request.user_name).get():
            raise endpoints.ConflictException(
                'A User with that name already exists!')
        user = User(name=request.user_name, email=request.email)
        user.put()
        return StringMessage(message='User {} created!'.format(
            request.user_name))

    @endpoints.method(request_message=NEW_GAME_REQUEST,
                      response_message=GameForm,
                      path='game',
                      name='new_game',
                      http_method='POST')
    def new_game(self, request):
        """Creates new game"""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                'A User with that name does not exist!')
        game = Game.new_game(user.key)
        game.put()
        # Use a task queue to update the average strikes remaining.
        # This operation is not needed to complete the creation of a new game
        # so it is performed out of sequence.
        taskqueue.add(url='/tasks/cache_average_strikes')
        return game.to_form('Good luck playing Hangman!')

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='get_game',
                      http_method='GET')
    def get_game(self, request):
        """Return the current game state."""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game:
            if game.game_over:
                return game.to_form('This game is over!')
            return game.to_form('Time to guess a letter!')
        else:
            raise endpoints.NotFoundException('Game not found!')

    @endpoints.method(request_message=MAKE_MOVE_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='make_move',
                      http_method='PUT')
    def make_move(self, request):
        """Makes a move. Returns a game state with message"""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        theUser = User.query(User.key == game.user).get()
        # Test if the game is already over.
        if game.game_over:
            raise endpoints.ForbiddenException('Illegal action: '
                                               'Game is already over.')

        if len(request.guess) > 1 or request.guess.isalpha() is False:
            return game.to_form('Your guess must be a single English letter!')

        if request.guess in game.guessed_letters:
            return game.to_form('You have already guessed this letter')

        if request.guess in game.target_string:
            game.guessed_letters += request.guess
            game.correct_letters += request.guess
            msg = "The letter IS in the secret word!"
            game.history.append(
                {"guess": request.guess, "message": msg,
                 "strikes": game.strikes_remaining})
        else:
            game.strikes_remaining -= 1
            game.guessed_letters += request.guess
            msg = "The letter IS NOT in the secret word!"
            game.history.append(
                {"guess": request.guess, "message": msg,
                 "strikes": game.strikes_remaining})

        for i in range(len(game.target_string)):
            if game.target_string[i] in game.correct_letters:
                game.shown_string = game.shown_string[
                    :i] + game.target_string[i] + game.shown_string[i + 1:]

        if game.shown_string == game.target_string:
            game.end_game(True)
            theUser.games_played += 1
            theUser.career_points += game.strikes_remaining
            # theUser.performance is updated upon theUser.put()
            theUser.put()
            return game.to_form('You win! ')

        if game.strikes_remaining < 1:
            game.end_game(False)
            theUser.games_played += 1
            theUser.career_points += game.strikes_remaining
            # theUser.performance is updated upon theUser.put()
            theUser.put()
            return game.to_form(msg + ' Game over!')
        else:
            game.put()
            return game.to_form(msg)

    @endpoints.method(response_message=ScoreForms,
                      path='scores',
                      name='get_scores',
                      http_method='GET')
    def get_scores(self, request):
        """Return all scores"""
        return ScoreForms(items=[score.to_form() for score in Score.query()])

    @endpoints.method(request_message=USER_REQUEST,
                      response_message=ScoreForms,
                      path='scores/user/{user_name}',
                      name='get_user_scores',
                      http_method='GET')
    def get_user_scores(self, request):
        """Returns all of an individual User's scores"""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                'A User with that name does not exist!')
        scores = Score.query(Score.user == user.key)
        return ScoreForms(items=[score.to_form() for score in scores])

    @endpoints.method(response_message=StringMessage,
                      path='games/average_strikes',
                      name='get_average_strikes_remaining',
                      http_method='GET')
    def get_average_strikes(self, request):
        """Get the cached average moves remaining"""
        return StringMessage(message=memcache.
                             get(MEMCACHE_STRIKES_REMAINING) or '')

    @staticmethod
    def _cache_average_strikes():
        """Populates memcache with the average moves remaining of Games"""
        logging.info('Going to cache the average strikes')
        games = Game.query(Game.game_over == False).fetch()
        # this isn't working if I do (not Game.game_over) it is frustrating.
        logging.info('I made it this far')
        if games:
            logging.info('This is the len of games: ' + str(len(games)))
            count = len(games)
            total_strikes_remaining = sum([game.strikes_remaining
                                           for game in games])
            average = float(total_strikes_remaining) / count
            memcache.set(MEMCACHE_STRIKES_REMAINING,
                         'The average strikes remaining is {:.2f}'.
                         format(average))

    @endpoints.method(request_message=USER_REQUEST,
                      response_message=GameForms,
                      path='games/user/{user_name}',
                      name='get_user_games',
                      http_method='GET')
    def get_user_games(self, request):
        """Returns all of an individual User's active games"""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                'A User with that name does not exist!')
        games = Game.query(Game.user == user.key).\
            filter(Game.game_over == False)
        # I really don't understand why anaconda says I have to put
        # the 'filter' this far back.. Also forced to do == False
        return GameForms(items=[game.to_form("") for game in games])

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=GameForm,
                      path='game/cancel/{urlsafe_game_key}',
                      name='cancel_game',
                      http_method='PUT')
    def cancel_game(self, request):
        """ends the game prematurely - no points given. Game = Over """
        # it's my belief that if you need to cancel your game, you need
        # to take a loss, otherwise players will simply delete / cancel
        # games when performing poorly, so it does not affect their ranking.
        # That's letting the ragequitters win, and ragequitters never deserve
        # to win.
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if not game.game_over:
            game.strikes_remaining = 0
            game.end_game(False)
            return game.to_form('Game canceled prematurely - Game over!')
        raise endpoints.ForbiddenException('Game already over! Cannot cancel!')

    @endpoints.method(request_message=NUMBER_RESULTS_REQUEST,
                      response_message=ScoreForms,
                      path='get_scores/high',
                      name='get_high_scores',
                      http_method='GET')
    def get_high_scores(self, request):
        """generates a list of game high scores in descending order; a leader-board.
           accepts optional parameter 'num_results' which limits the number of
           returned results. Doesn't work well with Hangman since a perfect
           game is not uncommon."""
        qu = Score.query().\
            order(-Score.points).\
            order(Score.date)
        if request.num_results:
            return ScoreForms(items=[score.to_form() for score in qu.
                                     fetch(limit=request.num_results)])
        return ScoreForms(items=[score.to_form() for score in qu])

    @endpoints.method(request_message=NUMBER_RESULTS_REQUEST,
                      response_message=UserForms,
                      path='userranks',
                      name='get_user_rankings',
                      http_method='GET')
    def get_user_rankings(self, request):
        """generates ranked list (leaderboard) of users based on user performance,
        then by career points, then by fewest games played"""
        qu = User.query().\
            order(-User.performance).\
            order(-User.career_points).\
            order(User.games_played)
        if not qu:
            raise endpoints.NotFoundException('There are no rankings!')
        if request.num_results:
            return UserForms(items=[user.to_form() for user in qu.
                                    fetch(limit=request.num_results)])
        return UserForms(items=[user.to_form() for user in qu])

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=GameHistoryForm,
                      path='history/{urlsafe_game_key}',
                      name='get_game_history',
                      http_method='GET')
    def get_game_history(self, request):
        """returns the move history of a given game as JSON"""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        return game.history_to_form()

api = endpoints.api_server([HangmanApi])
