# 2022 Hendra Manudinata <saya@hendra-manudinata.my.id>

import json
import re
from bs4 import BeautifulSoup
from flask import Flask, jsonify
import requests
from urllib.parse import urlparse

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False # Disable JSON sorting

GOMUNIME_URL = "https://185.231.223.76"

@app.route("/", methods=["GET"])
def home():
    accessHome = requests.get(GOMUNIME_URL)
    parseHome = BeautifulSoup(accessHome.text, "html.parser")
    animeList = parseHome.find_all("ul", {"class": "anime-list"}) # 0: latest, 1: new

    # Latest anime
    latestAnime = []
    for list in animeList[0].find_all("li", {"class": "episode"}):
        anchorList = list.find_all("a")
        latestAnimeDict = {
            "title": anchorList[1].text,
            "cover": anchorList[0].find("img")["data-lazy-src"],
            "url": anchorList[0]["href"]
        }
        latestAnime.append(latestAnimeDict)

    # New anime
    newAnime = []
    for list in animeList[1].find_all("li"):
        anchorList = list.find_all("a")
        newAnimeDict = {
            "title": anchorList[1].text,
            "cover": anchorList[0].find("img")["data-lazy-src"],
            "url": anchorList[0]["href"]
        }
        newAnime.append(newAnimeDict)

    return jsonify({
        "latest_anime": latestAnime,
        "new_anime": newAnime
    })

@app.route("/search/<query>/", methods=["GET"])
def search(query):
    accessSearch = requests.get(GOMUNIME_URL + f"/?s={query}")
    parseSearch = BeautifulSoup(accessSearch.text, "html.parser")
    searchList = parseSearch.find("ul", {"class": "anime-list"})

    # Search
    searchResult = []
    for list in searchList.find_all("li"):
        anchorList = list.find_all("a")
        searchResultDict = {
            "title": anchorList[1].text,
            "cover": anchorList[0].find("img")["src"],
            "url": anchorList[0]["href"],
            # "page_name": os.path.basename(urlparse(anchorList[0]["href"]).path)
            "page_name": urlparse(anchorList[0]["href"]).path
        }
        searchResult.append(searchResultDict)

    return jsonify({
        "search_query": query,
        "result": searchResult
    })

@app.route("/anime/<page_url>/", methods=["GET"])
def parseAnime(page_url):
    accessSearch = requests.get(GOMUNIME_URL + f"/anime/{page_url}")
    parseSearch = BeautifulSoup(accessSearch.text, "html.parser")
    asideElement = parseSearch.find("aside", {"class": "main"})

    # Anime info
    animeInfo = {
        "title": asideElement.find("h1", {"class": "entry-title"}).text,
        "cover": asideElement.find("div", {"class": "thumbposter"}).find("img")["data-lazy-src"],
        "sinopsis": asideElement.find("div", {"class": "entry-content"}).find("p").text,
    }

    # Episode list
    regex = re.compile(f'var\s+episodelist\s+=\s+(.*);')
    episodeListJSON = regex.search(asideElement.find("div", {"class": "bixbox bxcl epcheck"}).find("script").text).group(1)
    episodeListJSON = json.loads(episodeListJSON)

    episodeList = []
    for list in episodeListJSON:
        episodeList.append({
            "episode-number": list["ep-num"],
            "episode-title": list["ep-title"],
            "episode-date": list["ep-date"],
            "episode-link": list["ep-link"],
            "episode-pagename": "/episode" + urlparse(list["ep-link"]).path
        })

    return jsonify({
        "anime_info": animeInfo,
        "episode-list": episodeList
    })

@app.route("/episode/<episode_page>/", methods=["GET"])
def episodePage(episode_page):
    accessEpisode = requests.get(GOMUNIME_URL + f"/{episode_page}")
    parseEpisode = BeautifulSoup(accessEpisode.text, "html.parser")
    asideElement = parseEpisode.find("aside", {"class": "main"})

    animeInfo = {
        "title": asideElement.find("h1", {"class": "title entry-title"}).text.replace("Nonton ", ""),
        "uploaded_on": asideElement.find("span", {"class": "updated"}).text
    }

    # Mirror and download list gathering
    vapiAlias = {
        "data": "a_ray",
        "gambar": "image_data",
        "judul": "judul_postingan",
    }
    vapiParams = {}
    for item in vapiAlias.items():
        p = re.compile(f'var\s+{item[1]}\s+=\s+(.*);')
        for script in parseEpisode.find_all("script", {"src":False}):
            m = p.search(script.text)
            if m != None:
                vapiParams[item[0]] = m.group(1).replace("'", "").replace('"', "")

    vapiParams["func"] = "mirror"
    embedListHTML = requests.post("https://path.onicdn.xyz/app/vapi.php", data=vapiParams)
    parsedEmbedListHTML = BeautifulSoup(embedListHTML.text, "html.parser")
    anchorListEmbed = parsedEmbedListHTML.find_all("div", {"data-vhash": re.compile(r".*")})
    specialEmbedLink = ""
    embedList = []
    for anchor in anchorListEmbed:
        if anchor["data-vhash"].startswith("https://"): # Normal embed link
            embedList.append(anchor["data-vhash"])
        else: # Hash token embed link, needs to be appended to vapi link
            p = re.compile('var\s+fhash\s+=\s+(.*);')
            for script in parseEpisode.find_all("script", {"src":False}):
                m = p.search(script.text)
                if m != None:
                    specialEmbedLink = m.group(1).replace("'", "").replace('"', "").strip()
                    if f"https://gugcloud.club/vapi.php?id={specialEmbedLink}" not in embedList:
                        embedList.append(f"https://gugcloud.club/vapi.php?id={specialEmbedLink}")

    vapiParams["func"] = "ddl"
    downloadListHTML = requests.post("https://path.onicdn.xyz/app/vapi.php", data=vapiParams)
    parsedDownloadListHTML = BeautifulSoup(downloadListHTML.text, "html.parser")
    anchorListDownload = parsedDownloadListHTML.find_all("a")
    downloadList = []
    for anchor in anchorListDownload:
        downloadList.append(anchor["href"])

    return jsonify({
        "anime_info": animeInfo,
        "embed_list": embedList,
        "embed_token": specialEmbedLink,
        "download_list": downloadList
    })

if __name__ == "__main__":
    app.run(port=2704, threaded=True)
