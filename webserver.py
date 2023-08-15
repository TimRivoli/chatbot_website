from flask import Flask, render_template, request, jsonify, session
import openai, constants, tiktoken

app = Flask(__name__)
app.secret_key = 'shamalamabingbam_yougotit'
openai.api_key = constants.openai_api_key
token_limit = 4096 	  #GPT 3.5 turbo limit, 4.0 is much higher

#the API doesn't remember prior questions and answers, the conversation_mode checkbox will submit the conversation history to the model which provides context but uses more tokens
#session variables
#'question_history' list to track previous questions
#'response_history' list to track previous responses
#'conversation_summary' string conversation summarized as needed to reduce the size of the messages
max_question_length = 200  		   #Trim the history to this number of characters
max_history_response_length = 750  #Trim the history to this number of characters
openai.api_key = constants.openai_api_key

def _chatgpt_query(messages:list, response_tokens:int=1000, temperature:float=.2, include_usage_summary:bool=False, model:str = 'gpt-3.5-turbo'):
	try: 
		result = openai.ChatCompletion.create(model=model, messages=messages, temperature=temperature, max_tokens=response_tokens)
		success = True
	except Exception as e:
		print("ChatGPT query failed:", e)
		success = False
		result = "API Call Failed"
	if success: 
		usage_summary = f"Usage Summary (Prompt: {result.usage.prompt_tokens} - Response: {result.usage.completion_tokens} - Total Tokens: {result.usage.total_tokens} - Response Limit: {response_tokens}  - Specified Model Limit: {token_limit})"
		print(usage_summary)
		result = result.choices[0].message.content
		session['response_history'].append(result[:max_history_response_length])
		result = result.replace("\n", "<BR>") 
		result += "<BR>" + usage_summary
	return result
	
def _token_count(text:str):
	token_count=0
	if text:
		encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
		token_count = len(encoding.encode(text))
		print(f"The text contains {token_count} tokens.")
	return token_count

def _session_init():
	if not 'question_history' in session:
		print('Session initialized.')
		session['conversation_summary'] = ''
		session['question_history'] = []
		session['response_history'] = []
		session['converstation_length'] = 0

def _converstation_history_clear():
	print('Clearning chat history')
	session['conversation_summary'] = ''
	session['question_history'].clear()
	session['response_history'].clear()

def _converstation_summarize(messages:list):
	print('Summarizing converstation...')
	session['conversation_summary'] = _chatgpt_query(messages=messages, response_tokens=1000, temperature=0.0)
	print(session['conversation_summary'])

def _converstation_history_get(tokens_spoken_for:int = 0):
	messages = []
	#print(len(session['question_history']), len(session['response_history']))
	while len(session['question_history']) < len(session['response_history']): session['response_history'].append("") #These could get out of sync with asyc calls if the user spam clicks
	while len(session['response_history']) > len(session['question_history']): session['response_history'].pop(0)	
	#print(len(session['question_history']), len(session['response_history']))
	if session['conversation_summary'] !='': 
		tokens_spoken_for += _token_count(session['conversation_summary'])
		messages.append({"role": "system", "content": 'Summary of our conversation so far: ' + session['conversation_summary']})
	tokens_estimated = tokens_spoken_for
	for i in range(len(session['question_history'])):
		q = session['question_history'][i]
		a = session['response_history'][i]
		messages.append({"role": "user", "content": q})
		messages.append({"role": "assistant", "content": a})
		tokens_estimated += _token_count(q +' '+ a)
	if tokens_estimated  > token_limit -400 and len(messages) > 1:
		while tokens_estimated  > token_limit and len(messages) > 1:
			x = messages.pop(1)
			tokens_estimated -= _token_count(x)
		_summarize_converstation(messages)
	return messages

@app.route('/')
def index():
	_session_init()
	return render_template('index.html')

@app.route('/clear_history', methods=['POST'])
def clear_history():
	_converstation_history_clear()
	response = 'Chat history cleared.'
	print(response)
	return jsonify({'response': response})

@app.route('/get_response', methods=['POST'])
def get_response():
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
		user_instructions = request.form['user_instructions'][:max_question_length].strip()
		
		messages = []
		system_command = "Be descriptive and if the response has more than 50 tokens then use HTML formatting"
		if user_instructions !='': system_command = user_instructions + '. ' + system_command
		messages.append({"role": "system", "content": system_command})
		token_estimate = _token_count(system_command + ' ' + question) + response_tokens
		if conversation_mode:	#add as much of the conversation history as possible without risking going over max_tokens
			messages += _converstation_history_get(tokens_spoken_for=token_estimate)
		else:
			_converstation_history_clear()
		messages.append({"role": "user", "content": question})
		session['question_history'].append(question[:max_question_length])
		print(messages)
		response = _chatgpt_query(messages, response_tokens, temperature=temperature)
	return jsonify({'response': response})

@app.route('/logout')
def logout():
    session.clear()
    return 'Logged out successfully'
	
if __name__ == '__main__':
	app.run(debug=True)