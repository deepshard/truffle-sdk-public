# The Truffle Python SDK 

This repo provides the Truffle SDK and the Truffle CLI tool. Full Truffle SDK functionality is planned to be open-sourced at a later date.
Issues associated with the SDK functionality should be filed here. Wheels should be fetched from releases.

# Creating a new app
`truffle init MyCoolApp` (omit to use current directory)

# Building a app
`truffle build ../Path/To/My/App/Root/Dir/MyCoolApp` - outputs `MyCoolApp.truffle`

# Installing your App onto your Truffle
`truffle upload MyBundledApp.truffle` - ensure client is open and connected
The progress of this will be reported in the client.



# Simple example

````python


import truffle
import traceback
from duckduckgo_search import DDGS
from typing import List 
from pytrends.request import TrendReq
import pandas as pd
import tabulate
from typing import List, Dict
import subprocess
import os 

class Trending:
    def __init__(self):
        self.metadata = truffle.AppMetadata(
            name="Trending",
            description="Finds trendy topics",
            icon="icon.png",
        )
    
    @truffle.tool("Take notes", icon="note.text.badge.plus")
    @truffle.args(note="The note to take, it will be saved for future access")
    def TakeNote(self, note: str) -> str:
        self.notepad += note + "\n"
        return "Added note.\n Current notes: \n" + str(self.notepad)
    
    @truffle.tool("Read notes", icon="note")
    @truffle.args(clear_after="Clear notes after reading, not recommended (yes/no)")
    def ReadNotes(self, clear_after: str) -> str:
        if clear_after == "yes":
            notes = self.notepad
            self.notepad = ""
            return "Current notes: \n" + str(notes)
        else:
            return "Current notes: \n" + str(self.notepad)
    
    @truffle.tool("Search the web with DuckDuckGo", icon="globe")
    @truffle.args(query="The search query", num_results="The number of results to return")
    def WebSearch(self, query: str, num_results: int) -> List[str]:
        results = DDGS().text(query, region='wt-wt', safesearch='off', timelimit='y', max_results=num_results)
        ret = []
        print(results)
        for result in results:
            sr = f"**{result['title']}** - {result['href']}"
            sr += f"\n{result['body']}"
            ret.append(sr)
        return ret

    @truffle.tool("Get North American news articles from the last week", icon="newspaper")
    @truffle.args(query="News search query", num_results="The number of news results to return")
    def SearchNewsArticles(self, query: str, num_results: int) -> List[str]:
        results = DDGS().news(query, region='us-en', safesearch='off', timelimit='w', max_results=num_results)
        ret = []
        for result in results:
            sr = f"**{result['title']}** - {result['source']} - {result['date']}"
            sr += f"\n{result['body']}"
            ret.append(sr)
        return ret
    
    @truffle.tool("Get Google Trends", icon="chart.line.flattrend.trend.xyaxis")
    @truffle.args(trends="topics to get trends for, max 5")
    def GoogleTrends(self, trends : List[str]) -> str:
        if len(trends) > 5:
            trends = trends[:4]
            print("Max 5 trends allowed, truncating to 5")
        pytrends = TrendReq(hl='en-US', tz=300)
        pytrends.build_payload(kw_list=trends, timeframe='now 7-d')
        print("Getting trends for", trends) 
        data = pytrends.interest_over_time()
        pd.set_option('future.no_silent_downcasting', True)
        return data.to_markdown()

    @truffle.tool("Gets live trending search", icon="chart.line.uptrend.xyaxis")
    @truffle.args(country="The country to get trending searches from, as a json key, ie. united_states")
    def TrendingSearchQueries(self, country: str) -> str:

        valid_countries = ["united_states", "united_kingdom", "australia", "canada", "germany", "france", "india", "japan", "russia", "south_korea"]
        if country not in valid_countries:
            country = "united_states"
            print("Invalid country, defaulting to United States")
        print(f"Getting trending searches for {country}")
        pytrends = TrendReq(hl='en-US', tz=300)
        data = pytrends.trending_searches(pn=country)
        pd.set_option('future.no_silent_downcasting', True)
        return data.to_markdown()



    @truffle.tool("Gets related keywords, and classifies the input", icon="rectangle.and.text.magnifyingglass")
    @truffle.args(keyword="what to get related keywords for")
    def FindRelatedKeywords(self, keyword : str) -> str:
        pytrends = TrendReq(hl='en-US', tz=300)
        data = pytrends.suggestions(keyword)
        print("Find related keywords for", keyword)
        pd.set_option('future.no_silent_downcasting', True)
        df = pd.DataFrame(data).drop(columns='mid')
        return df.to_markdown()
    
    @truffle.tool("This tool writes a file to the given path with the given content. ", icon="keyboard")
    @truffle.args(path="The path to write the file to", content="The content to write to the file")
    def WriteFile(self, path: str, content: str) -> truffle.TruffleFile:
        if len(path) > len(content):
            x = path
            path = content 
            content = x 
        
        print("write file", path)
        directory = os.path.dirname(path)
        if directory:  # Only create directories if there's a path specified
            os.makedirs(directory, exist_ok=True)
        try:
            with open(path, "w") as f:
                f.write(content)
            return truffle.TruffleFile(path, os.path.basename(path))
        except Exception as e:
            truffle.TruffleFile("notfound", "error")

    @truffle.tool("This tool executes a shell command and returns the output. The system is Alpine on arm64, python packages available through apk or pip ", icon="apple.terminal")
    @truffle.args(command="The shell command to execute", timeout="The timeout (seconds) for the command execution")
    def ExecuteCommand(self, command: str, timeout: int) -> List[str]:
        print("ExecuteCommand: ", command)
        return self._run_cmd(command, timeout)
    
    def _run_cmd(self, command, timeout): #demo calling other funcs from within a tool, and that non decorated funcs dont become tools
        self.command_history.append(command)
        output = ""
        try:
            output = subprocess.check_output(
                command, stderr=subprocess.STDOUT, shell=True, timeout=30,
                universal_newlines=True)
        except subprocess.CalledProcessError as exc:
            return ["Shell Command Error (" + str(exc.returncode) + "): " + exc.output, command]
        except subprocess.TimeoutExpired:
            return ["Shell Command Timeout", command]
        except Exception as e:
            return ["Shell Command Error: " + str(e) + '\n Traceback:' + traceback.format_exc(), command]
        else:
            return [output, command]
        
if __name__ == "__main__":
    app = truffle.TruffleApp(Trending())
    app.launch()
````


# TODO:
- docs for SDK apis, like inference within your tools, etc.
- more examples
- pip package
    
