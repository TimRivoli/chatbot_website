//buttons
const clearButton = document.getElementById('clear-button');
const conversationsButton = document.getElementById('conversations-button');
const copyButton = document.getElementById('copy-button');
const logoutButton = document.getElementById('logout-button');
const sendButton = document.getElementById('send-button');

//Options
const conversationMode = document.getElementById('conversation-mode'); 
const responseSize = document.getElementById('response-size'); 
const temperature = document.getElementById('temperature'); 
const customInstructions = document.getElementById('user-instructions'); 

//other
const chatBox = document.getElementById('chat-box');
const userInput = document.getElementById('user-input');

function addUserMessage(message) { chatBox.innerHTML += `<div class="user-message">${message}</div>`; }
function addResponseMessage(message) { chatBox.innerHTML += `<div class="bot-message">${message}</div>`; }

sendButton.addEventListener('click', async () => {
    const userMessage = userInput.value;
    addUserMessage(userMessage);
	userInput.value = '';
    const formData = new URLSearchParams({user_input: userMessage, conversation_mode: conversationMode.checked, response_size: responseSize.value, temperature: temperature.value, user_instructions: customInstructions.value});
    const response = await fetch('/chat_query', {method: 'POST', body: formData,}).then(response => response.json());
	addResponseMessage(response.response);
    chatBox.scrollTop = chatBox.scrollHeight;
});
	
userInput.addEventListener('keydown', event => {
	if (event.key === 'Enter') {
		event.preventDefault(); 
		sendButton.click(); 
	}
});

conversationsButton.addEventListener('click', function() {
	window.location.href = '/conversations';
});

clearButton.addEventListener('click', () => { 	window.location.href = '/';});

// copyButton.addEventListener('click', () => {
    // const botMessages = document.querySelectorAll('.bot-message');
    // const textToCopy = Array.from(botMessages).map(message => message.textContent).join('\n');   
    // const tempTextarea = document.createElement('textarea');
    // tempTextarea.value = textToCopy;
    // document.body.appendChild(tempTextarea);
    // tempTextarea.select();
    // document.execCommand('copy');
    // document.body.removeChild(tempTextarea);
// });

logoutButton.addEventListener('click', function() {
	window.location.href = '/logout';
});

