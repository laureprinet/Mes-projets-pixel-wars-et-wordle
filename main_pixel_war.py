from fastapi import FastAPI
from uuid import uuid4
from fastapi .responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Query, Cookie
from time import time

app=FastAPI()

app.add_middleware(CORSMiddleware,
    allow_origins=["*","http://localhost:8000"],
    allow_credentials=True)


################# Classe Utilisateur et Carte ###################
class Utilisateur:
    def __init__(self, user_id:str, nx: int, ny : int):
        self.id=user_id
        self.last_seen_map=[[(0,0,0) for j in range(ny)] for i in range(nx)]
        self.last_paint_time=0


class Carte:
    keys: set[str]
    nx:int 
    ny:int
    user_ids : set[str]
    user_infos : dict[str:list[list[tuple[int,int,int]]], float]
    data:list[list[tuple[int,int,int]]]

    def __init__(self,nx:int,ny:int,timeout_nanos:int = 100000000):
        self.keys=set()
        self.nx=nx
        self.ny=ny
        self.user_ids=set()
        self.user_infos={}
        self.data=[[(0,0,0) for _ in range (ny)]]
        self.timeout_nanos=timeout_nanos
        

    def create_new_key(self):
        key=str(uuid4())
        self.keys.add(key)
        return key
    
    def is_valid_key(self,key:str):
        return key in self.keys
    
    def create_new_user_id(self):
        user_id=str(uuid4())
        self.user_ids.add(user_id) 
        user=Utilisateur(user_id, self.nx, self.ny)
        self.user_infos[user_id]=[user.last_seen_map,user.last_paint_time]
        return user_id
    
    def is_valid_user_id(self,user_id):
        return user_id in self.user_ids
    

################# Fonctionnement du Pixel Wars #####################

cartes : dict[str, Carte] = {
    "Test": Carte(nx=10, ny=10,timeout_nanos=1000000000000)
}


@app.get("/")
async def root():
    return {"Bienvenue": "Projet Pixel Wars"}


@app.get("/api/v1/{nom_carte}/preinit")
async def preinit(nom_carte:str):
    carte=cartes[nom_carte]
    if not carte :
        return {"error": "Je n'ai pas trouvé la carte"}

    key=str(uuid4())
    res=JSONResponse({"key" : key})
    res.set_cookie("key",key, httponly=True, samesite='None', max_age=3600)
    return res
#Pour que ce soit complet faut rajouter un cookie


@app.get("/api/v1/{nom_carte}/init")
async def init(nom_carte:str, query_key: str = Query(alias='key'), cookie_key: str = Cookie(alias="key")):
    carte=cartes[nom_carte]
    if not carte:
        return {"error": "Je n'ai pas trouvé la carte"}
    if query_key!=cookie_key:
        return {"error": "Les clés ne correspondent pas"}
    if not carte.is_valid_key(cookie_key):
        return {"error": "La clé n'est pas valide"}
        
    user_id=carte.create_new_user_id()
    res=JSONResponse({"id": user_id, "nx":carte.nx, "ny":carte.ny, "data": carte.data})
    res.set_cookie("id", user_id, secure=True, samesite="None", max_age=3600)
    return res

@app.get("/api/v1/{nom_carte}/deltas")
async def deltas (nom_carte:str,query_user_id: str = Query(alias="id"),
            cookie_key: str = Cookie(alias="key"),
            cookie_user_id: str = Cookie(alias="id")):
            
    carte = cartes[nom_carte]

    if not carte is None:
        return {"error": "Je n'ai pas trouvé la carte"}     
    
    if not carte.is_valid_key(cookie_key):
        return {"error": "La clé n'est pas valide"}
    
    if query_user_id != cookie_user_id:
        return {"error": "Les clés ne correspondent pas"}
    
    if not carte.is_valid_user_id(cookie_user_id):
        return {"error": "La clé utilisateur n'est pas valide."}
    
    user_info = carte.user_infos[query_user_id]
    user_carte, user_last_paint_time = user_info[0],user_info[1]

    # Différence entre la carte et celle qu'a l'utilisateur
    deltas : list[tuple[int, int, int, int, int]] = []
    for y in range(carte.ny):
        for x in range(carte.nx):
            if carte.data[x][y] != user_carte[x][y]:
                deltas.append((y, x, *carte.data[x][y]))
    return {
        "id": query_user_id,
        "nx": carte.nx,
        "ny": carte.ny,
        "deltas": deltas}

@app.post("/api/v1/{nom_carte}/colour")
async def colour_pixel(nom_carte: str,
                      data_request: list[tuple[int, int],tuple[int,int,int]], #sous la forme : [(x,y),(r,g,b)]
                      cookie_key: str = Cookie(alias="key"),
                      cookie_user_id: str = Cookie(alias="id")):
    carte = cartes[nom_carte]

    if not carte:
        return {"error": "Je n'ai pas trouvé la carte"}
    
    if not carte.is_valid_user_id(cookie_user_id):
        return {"error": "Les clés ne correspondent pas"}
    
    if not carte.is_valid_key(cookie_key):
        return {"error": "La clé n'est pas valide"}
    
    # Coordonnées
    x, y = data_request[0][0], data_request[0][1]
    if not (0 <= x < carte.nx and 0 <= y < carte.ny):
        return {"error": "Les coordonnées ne sont pas valides"}

    # Lapse de temps entre chaque coloration (ici : 1 seconde)
    user_info = carte.user_infos[cookie_user_id]
    user_last_paint_time = user_info[1]
    current_time=time.time()

    if current_time - user_last_paint_time < 1:  # cooldown de 1 seconde
        return {"error": "Veuillez patienter avant de pouvoir colorier à nouveau"}

    # Coloriage
    couleurs=data_request[1]
    carte.data[x][y] = (couleurs[0], couleurs[1], couleurs[2])
    carte.user_infos[cookie_user_id][1] = current_time  # mise à jour du temps du dernier coloriagr

    return {
        "message": "Pixel modifié.",
        "x": x,
        "y": y,
        "color": carte.data[x][y]
    }