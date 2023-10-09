from functools import wraps
from flask import Flask, redirect, render_template, request, jsonify, session, url_for
import openai, tiktoken, uuid
import firebase_admin
from flask_oauthlib.client import OAuth
from google.oauth2 import id_token
from google.auth.transport import requests
from _classes.Constants import *

app = Flask(__name__)
app.secret_key = google_api_key
openai.api_key = openai_api_key
token_limit = 4096 	  #GPT 3.5 turbo limit, 4.0 is much higher
max_question_length = 200  		   #Used to limit user input length
max_history_response_length = 750  #Trim the history to this number of characters
user_list = []
conversation_history = {} #Stores conversation history for each active user
conversation_summary = {}   #Stores conversation summary for each active user
default_model = 'gpt-3.5-turbo'
enhanced_model = 'gpt-4'
current_model = default_model

# ------------------------------------------------------- Google OAuth  ---------------------------------------------------------
oauth = OAuth(app)
google = oauth.remote_app(
    'google',
    consumer_key=google_client_id, 
    consumer_secret=google_client_secret,
    request_token_params={'scope': 'email', },
    base_url='https://www.googleapis.com/oauth2/v1/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://accounts.google.com/o/oauth2/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
)
	
# ------------------------------------------------------- API Calls ---------------------------------------------------------
def _execute_query(messages:list, response_tokens:int=1000, temperature:float=.2, include_usage_summary:bool=False, model:str = default_model):
	try: 
		model_result = openai.ChatCompletion.create(model=model, messages=messages, temperature=temperature, max_tokens=response_tokens)
		success = True
	except Exception as e:
		print("ChatGPT query failed:", e)
		success = False
		result = "API Call Failed. " + str(e)
		#Incorrect API key provided
		#The model `gpt-4` does not exist or you do not have access to it. Learn more: https://help.openai.com/en/articles/7102672-how-can-i-access-gpt-4.
	if success: 
		usage_summary = f"Usage Summary (Prompt: {model_result.usage.prompt_tokens}, Response: {model_result.usage.completion_tokens}, Total Tokens: {model_result.usage.total_tokens}, Response Limit: {response_tokens}, Specified Model Limit: {token_limit})"
		print(usage_summary)
		result = model_result.choices[0].message.content
		x = result[:max_history_response_length]
		token_count = _token_count(x)
		_converstation_append(content=x, token_count=token_count, is_response=True)
		result = result.replace("\n", "<BR>") 
		result = result.replace("<BR><BR>", "<BR>") 
		result = result.replace("<BR><BR>", "<BR>") 
		if include_usage_summary: result += "<BR>" + usage_summary
	return result
	
def _token_count(text:str):
	token_count=0
	if text:
		encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
		token_count = len(encoding.encode(text))
		print(f" The text contains {token_count} tokens.")
	return token_count

# ------------------------------------------------ User Session Management  -------------------------------------------------
def _session_init():
	if not 'uid' in session:
		user_id = uuid.uuid4()
		session['uid'] = user_id
		user_list.append(user_id)
		session.modified = True
		print(' Session created: ', user_id)
	else:
		user_id = session['uid']
	if not user_id in conversation_history:
		conversation_history[user_id] = []
		conversation_summary[user_id] = {"content": "", "tokens": 0}
		print(' Session initialized: ', user_id)

def _converstation_clear():
	conversation_history[session['uid']] = []
	conversation_summary[session['uid']] = {"content": "", "tokens": 0}
	print(' Chat history cleared: ', session['uid'])

def _converstation_append(content:str, token_count:int, is_response:bool):
	if len(content) > 0:
		if is_response:
			conversation_history[session['uid']].append({"role": "assistant", "content": content[:max_history_response_length], "tokens": token_count})
		else:
			conversation_history[session['uid']].append({"role": "user", "content": content[:max_question_length], "tokens": token_count})		

def _converstation_summarize(messages:list):
	print(' Summarizing converstation...')
	content = _execute_query(messages=messages, response_tokens=1000, temperature=0.0)
	token_count = _token_count(content)
	conversation_summary[session['uid']]  = {"content": content, "tokens": token_count}
	while len(conversation_history[session['uid']]) > 50:
		x = conversation_history[session['uid']].pop(0)
	for i in range(len(conversation_history[session['uid']])):
		x = conversation_history[session['uid']][i]
		tokens = x['tokens']
		if x['role'] == "assistant" and tokens > 25:
			content = x['content']
			if tokens > 500:
				content = content[:500]
			elif x['tokens'] > 100:
				content = content[:100]
			elif x['tokens'] > 50:
				content = content[:50]
			elif x['tokens'] > 25:
				content = content[:25]
			tokens = _token_count(content)
			conversation_history[session['uid']][i]['content'] = content
			conversation_history[session['uid']][i]['tokens'] = tokens			
	print(' Conversation Summary: ', content)

def _converstation_history_get(tokens_spoken_for:int = 0):
	messages = []
	if conversation_summary[session['uid']]['content'] !='': 
		tokens_spoken_for += conversation_summary[session['uid']]['tokens']
		messages.append({"role": "system", "content": 'Conversation summary: ' + conversation_summary[session['uid']]['content']})
	tokens_estimated = tokens_spoken_for
	for m in conversation_history[session['uid']]:
		messages.append({"role": m['role'], "content": m['content']})
		tokens_estimated += m['tokens']
	if tokens_estimated > token_limit/3 and len(messages) > 1:
		print('Trimming and summarizing conversation..')
		if 'Summary' in messages[0]['content']: 
			x = messages.pop(0)
			tokens_spoken_for -= conversation_summary[session['uid']]['tokens']
		_converstation_summarize(messages)
		tokens_spoken_for += conversation_summary[session['uid']]['tokens']
		messages.insert(0, {"role": "system", "content": 'Conversation summary: ' + conversation_summary[session['uid']]['content']})
		while tokens_estimated > token_limit and len(messages) > 1:
			x = messages.pop(1)
			print('Removing ', x['content'])
			tokens_estimated -= x['tokens']
	return messages

# ------------------------------------------------------- Web Handling ------------------------------------------------------
@app.route('/login')
def login():
	return google.authorize(callback=url_for('authorized', _external=True))

@app.route('/logout')
def logout():
	_converstation_clear()
	session.clear()
	session.pop('google_token', None)
	return "You have been logged out."
	
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'google_token' in session:
            return f(*args, **kwargs)
        else:
            return redirect(url_for('login'))
    return decorated_function

@app.route('/')
@login_required
def index():
	if 'google_token' in session:
		user_info = google.get('userinfo')
		user_id = google.get('sub')
		print("user_info: ", user_info.data)
		print("user_id: ", user_id.data)
		_session_init()
		return render_template('conversation.html', username=user_info.data['email'])
	else:
		return 'You are not logged in.'


@app.route('/login/authorized')
def authorized():
	response = google.authorized_response()
	if response is None or response.get('access_token') is None:
		return 'Access denied: reason={} error={}'.format(
			request.args['error_reason'],
			request.args['error_description']
		)
	session['google_token'] = (response['access_token'], '')
	user_info = google.get('userinfo')
	result = 'Logged in as: ' + user_info.data['email']
	result +="<script> setTimeout(function() {window.location.href = '/';  }, 3000);     </script>"
	return result

@google.tokengetter
def get_google_oauth_token():
	return session.get('google_token')

@app.route('/clear_chat', methods=['POST'])
@login_required
def clear_chat():
	_converstation_clear()
	return redirect('/')


@app.route('/chat_query', methods=['POST'])
@login_required
def chat_query():
	_session_init()
	question = request.form['user_input'][:max_question_length].strip()
	response = ""
	if question !='':
		x = request.form['conversation_mode']
		conversation_mode = (x=='true') 
		x = request.form['response_size']
		response_tokens = 1000
		if x =='small':	response_tokens = 350
		if x =='large':	response_tokens = 2000
		if x =='verylarge':	response_tokens = 3500
		x = request.form['temperature']
		temperature = float(x)/10
		
		system_command = "Be descriptive and if the response has more than 50 tokens then use HTML formatting"
		#system_command = "Provide a detailed description of the issue or topic. If your response contains more than 50 tokens, use HTML formatting to ensure clarity. In the conversation history, the assistant's responses may be truncated to prioritize information the user provided."
		system_tokens = len(system_command.split())
		user_instructions = request.form['user_instructions'][:max_question_length].strip()
		user_tokens = _token_count(user_instructions + '. ' + question)	
		if user_instructions !='': system_command = user_instructions + '. ' + system_command
		messages = []
		messages.append({"role": "system", "content": system_command})
		token_estimate = system_tokens + user_tokens + response_tokens
		if conversation_mode:	#add as much of the conversation history as possible without risking going over max_tokens
			messages += _converstation_history_get(tokens_spoken_for=token_estimate)
		messages.append({"role": "user", "content": question})
		_converstation_append(content=question, token_count=user_tokens, is_response=False)
		print(messages)
		response = _execute_query(messages, response_tokens, include_usage_summary=True, temperature=temperature, model=current_model)
	return jsonify({'response': response})
	
@app.errorhandler(404)
def page_not_found(e):
	result = "Page not found. Redirecting to home page..."
	result +="<script> setTimeout(function() {window.location.href = '/';  }, 3000);     </script>"
	return result
    #flash('Page not found. Redirecting to home page in 1 second...', 'error')
    #return redirect(url_for('index', _external=True), code=302)
	
if __name__ == '__main__':
	app.run(debug=True)