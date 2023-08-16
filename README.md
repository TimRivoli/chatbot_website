# chatbot_website
## ✅ Requirements:
pip install flask, openai, tiktoken, uuid
get and API token

## 📚 Description
My sample Chat website using OpenAI GPT backend.  This has become an interesting study in managing conversation history to balance cost, performance, and model comprehension.  The GPT model has zero memory of your prior conversation, so to simulate memory the developer must collect the conversation history (both the user questions and the model responses) and post the whole thing to the model at each turn.  That quickly becomes cumbersome and it confuses the model.

Several issues:
1) as the conversation grows, it consumes memory on the server and money from your pocket, as the API is billed by token (~ 4 letters of each word).
2) passing the whole text of the conversation back and forth, confuses the model.  If I tell it my name is Bob and then ask it what my name is, it can answer the question because that was in the recent history.  If I then ask it about the history of the Roman Empire, the profusion of additional data in the conversation, makes it unable to figure out my name.  Keep in mind, I'm giving it the entire conversation on every turn so it has that information, but it doesn't find it until I specifically ask it to look for the answer in our prior conversation.

So, the conversation history needs to be intelligently managed.  It can be periodically summarized and the summary added to the system message.  I can truncate the assistant's responses, because those are perhaps 1) things the model already knows 2) perhaps less relevant to the ongoing conversation, unless I'm asking it about what it said.  I could also probably do something with vectors to keep track of the gist of the conversation.

I'm using the GPT 3.5 Turbo model, which is a great because GPT 4.0 might be smarter, and if it gets too smart then I don't get to be! 

The official ChatGPT website does this all really well.  Have fun and keep programming!

-Tim
