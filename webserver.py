from flask import Flask, render_template, request, jsonify
import openai, constants 
app = Flask(__name__)
openai.api_key = constants.openai_api_key
token_limit = 4096 	  #GPT 3.5 turbo limit, 4.0 is much higher
#the API doesn't remember prior questions and answers, the conversation_mode checkbox will submit the conversation history to the model which provides context but uses more tokens
question_history = [] #keeps track of previous questions
response_history = [] #keeps track of previous responses
conversation_summary = '' #summarize conversation as needed to reduce the size of the messages
max_question_length = 150  #Trim the history to this number of characters
max_history_response_length = 500  #Trim the history to this number of characters
openai.api_key = constants.openai_api_key

#conversation_summary = "In our conversation, you initially asked about how to play chess. I provided a description explaining the setup of the chessboard and the basics of moving the pieces. Then, you asked about how to play Magic: The Gathering, to which I began explaining the process of deck construction and the objective of reducing your opponent's life total to zero. Finally, you mentioned that your name is Bob."

def _clear_history():
	conversation_summary = ''
	question_history.clear()
	response_history.clear()

def _ask_chatgpt(messages:list, response_tokens:int=1000, temperature:float=.2, include_usage_summary:bool=False, model:str = 'gpt-3.5-turbo'):
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
		response_history.append(result[:max_history_response_length])
		result = result.replace("\n", "<BR>") 
		result += "<BR>" + usage_summary
	return result
 
def _summarize_converstation(messages:list):
	print('Summarizing converstation...')
	conversation_summary = _ask_chatgpt(messages=messages, response_tokens=1000, temperature=0.0)
	print(conversation_summary)

@app.route('/')
def index():
	return render_template('index.html')

@app.route('/clear_history', methods=['POST'])
def clear_history():
	_clear_history()
	response = 'Chat history cleared.'
	print(response)
	return jsonify({'response': response})

@app.route('/get_response', methods=['POST'])
def get_response():
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
		
		#question:str,  conversation_mode:bool=False,
		messages = []
		system_command = "Be descriptive and if the response has more than 50 tokens then use HTML formatting"
		if user_instructions !='': system_command = user_instructions + '. ' + system_command
		messages.append({"role": "system", "content": system_command})
		if conversation_mode:	#add as much of the conversation history as possible without risking going over max_tokens
			print(len(question_history), len(response_history))
			while len(question_history) < len(response_history): response_history.append("") #These could get out of sync with asyc calls if the user spam clicks
			while len(response_history) > len(question_history): response_history.pop(0)	
			print(len(question_history), len(response_history))
			if len(conversation_summary) > 0: messages.append({"role": "system", "content": 'Summary of our conversation so far: ' + conversation_summary})
			tokens_estimated = len(system_command) + len(question) + len(conversation_summary)			
			for i in range(len(question_history)):
				q = question_history[i]
				a = response_history[i]
				messages.append({"role": "user", "content": q})
				messages.append({"role": "assistant", "content": a})
				tokens_estimated += len(q) + len(a)
			if tokens_estimated + response_tokens > token_limit-600 and len(messages) > 1:
				while tokens_estimated + response_tokens > token_limit and len(messages) > 1:
					x = messages.pop(1)
					tokens_estimated -= len(x)
				_summarize_converstation(messages)
		else:
			_clear_history()
		messages.append({"role": "user", "content": question})
		question_history.append(question[:max_question_length])
		print(messages)	
		response = _ask_chatgpt(messages, response_tokens, temperature=temperature)
	return jsonify({'response': response})

if __name__ == '__main__':
	app.run(debug=True)