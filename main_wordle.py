from fastapi import FastAPI, Cookie, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from uuid import uuid4
import random

app = FastAPI()

app.add_middleware(CORSMiddleware,
    allow_origins=["*","http://localhost:8000"],
    allow_credentials=True)


class WordleGame:
    def __init__(self, word :str):
        self.word = word
        self.user_data = {}  # user_id:list des essais
        self.length = len(self.word)

    def create_user(self):
        user_id = str(uuid4())
        self.user_data[user_id] = []
        return user_id

    def is_valid_user(self, user_id : str):
        return user_id in self.user_data

    def make_guess(self, user_id:str, guess:str):
        guess = guess.upper()
        if len(guess) != self.length or not guess.isalpha():
            return {"error": "Mot invalide"}

        #Initialisation des variables
        feedback = []
        target = list(self.word)
        guess_letters = list(guess)
        used = [False] * self.length

        # Si une lettre est correcte et bien lacée
        for i in range(self.length):
            if guess_letters[i] == target[i]:
                feedback.append("Correct")
                used[i] = True
            else:
                feedback.append(None)

        # Si elle est correcte mais male placée
        for i in range(self.length):

            if feedback[i] is None:

                # On vérifie que la lettre est bien dans le mot et qu'elle n'apparaît pas en surnombre dans guess
                if guess_letters[i] in target and target.count(guess_letters[i]) > sum(guess_letters[j] == guess_letters[i] and feedback[j] == "Correct" for j in range(self.length)):
                    feedback[i] = "Mal placée"

                else:
                    feedback[i] = "Incorrect"

        self.user_data[user_id].append((guess, feedback))
        return {"guess": guess, "feedback": feedback}

    def get_status(self, user_id):
        if not self.is_valid_user(user_id):
            return {"error": "Utilisateur invalide"}
        return {
            "attempts": self.user_data[user_id],
            "finished": any("Correct" * self.length == "".join(fb) for _, fb in self.user_data[user_id]),
        }


mots=["informatique", "mathématiques", "mines", "internet", "énergies", "écologie", "jancovici", "thermodynamique"]
mot=random.choice(mots)
game = WordleGame(mot)

@app.get("/api/v1/wordle/preinit")
async def preinit():
    key = str(uuid4())
    res = JSONResponse({"key": key})
    res.set_cookie("key", key, httponly=True, samesite="Lax", max_age=3600)
    return res

@app.get("/api/v1/wordle/init")
async def init(query_key: str = Query(alias="key"), cookie_key: str = Cookie(alias="key")):
    if query_key != cookie_key:
        return {"error": "Clés non correspondantes"}
    user_id = game.create_user()
    res = JSONResponse({"id": user_id})
    res.set_cookie("id", user_id, httponly=True, samesite="None", max_age=3600)
    return res

@app.get("/api/v1/wordle/guess")
async def guess(guess: str,user_id: str = Query(alias="id"),cookie_id: str = Cookie(alias="id")):
    if user_id != cookie_id:
        return {"error": "Utilisateur invalide"}

    if not game.is_valid_user(user_id):
        return {"error": "Utilisateur inconnu"}

    return game.make_guess(user_id, guess)

@app.get("/api/v1/wordle/status")
async def status(user_id: str = Query(alias="id"),cookie_id: str = Cookie(alias="id")):
    if user_id != cookie_id:
        return {"error": "Utilisateur invalide"}
    return game.get_status(user_id)
