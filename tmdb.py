import requests
import json
import os
from requests.exceptions import ConnectionError

# you'll need to have an API key for TMDB
# to run these examples,
# run export TMDB_API_KEY=<YourAPIKey>
tmdb_api_key = os.environ["TMDB_API_KEY"]
# Setup tmdb as its own session, caching requests
# (we only want to cache tmdb, not elasticsearch)
# Get your TMDB API key from
#  https://www.themoviedb.org/documentation/api
# then in shell do export TMDB_API_KEY=<Your Key>
tmdb_api = requests.Session()
tmdb_api.params={'api_key': tmdb_api_key}

def movieList(linksFile='ml-latest/links.csv'):
    import csv
    rdr = csv.reader(open(linksFile))
    tmdbIds = {}
    numMissing = 0
    for rowNo, row in enumerate(rdr):
        if rowNo == 0:
            continue
        try:
            tmdbIds[row[0]] = int(row[2])
        except ValueError:
            numMissing += 1
            print("No TMDB ID at %s, imdb is: %s, missing %s/%s" % (row[0], row[1], numMissing, rowNo))
    print("Pulling %s TMDB movies from %s" % (len(tmdbIds),linksFile))
    return tmdbIds

def getCastAndCrew(movieId, movie):
    httpResp = tmdb_api.get("https://api.themoviedb.org/3/movie/%s/credits" % movieId, verify=False)
    credits = json.loads(httpResp.text) #C
    try:
        crew = credits['crew']
        directors = []
        for crewMember in crew: #D
            if crewMember['job'] == 'Director':
                directors.append(crewMember)
        movie['cast'] = credits['cast'] #E
        movie['directors'] = directors
    except KeyError as e:
        print(e)
        print(credits)

def extract(movieIds=[]):
    localMovies = json.load(open('tmdb57k.json'))
    print("CACHED: %s MOVIES" % len(localMovies))
    for idx, (mlensId, tmdbId) in enumerate(movieIds.items()):
        try:
            print("On %s / %s movies" % (idx, len(movieIds)))
            movie = None
            if str(tmdbId) in localMovies:
                movie = localMovies[str(tmdbId)]
                #print("Cache %s" % tmdbId)

            if movie is None:
                print("Fetch %s" % tmdbId)
                httpResp = tmdb_api.get("https://api.themoviedb.org/3/movie/%s"
                                        % tmdbId, verify=False)
                if 'x-ratelimit-remaining' not in httpResp.headers:
                    print(httpResp)
                elif int(httpResp.headers['x-ratelimit-remaining']) < 10:
                    print("Rate limited, sleeping")
                    with open('tmdb.json', 'w') as f:
                        print("DUMPED!")
                        json.dump(localMovies, f)
                movie = json.loads(httpResp.text)
                getCastAndCrew(tmdbId, movie)

            movie['mlensId'] = mlensId
            movie['tmdbId'] = tmdbId
            localMovies[str(tmdbId)] = movie
            yield movie
            # movieDict[tmdbId] = movie
        except ConnectionError as e:
            print(e)

    with open('tmdb.json', 'w') as f:
        print("DUMPED - DONE!!")

    return movieDict



if __name__ == "__main__":
    movieIds = movieList()
    movieDict = extract(movieIds)
    f = open('tmdb.json', 'w')
    f.write(json.dumps(movieDict))
