###################
# Autobooga
# Copyright (C) 2023 by Sammy Fischer (autobooga@cosmic-bandito.com)
# 
# This program is free software: you can redistribute it and/or modify it under the 
# terms of the GNU General Public License as published by the Free Software Foundation, 
# either version 3 of the License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; 
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. 
# See the GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along with this program. 
# If not, see <https://www.gnu.org/licenses/>.
#
import os.path
import string
import requests
import json
from bs4 import BeautifulSoup
from summarizer import Summarizer
from modules import chat
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import re
import gradio as gr

CONFIG_FILE="extensions/autobooga/autobooga_config.json"
############# TRIGGER PHRASES  #############
## you can add anything you like here, just be careful not to trigger unwanted searches or even loops
INTERNET_QUERY_PROMPTS=[ "search the internet for information on", "search the internet for information about",
                         "search for information about", "search for information on", "search for ",
                         "i need more information on ", "search the internet for ",
                         "can you provide me with more specific details on ",
                         "can you provide me with details on ",
                         "can you provide me with more details on ",
                         "can you provide me with more specific details about ",
                         "can you provide me with details about ",
                         "can you provide me with more details about ",                                                  
                         "what can you find out about ", "what information can you find out about ",
                         "what can you find out on ", "what information can you find out on ",
                         "what can you tell me about ", "what do you know about ",  "ask the search engine on ",
                         "ask the search engine about ", "ask the seach engine on "]

DBNAME = ""
character  = ""

# If 'state' is True, will hijack the next chat generation
input_hijack = {
    'state': False,
    'value': ["", ""]
}

with open(CONFIG_FILE) as f:
    config = json.load(f)

params = {
    "searx_server":config['searx_server'],
    "max_search_results":config['max_search_results'],
    "max_text_length":config['max_text_length']
}

def set_searx_server( x):
    params.update({"searx_server": x})
    with open('extensions/moztts/tts_config.json', 'w') as f:
        json.dump(params, f, indent=4)

def set_max_search_results( x):
    params.update({"maximum_search_results": x})
    with open(CONFIG_FILE, 'w') as f:
        json.dump(params, f, indent=4)

def set_max_extracted_text(x):
    params.update({"maximum_text_length": x})
    with open(CONFIG_FILE, 'w') as f:
        json.dump(params, f, indent=4)

def call_searx_api(query):
    url = f"{params['searx_server']}?q={query}&format=json"
    try:
        response = requests.get(url)
    except:
        return "An internet search returned no results as the SEARX server did not answer."
    # Load the response data into a JSON object.
    try:
        data = json.loads(response.text)
    except:
        return "An internet search returned no results as the SEARX server doesn't seem to output json."
    # Initialize variables for the extracted texts and count of results.
    texts = ''
    count = 0
    max_results = params['max_search_results']
    rs = "An internet search returned these results:"
    result_max_characters = params['max_text_length']
    # If there are items in the data, proceed with parsing the result.
    if 'results' in data:
        # For each result, fetch the webpage content, parse it, summarize it, and append it to the string.
        for result in data['results']:
            # Check if the number of processed results is less than or equal to the maximum number of results allowed.
            if count <= max_results:
                # Get the URL of the result.
                # we won't use it right now, as it would be too much for the context size we have at hand
                link = result['url']
                # Fetch the webpage content of the result.
                content = result['content']
                if len(content) > 0:  # ensure content is not empty
                    # Append the summary to the previously extracted texts.
                    texts = texts + ' ' + content+"\n"
                    # Increase the count of processed results.
                    count += 1
        # Add the first 'result_max_characters' characters of the extracted texts to the input string.
        rs += texts[:result_max_characters]
    # Return the modified string.
    return rs

## returns only the first URL in a prompt
def extract_url(prompt):
    url=""
    # Regular expression to match URLs
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    # Find all URLs in the text
    urls = re.findall(url_pattern, prompt.lower())
    if len(urls)>0:
        url=urls[0]
    return url


def trim_to_x_words(prompt:string, limit:int):
    rev_rs = []
    words = prompt.split(" ")
    rev_words = reversed(words)
    for w in rev_words:
        rev_rs.append(w)
        limit -= 1
        if limit <= 0:
            break;
    rs = reversed(rev_rs)
    return " ".join(rs)

def extract_query(prompt):
    rs=["",""]
    # Define your sentence-terminating symbols
    terminators = [".", "!", "?"]
    # Join the terminators into a single string, separating each with a pipe (|), which means "or" in regex
    pattern = "|".join(map(re.escape, terminators))

    search_prompt = ""
    for qry in INTERNET_QUERY_PROMPTS:
        if qry in prompt.lower():
            search_prompt = qry
            break
    if search_prompt != "":
        query_raw = prompt.lower().split(search_prompt)[1]
        rs[1] = query_raw[0]+"."
        # Split the text so that we only have the search query
        query = re.split(pattern, query_raw)
        q = query[0]
        q = q.replace(" this year ", datetime.now().strftime("%Y"))
        q = q.replace(" this month ", datetime.now().strftime("%B %Y"))
        q = q.replace(" today ", datetime.now().strftime("'%B,%d %Y'"))
        q = q.replace(" this month ", datetime.now().strftime("%B %Y"))
        q = q.replace(" yesterday ", (datetime.today() - timedelta(days=1)).strftime("'%B,%d %Y'"))
        q = q.replace(" last month ", (datetime.today() - relativedelta(months=1)).strftime("%B %Y"))
        q = q.replace(" last year ", (datetime.today() - relativedelta(years=1)).strftime("%Y"))
        rs[0] = q
        for rest in q[1:]:
            rs[1] += rest
    return rs

def get_page(url, prompt):
    text = "This web page doesn't have any useable content. Sorry."
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    paragraphs = soup.find_all('p')
    if len(paragraphs) > 0:
        text = '\n'.join(p.get_text() for p in paragraphs)
    else:
        text = f"This web page doesn't seem to have any readable content."
        metas = soup.find_all("meta")
        for m in metas:
            if 'content' in m.attrs:
                if m['name'] == 'page-topic' or m['name'] == 'description':
                    text += f"It's {m['name']} is '{m['content']}'"
    if prompt == url:
        prompt = f"Summarize the content from this url : {url}"
    prompt = f"{prompt}\nContent of {url} : \n{trim_to_x_words(text, params['max_text_length'])}[...]\n"
    return prompt

def output_modifier(llm_response, state):
    global character
    # print("original response : "+llm_response)
    # If the LLM needs more information, we call the SEARX API.
    q = extract_query(llm_response)
    if q[0] != "":
        input_hijack.update({'state':True,'value':[f"\nsearch for "+q[0], f"Searching the internet for information on '{q[0]}' ..."]})
        ## this is needed to avoid a death loop.
        llm_response = f"I'll ask the search engine on {q[0]} ..."
    return llm_response

def input_modifier(prompt, state):
    global character
    if character == "":
        character = state["character_menu"]
    now = "it is " + datetime.now().strftime("%H:%M on %A %B,%d %Y") + "."

    q = extract_query(prompt)
    if q[0] != "":
        searx_results = call_searx_api(q[0])
        # Pass the SEARX results back to the LLM.
        if(q[1] == ""):
            q[1] = "Summarize the results."
        prompt = prompt + "." + searx_results+"."+q[1]
    else:
        url = extract_url(prompt)
        if url != "":
            prompt = get_page(url, prompt)
    return now+"\n"+prompt

def ui():
    with gr.Accordion("AutoBooga"):
        with gr.Row():
            searx_server = gr.Textbox(value=params['searx_server'], label='Searx-NG Server capable of returning JSon')
        with gr.Row():
            max_search_results = gr.Textbox(value=params['max_search_results'], label='The amount of search results to read.')
        with gr.Row():
            max_extracted_text = gr.Text(value=params['max_text_length'], label='The maximum amount of words to read. Anything after that is truncated')

    searx_server.change(lambda s: set_searx_server(s), searx_server, None),
    max_search_results.change(lambda s: set_max_search_results(s), max_search_results, None),
    max_extracted_text.change(lambda s: set_max_extracted_text(s), max_extracted_text, None),
