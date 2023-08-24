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
from modules import chat, shared
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import re
import gradio as gr
from PyPDF2 import PdfReader

CONFIG_FILE="extensions/Autobooga/autobooga_config.json"
LOG_DIR="logs/AB_"
LOG_FILE="_logs.txt"
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
                         "ask the search engine about "]

FILE_QUERY_PROMPTS=[
    "open the file ",
    "read the file ",
    "summarize the file ",
    "get the file "
]

DBNAME = ""
character  = "None"

# If 'state' is True, will hijack the next chat generation
input_hijack = {
    'state': False,
    'value': ["", ""]
}

def write_config():
    with open(CONFIG_FILE, 'w') as f:
        json.dump(params, f, indent=4)

def write_log(char, s):
    try:
        with open(LOG_DIR+char+LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(s)
    except Exception as e:
        print(f"Error writing to log: {e}")

config = []
try:
    with open(CONFIG_FILE) as f:
        config = json.load(f)
except:
    config = []

params = {
    "searx_server":"enter the url to a searx server capable of json here.",
    "max_search_results":5,
    "max_text_length":1000,
    "upload_prompt":"Please summarize the following text, one paragraph at a time:",
    "upload_position":"before",
    "logging_enabled":1
}

if 'searx_server' in config:
    params.update({"searx_server":config['searx_server']})
if 'max_search_results' in config:
    try:
        params.update({"max_search_results":int(config['max_search_results'])})
    except:
        pass
if 'max_text_length' in config:
    try:
        params.update({"max_text_length":int(config['max_text_length'])})
    except:
        pass
if 'upload_prompt' in config:
    params.update({"upload_prompt":config['upload_prompt']})
if 'upload_position' in config:
        params.update({"upload_position": config['upload_position']})

write_config()


def set_upload_prompt( x):
    params.update({"upload_prompt": x})
    write_config()

def set_upload_position( x):
    params.update({"upload_position": x})
    write_config()

def set_searx_server( x):
    params.update({"searx_server": x})
    write_config()

def set_max_search_results( x):
    try:
        params.update({"max_search_results": int(x)})
    except:
        pass
    write_config()


def set_max_extracted_text(x):
    try:
        params.update({"max_text_length": int(x)})
    except:
        pass
    write_config()

def set_logging_enabled(x):
    try:
        params.update({"logging_enabled": int(x)})
    except:
        pass
    write_config()

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
        # Add the first 'result_max_acters' characters of the extracted texts to the input string.
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

def extract_file_name( prompt):
    rs=""
    query_raw = ""
    for qry in FILE_QUERY_PROMPTS:
        pattern = rf'{qry}(.*)'
        match = re.search(pattern, prompt, re.IGNORECASE)  # re.IGNORECASE makes the search case-insensitive
        if match:
            query_raw = match.group(1)
            break
    if query_raw != "":
        pattern = r"([\"'])(.*?)\1"
        query = re.search(pattern, query_raw)
        if query is not None:
            rs = query.group(2)
    return rs

def get_page(url, prompt):
    text = f"The web page at {url} doesn't have any useable content. Sorry."
    try:
        response = requests.get(url)
    except:
        return f"The page {url} could not be loaded"
    soup = BeautifulSoup(response.content, 'html.parser')
    paragraphs = soup.find_all('p')
    if len(paragraphs) > 0:
        text = '\n'.join(p.get_text() for p in paragraphs)
        text = f"Content of {url} : \n{trim_to_x_words(text, params['max_text_length'])}[...]\n"
    else:
        text = f"The web page at {url} doesn't seem to have any readable content."
        metas = soup.find_all("meta")
        for m in metas:
            if 'content' in m.attrs:
                try:
                    if 'name' in m and m['name'] == 'page-topic' or m['name'] == 'description':
                        if 'content' in m and m['content'] != None:
                            text += f"It's {m['name']} is '{m['content']}'"
                except:
                    pass
    if prompt.strip() == url:
        text += f"\nSummarize the content from this url : {url}"
    return text

def read_pdf( fname):
    parts = []

    def visitor_body(text, cm, tm, fontDict, fontSize):
        y = tm[5]
        if y > 50 and y < 720:
            parts.append(text)

    pdf = PdfReader(fname)
    rs = ""
    for page in pdf.pages:
        page.extract_text(visitor_text=visitor_body)
        text_body = "".join(parts)
        text_body = text_body.replace("\n", "")
        rs += text_body+"\n"
        if rs != trim_to_x_words(rs, params['max_text_length']):
            break
    return rs

def open_file(fname):
    rs = ""
    print(f"Reading {fname}")
    if fname.lower().endswith(".pdf"):
        try:
            rs = read_pdf(fname)
        except:
            return "The file can not be opened. Perhaps the filename is wrong?"
    else:
        try:
            with open(fname, 'r') as f:
                lines = f.readlines()
        except:
            return "The file can not be opened. Perhaps the filename is wrong?"
        rs = "\n".join(lines)
    rs = trim_to_x_words(rs, params['max_text_length'] )
    return f"This is the content of the file '{fname}':\n{rs}"

def chat_input_modifier(text, visible_text, state):
    global input_hijack
    if input_hijack['state']:
        input_hijack['state'] = False
        return input_hijack['value']
    else:
        return text, visible_text


def output_modifier(llm_response, state):
    global character
    try:
        character = state["character_menu"]+"("+shared.model_name+")"
    except:
        character = "None"+"("+shared.model_name+")"
    # print("original response : "+llm_response)
    # If the LLM needs more information, we call the SEARX API.
    q = extract_query(llm_response)
    if q[0] != "":
        input_hijack.update({'state':True,'value':[f"\nsearch for information on '{q[0]}'\n", f"Search for information on '{q[0]}'\n"]})
        ## this is needed to avoid a death loop.
        llm_response = f"I'll ask the search engine on {q[0]} ..."
    if params['logging_enabled'] == 1:
        now = datetime.now().strftime("%H:%M on %A %B,%d %Y")
        write_log(character, "("+now+")"+character+"> "+llm_response+"\n")
    return llm_response

def input_modifier(prompt, state):
    global character
    try:
        character = state["character_menu"]+"("+shared.model_name+")"
    except:
        character = "None"+"("+shared.model_name+")"
    now = "it is " + datetime.now().strftime("%H:%M on %A %B,%d %Y") + "."
    fn = extract_file_name(prompt)
    url = extract_url(prompt)
    q = extract_query(prompt)
    print(f"Filename found : '{fn}'\nQuery found : {q[0]}\nUrl found : {url}\n")
    if fn != "":
        prompt = open_file(fn)+prompt
    elif url != "":
            prompt = get_page(url, prompt)+prompt
    elif q[0] != "":
        searx_results = call_searx_api(q[0])
        # Pass the SEARX results back to the LLM.
        if(q[1] == ""):
            q[1] = "Summarize the results."
        prompt = prompt + "\n" + searx_results+"."+q[1]
    if params['logging_enabled'] == 1:
        _now = datetime.now().strftime("%H:%M on %A %B,%d %Y")
        write_log(character, "\n\n("+_now+") USER > "+prompt+"\n")
    return now+"\n"+prompt

def dragAndDropFile(path):
    prompt = f"{open_file(path)}\n{params['upload_prompt']}\n"
    if params['upload_position'] == "before":
        prompt = f"{params['upload_prompt']}\n{open_file(path)}\n"
    input_hijack.update({"state": True,
                         "value": [
                             prompt,
                             f"{params['upload_prompt']}"]})

def upload_file(file):
    file_path = file.name
    print(f"\nUPLOAD-PATH : {file_path}\n")
    dragAndDropFile(file_path)
    return file_path

def ui():
    with gr.Accordion("AutoBooga"):
        with gr.Row():
                file_output = gr.File()
                upload_button = gr.UploadButton("Click to Upload a PDF, TXT or CSV file.NOTE: Some text files do not work if they are, apparently, using newline/formfeed as end of line sequence instead of just newline.", file_types=[".txt", ".pdf", ".csv", ".*"], file_count="single")
                upload_button.upload(upload_file, upload_button, file_output).then(
                    chat.generate_chat_reply_wrapper, shared.input_params, shared.gradio['display'],
                    show_progress=False)
        with gr.Row():
            fu_prompt = gr.Textbox(value=params['upload_prompt'], label='Prompt accompanying uploaded files.')
        with gr.Row():
            fu_position = gr.Dropdown(choices=["before", "after"], value=params['upload_position'], label='Position of the uploaded files prompt in respect to the files content.')
        with gr.Row():
            searx_server = gr.Textbox(value=params['searx_server'], label='Searx-NG Server capable of returning JSon')
        with gr.Row():
            max_search_results = gr.Textbox(value=params['max_search_results'], label='The amount of search results to read.')
        with gr.Row():
            max_extracted_text = gr.Textbox(value=params['max_text_length'], label='The maximum amount of words to read. Anything after that is truncated')
        with gr.Row():
            logging = gr.Checkbox(value=params['logging_enabled'], label='Log all the dialogs for posterity')

    fu_prompt.change(lambda x: set_upload_prompt(x), fu_prompt, None)
    fu_position.change(lambda x: set_upload_position(x), fu_position, None)

    searx_server.change(lambda x: set_searx_server(x), searx_server, None)
    max_search_results.change(lambda x: set_max_search_results(x), max_search_results, None)
    max_extracted_text.change(lambda x: set_max_extracted_text(x), max_extracted_text, None)
    logging.change( lambda x: set_logging_enabled(x), logging, None)