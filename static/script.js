const chatBox = document.getElementById('chat-box');
const userInput = document.getElementById('user-input');
const sendButton = document.getElementById('send-button');
const clearButton = document.getElementById('clear-button');
const copyButton = document.getElementById('copy-button');
const conversationMode = document.getElementById('conversation-mode'); 
const responseSize = document.getElementById('response-size'); 
const temperature = document.getElementById('temperature'); 
const customInstructions = document.getElementById('user-instructions'); 

sendButton.addEventListener('click', async () => {
    const userMessage = userInput.value;
    chatBox.innerHTML += `<div class="user-message">${userMessage}</div>`;
    userInput.value = '';
    const formData = new URLSearchParams({user_input: userMessage, conversation_mode: conversationMode.checked, response_size: responseSize.value, temperature: temperature.value, user_instructions: customInstructions.value});
    const response = await fetch('/get_response', {method: 'POST', body: formData,}).then(response => response.json());
    chatBox.innerHTML += `<div class="bot-message">${response.response}</div>`;
    chatBox.scrollTop = chatBox.scrollHeight;
});
	
clearButton.addEventListener('click', () => { 
            fetch('/clear_history', {
                method: 'POST'
            })
            .then(response => response.json())
            .then(data => {
                console.log(data.message);
				chatBox.innerHTML = '';

            })
            .catch(error => console.error('Error:', error));
        });

copyButton.addEventListener('click', () => {
    const botMessages = document.querySelectorAll('.bot-message');
    const textToCopy = Array.from(botMessages).map(message => message.textContent).join('\n');   
    const tempTextarea = document.createElement('textarea');
    tempTextarea.value = textToCopy;
    document.body.appendChild(tempTextarea);
    tempTextarea.select();
    document.execCommand('copy');
    document.body.removeChild(tempTextarea);
});



userInput.addEventListener('keydown', event => {
	if (event.key === 'Enter') {
		event.preventDefault(); 
		sendButton.click(); 
	}
});