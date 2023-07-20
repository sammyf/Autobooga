# Autobooga

## Acknowledgment :
thanks to 
* Sascha Endlicher of Panomity GmbH for releasing MegaSearch 
for Oobabooga and indirectly making me write this. Part of the Autobooga
code (the Searx search) is heavily based off Megasearch's code.
* The InvokeAI user *Gille*, who actually tried to use this extension and found way too many bugs I really should have caught. 

## What's new :
* Upload file button added

## What it does :
*Autobooga* is just a simple extension for oobabooga that gives
LLMs the ability to call a SEARX search engine and to read URLs, Files ... 
and a clock. 

### The Date and Time
are added at the start of each prompt in the Format :
"It's 12:00 on Friday February, 1 April 2026."

### Files
can be opened by using those key (case insensitive) sentences :
* open the file 
* read the file
* get the file


followed by a path enclosed in quotes (either " or ' work). Text files and PDFs are supported. Note that the content is still subjected to "maximum token extracted" settings.

If the file can not be opened for some reason, the LLM **should** tell you that. Honestly, it's hit and miss. Sometimes it will just hallucinate content.

Some examples
  * Please open the file "c:\\What I Did Last Xmas.txt" and write a song about it.
  * Open the file '/home/kermit/Documents/Love Letters By Miss Piggy.pdf'

**OR** by using the file upload button in the Autobooga panel.


### Internet searches
are generally triggered by the user, by using one of the 

following (case insensitive) key phrases :

  * search the internet for information on 
  * search the internet for information about
  * search for information about
  * search for information on
  * search for
  * I need more information on
  * search the internet for
  * can you provide me with more specific details on
  * what can you find out about
  * what information can you find out about
  * what can you find out on
  * what information can you find out on
  * what can you tell me about
  * what do you know about
  * ask the search engine on
  * ask the search engine about

If the LLM uses any of them it triggers a search itself. In my experience this
doesn't happen very often sadly. 

The search is performed by calling a SEARX-NG instance (https://github.com/searxng). The extension adds glimpses
of the first five hits to the user prompt and marks them as internet search results.
*If you have a raspberry-pi or similar lying around or a server with a bit of free space/bandwidth it's worth thinking 
about installing SEARX-NG on it and to use that for your LLM.* 

### URL Retrieval
are triggered only by the user right now. As soon as there is a 
full URL (including http/https protocol) in the prompt the first 1000 words of the page 
behind the URL are retrieved. The model still receives the whole prompt. If the prompt was 
only the URL a "summarize this page" is added at the end.

## How models perform :
This extension was found to work well with 13B models and especially well with 
30B models. *Uncensored* models seem to perform better than guardrailed ones, and the 
higher the context limit the better. 

On a RTX3090/24GB the models that performed best for me (very subjective and not representative
opinion) were :

   * TheBloke_WizardLM-Uncensored-SuperCOT-StoryTelling-30B-GPTQ
   * TheBloke_orca_mini_v2_13b-GPTQ

I'm still unsure what's most important for this extension : more context or better model, so decide
yourself. It's really a subjective matter. 30B models are great at summarizing pages writen in languages
or even symbols you don't understand, and big context let you ask more questions and go deeper into 
understanding pages and results. It's a trade-off (unless you have tons of VRAM to spare)

## Requirements :
Obviously Oobabooga, and as much VRAM as you can, as context-limit is king. 
You also need to be able to access a Searx instance **with support for json output**. You can find a list of 
public instances here : https://searx.space/ . 

The extension uses these packages : 
`requests
beautifulsoup4
summarizer
datetime
re
PyPDF2`

So nothing horrible that will break your system.

## Installation :
* Check out this repo into `{YOUR OOBABOOGA INSTALLATION DIRECTORY}/extensions`
* Enter the oogabooga virtual environment if you have one and execute
`pip install -r requirements.txt` to install missing modules.
* Either add the extension on startup with 
--extension autobooga or check it in the interface panel
* **modify the settings in the Autobooga Accordeon panel in the UI**

You're set.

Just one last thing ... 


### DON'T TRUST THE LLM!!! 
I mean it! While the models I tried did a terrific job at summarizing stuff they retrieve 
they can still hallucinate heavily. 13B models and lower are especially prone at ignoring what
they read (I had a 7B model actually complaining that its completely fabricated story hadn't made
a bigger splash in the news) and even 30B models are not safe from extrapolating "facts" from random
elements on the page. Always double check if you can, and if you can't then use with extreme caution!

### DON'T TRUST THE LLM!!! 
Yes. that was on purpose and not an accidental copy and paste.

## THE WOKE PART ...
Anyway ... have fun and enjoy the fact that we live in the future with AI, Electric Cars, VR, and a 
global climatic catastrophe just right around the corner. Also, remember that you probably use up less
energy running LLMs at home on your gaming rig than if you used ChatGPT, Bing or Bard all the time. (and probably
still less than if you played Cyberpunk2077 or any other graphically challenging game)!
