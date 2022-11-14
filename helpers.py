import os
import requests
import urllib.parse

from flask import redirect, render_template, request, session
from functools import wraps


def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

#export API_KEY=61fa968ea1f32237a597a9cd500d9eea
#fetch list of movies based on keyword https://api.themoviedb.org/3/search/movie/?api_key={api_key}&query={title}
#fetch more details about a movie https://api.themoviedb.org/3/search/movie/{movie-id}?api_key={api_key}
#fetch list of shows based on keyword https://api.themoviedb.org/3/search/tv?api_key=%7Bapi_key%7D&page=1&query=KEYWORD
#fetch list of people based on keyword https://api.themoviedb.org/3/search/person?api_key=61fa968ea1f32237a597a9cd500d9eea&query=KEYWORD&page=1
#secure image url https://image.tmdb.org/t/p/
#config configuration?api_key=<apikey>
#multisearch (movies,shows,ppl) https://api.themoviedb.org/3/search/multi?api_key=61fa968ea1f32237a597a9cd500d9eea&query={keyword}&page=1

baseURL = "https://api.themoviedb.org/3/"

def get_all():
    """return list of trending films/tv shows"""
    try:
        api_key = os.environ.get("API_KEY")
        response = requests.get(baseURL+f"trending/all/day?api_key={api_key}")
        response.raise_for_status()
        response2 = requests.get(baseURL+f"movie/upcoming?api_key={api_key}")
        response2.raise_for_status()
        response3 = requests.get(baseURL+f"tv/top_rated?api_key={api_key}")
        response3.raise_for_status()
    except requests.RequestException:
        return None

    search = response.json()["results"]
    trend = []
    for i in search:
        trend.append("https://image.tmdb.org/t/p/w300/"+i["poster_path"])

    search2 = response2.json()["results"]
    upcoming = []
    for j in search2:
        upcoming.append({"image": "https://image.tmdb.org/t/p/w300/"+j["poster_path"], "date": j["release_date"]})

    search3 = response3.json()["results"]
    tvpop = []
    for k in search3:
        tvpop.append("https://image.tmdb.org/t/p/w300/"+k["poster_path"])
    results = [trend, upcoming, tvpop]
    return results



def lookup(keyword, type, num):
    """Look up keyword"""

    # Contact API
    responses = apiSearch(keyword, type)
    if responses == None:
        return None
    response = responses[0]
    response2 = responses[1]
    x = num

    # Check if no results
    count = response.json()["total_results"]
    if count == 0:
        return None

    genreDB = response2.json()["genres"] #e.g.[{"id": 10759, "name": "Action & Adventure"}, {"id": 16,"name": "Animation"}...]
    #iterate through list until each one has been searched or valid show found
    search = response.json()["results"]

    results = []
    # for each show in the list, check if it is valid
    i = 0
    # Whilest there are still results to search through and amount found is still < num requested
    while i < count and num != 0:
        temp = search[i]
        id = temp["id"]
        rating = temp["vote_average"]
        image = temp["poster_path"]
        overview = temp["overview"]
        # Skip shows without rating/image, otherwise carry on...
        if rating != 0 and image != 'null':
            if type == "mv":
                title = temp["title"]
            else:
                title = temp["name"]
            #returns list of genres for temp (current show)
            genreList = getGenres(genreDB, temp)
            results.append({
                "id": id,
                "title": title,
                "rating": rating,
                "image": image,
                "genres": genreList,
                "overview": overview,
            })
            num -= 1
        i += 1
    return results

# try searching movies or tv by ID
def lookupId(id, type):
    try:
        api_key = os.environ.get("API_KEY")
        if type == "mv":
            response = requests.get(baseURL+f"movie/{id}?api_key={api_key}")
        elif type == "tv":
            response = requests.get(baseURL+f"tv/{id}?api_key={api_key}")
        response.raise_for_status()
    except requests.RequestException:
        return None
    response.raise_for_status()

    show = response.json()
    if type == "mv":
        title = show["title"]
        eps = 1
        runtime = show["runtime"]
    elif type == "tv":
        title = show["name"]
        eps = show["number_of_episodes"]
        runtime = show["episode_run_time"][0]
    image = show["poster_path"]

    return {
            "id": id,
            "title": title,
            "image": image,
            "eps": eps,
            "runtime": runtime
    }


#iterate through the list of genre IDs for the movie/tv show
def getGenres(genreDB, temp):
    genreIds = temp["genre_ids"] #e.g.[16, 10759, 10765, 35]
    genreList = []
    for j in range(0, len(temp["genre_ids"])):
        tempId = genreIds[j]
        k = 0
        found = 0
        while k < len(genreDB) and found == 0:
            tempDict =  genreDB[k]
            if tempDict["id"] == tempId:
                genreList.append(tempDict["name"])
                found += 1
            k += 1
    return genreList


def apiSearch(keyword, type):
    try:
        api_key = os.environ.get("API_KEY")
        if type == "mv":
            response = requests.get(baseURL+f"search/movie/?api_key={api_key}&query={keyword}")
            response2 = requests.get(baseURL+f"genre/movie/list?api_key={api_key}")
        if type == "tv":
            response = requests.get(baseURL+f"search/tv?api_key={api_key}&page=1&query={keyword}")
            response2 = requests.get(baseURL+f"genre/tv/list?api_key={api_key}")
        response.raise_for_status()
        response2.raise_for_status()
    except requests.RequestException:
        return None
    responses = [response, response2]
    return responses
