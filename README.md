#Full Stack Nanodegree Project 4 Refresh

## Set-Up Instructions:
1.  Update the value of application in app.yaml to a Google app ID you have registered
 in the Google AppEngine admin console which you would like to use to host your instance of this game.
2.  Run the app with the devserver using dev_appserver.py DIR, and ensure it's
 running by visiting the API Explorer - by default localhost:8080/_ah/api/explorer.
3.  (Optional) Generate your client library(ies) with the endpoints tool.
 Deploy your application.
 
##Game Description:
Hangman is a single player guessing game. The user is given a target word to eventually guess. The player is given a
hidden string which shows the number of characters in the target word. On a round, the player is only allowed to guess 
one English letter. If the letter is in the target word, it will show all instances of that letter in the hidden string, which
can help guide the player in guessing the rest of the word in later rounds. If a player guesses a letter which is not in the target word
they will receive a strike. There are 6 strikes in a traditional game (drawing the head, body, right arm, left arm, right leg, left leg onto
a rope hanging from gallows). The game is over when the player uncovers the target word, or runs out of strikes. 

The 'Score' of a game is simply the remaining number of strikes. A player's performance is equal to their 'career points' (total points over every game played) divided by their total number of games played.

'Guesses' are sent to the `make_move` endpoint which will reply whether the letter is in the target word or not.
Many different Hangman games can be played by many different Users at any given time. Each game can be retrieved or played by using the path parameter
`urlsafe_game_key`.

##Quick Playguide:
Create a new user with the `create_user` endpoint. Give a name and e-mail (optional). Use the name you gave this user in the `new_game` endpoint. The `new_game` endpoint will give you a urlsafe game key, and a hidden string representing the target word. Copy the game key, as you will use it to make guesses. 

Use game key in the `make_move` endpoint to guess a single english letter. If your letter is found in the target string, you will receive no strikes, and the letter will be visible on the hidden string. If you guess a letter not in the target string, you will receive a strike. Once the game is over, the game_over property will be true, and the user's performance will be updated.

The game can be canceled prematurely with the `cancel_game` endpoint, though keep in mind this will negatively affect a user's performance. If you want to see the history of moves made and the responses given, call the `get_game_history` method.

##Files Included:
 - api.py: Contains endpoints and game playing logic.
 - app.yaml: App configuration.
 - cron.yaml: Cronjob configuration (configuring when to perform specific tasks and in what intervals).
 - main.py: Handler for taskqueue handler (in this project, configuring a mass e-mail sent to all players with unfinished games)
 - models.py: Entity and message definitions including helper methods.
 - utils.py: Helper function for retrieving ndb.Models by urlsafe Key string.
 - wordlist.txt: List of words used for the game.

##Endpoints Included:
 - **create_user**
    - Path: 'user'
    - Method: POST
    - Parameters: user_name, email (optional)
    - Returns: Message confirming creation of the User.
    - Description: Creates a new User. user_name provided must be unique. Will 
    raise a ConflictException if a User with that user_name already exists.
    
 - **new_game**
    - Path: 'game'
    - Method: POST
    - Parameters: user_name
    - Returns: GameForm with initial game state.
    - Description: Creates a new Game, and gives you a urlsafe game key to use when making guesses in the game. user_name provided must correspond to an
    existing user - will raise a NotFoundException if not. Also adds a task to a 
	task queue to update the average moves remaining for active games.
     
 - **get_game**
    - Path: 'game/{urlsafe_game_key}'
    - Method: GET
    - Parameters: urlsafe_game_key
    - Returns: GameForm with current game state.
    - Description: Returns the current state of a game.
    
 - **make_move**
    - Path: 'game/{urlsafe_game_key}'
    - Method: PUT
    - Parameters: urlsafe_game_key, guess
    - Returns: GameForm with new game state.
    - Description: Accepts a 'guess' and returns the updated state of the game.
    If this causes a game to end, a corresponding Score entity will be created.
    
 - **get_scores**
    - Path: 'scores'
    - Method: GET
    - Parameters: None
    - Returns: ScoreForms.
    - Description: Returns all Scores in the database (unordered).
    
 - **get_user_scores**
    - Path: 'scores/user/{user_name}'
    - Method: GET
    - Parameters: user_name
    - Returns: ScoreForms. 
    - Description: Returns all Scores recorded by the provided player (unordered).
    Will raise a NotFoundException if the User does not exist.
    
 - **get_average_strikes**
    - Path: 'games/average_strikes'
    - Method: GET
	- Parameters: (none)
	- Returns: StringMessage
    - Description: Get the cached average moves remaining.

 - **get_user_games**
    - Path: 'games/user/{user_name}',
    - Method: GET
    - Parameters: user_name, email (optional)
    - Returns: GameForms for user_name
    - Description: Returns all of an individual User's games.
    Will raise NotFoundException if the User does not exist

 - **cancel_game**
    - Path: 'game/cancel/{urlsafe_game_key}'
    - Method: PUT
    - Parameters: urlsafe_game_key
    - Returns: GameForm with update canceling the game
    - Description: ends the game prematurely - no points given. Game = Over.
    it's my belief that if you need to cancel your game, you need to take a loss.
    otherwise players will simply delete / cancel games when performing poorly, so it does not affect
    their ranking. That's letting the ragequitters win, and ragequitters never deserve to win.

 - **get_high_scores**
    - Path: 'get_scores/high'
    - Method: GET
    - Parameters: Max number of results (optional)
    - Returns: ScoreForms (all games, sorted by highest score, limited by max number of results)
    - Description: Generates a list of game high scores in descending order; a leader-board.
    accepts optional parameter 'num_results' which limits the number of returned
    results. Doesn't work well with Hangman since a perfect game is not uncommon.

 - **get_user_rankings**
    - Path: 'userranks'
    - Method: GET
    - Parameters: Max number of results (optional)
    - Returns: UserForms (all users, sorted by performance, limited by max number of results)
    - Description: generates ranked list (leaderboard) of users based on user performance, then by career points,
    then by fewest games played

 - **get_game_history**
    - Path: 'history/{urlsafe_game_key}'
    - Method: GET
    - Parameters: urlsafe_game_key
    - Returns: GameHistoryForm
    - Description: returns the move history of a given game as JSON, as well as whether the game is over, and the user playing.

##Models Included:
 - **User**
    - Stores unique user_name and (optional) email address.
    
 - **Game**
    - Stores unique game states. Associated with User model via KeyProperty.
    
 - **Score**
    - Records completed games. Associated with User model via KeyProperty.
    
##Forms Included:
 - **GameForm**
    - Representation of a Game's state (urlsafe_key, strikes_remaining,
    shown_string, guessed_letters, game_over flag, message, user_name).
 - **GameForms**
   - Multiple GameForm container.
 - **NewGameForm**
    - Used to create a new game (user_name)
 - **MakeMoveForm**
    - Inbound make move form (guess).
 - **ScoreForm**
    - Representation of a completed game's Score (user_name, date, won flag,
    points).
 - **ScoreForms**
    - Multiple ScoreForm container.
 - **StringMessage**
    - General purpose String container.
 - **UserForm**
    - Representation of a User's information and performance (games_played,
	career_points, performance)
 - **UserForms**
    - Multiple UserForm container.
 - **GameHistoryForm**
    - Container holding the historical guesses and responses made for a game as JSON