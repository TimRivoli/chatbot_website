from flask import Flask, render_template, request, jsonify
import openai, constants 
app = Flask(__name__)
openai.api_key = constants.openai_api_key
question_history = [] #keeps track of previous questions, the API doesn't remember prior questions asked, the aggregate-questions checkbox will submit all your prior questions with each question
token_limit = 4096 	  #GPT 3.5 turbo limit, 4.0 is much higher
response_tokens = 600 #How many tokens do you want to save for the response?  max_tokens = messages + response

def ask_chatgpt(question:str, system_command:str = "", model:str = 'gpt-3.5-turbo', temperature:float=.1, max_tokens:int=1200):
	openai.api_key = constants.openai_api_key
	messages = []
	if system_command !="": messages.append({"role": "system", "content": system_command})
	messages.append({"role": "user", "content": question})
	try: 
		result = openai.ChatCompletion.create(model=model, messages=messages, temperature=temperature, max_tokens=max_tokens )
		success = True
	except Exception as e:
		print("ChatGPT query failed:", e)
		success = False
		result = "API Call Failed"
	if success: result = result.choices[0].message.content
	return result
 
@app.route('/')
def index():
	return render_template('index.html')

@app.route('/get_response', methods=['POST'])
def get_response():
	question = request.form['user_input'].strip()
	if question !='':
		question_history.append(question)
		aggregate_questions = request.form['aggregate_questions']
		print('x', aggregate_questions, aggregate_questions, type(aggregate_questions))
		if aggregate_questions=='true':
			question = ''
			for q in question_history:
				if not "?" in q: q += "?"
				question += q + " "			
		else:
			question_history.clear()
		if len(question) + response_tokens > token_limit: question = question[token_limit-response_tokens:]
		print(f"Question: {question}")
		gpt_system = "Format response in HTML"
		response = ask_chatgpt(question, gpt_system, max_tokens=(len(question)+response_tokens))
		return jsonify({'response': response})

if __name__ == '__main__':
	app.run(debug=True)