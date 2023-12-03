<div align="center">
  <br>
  <a href="">
    <img src="res/github/ollama-telegram-readme.png" width="200" height="200">
  </a>
  <h1>🦙 Ollama Telegram Bot</h1>
  <p>
    <b>Chat with your LLM, using Telegram bot!</b><br>
    <b>🚧 Project is still WIP 🚧</b><br>
    <b>Feel free to contribute!</b><br>
  </p>
  <br>
  <p align="center">
    <img src="https://img.shields.io/github/downloads/ruecat/ollama-telegram/total?style=for-the-badge&label=GitHub Downloads&color=52489C">
    <img src="https://img.shields.io/docker/pulls/ruecat/ollama-aiogram?style=for-the-badge">
  </p>
  <br>
</div>

## Features
Here's features that you get out of the box:

- [x] Fully dockerized bot
- [x] Response streaming without ratelimit with **SentenceBySentence** method
- [x] Mention [@] bot in group to receive answer

## Roadmap
- [ ] Proper Docker Config (Broken at the moment)
- [ ] Implement **history** [Bot can't remember more that 1 prompt]
- [ ] Add more API-related functions
- [ ] Redis DB integration

## Prerequisites
- [Telegram-Bot Token](https://core.telegram.org/bots#6-botfather)

## Installation (Non-Docker)
+ Install latest [Python](https://python.org/downloads)
+ Clone Repository
```
git clone https://github.com/ruecat/ollama-telegram
```
+ Install requirements from requirements.txt
```
pip install -r requirements.txt
```
+ Enter all values in .env.example

+ Rename .env.example -> .env

+ Launch bot

```
python3 ollama-run.py
```
## Installation (Docker)
Soon..

## Environment Configuration
|  Parameter  |                                                      Description                                                      | Required? | Default Value |                        Example                        |
|:-----------:|:---------------------------------------------------------------------------------------------------------------------:|:---------:|:-------------:|:-----------------------------------------------------:|
|   `TOKEN`   | Your **Telegram bot token**.<br/>[[How to get token?]](https://core.telegram.org/bots/tutorial#obtain-your-bot-token) |    Yes    |  `yourtoken`  |             MTA0M****.GY5L5F.****g*****5k             |
| `ADMIN_IDS` |                     Telegram user IDs of admins.<br/>These can change model and control the bot.                      |    Yes    |               | 1234567890<br/>**OR**<br/>1234567890,0987654321, etc. |
| `USER_IDS`  |                       Telegram user IDs of regular users.<br/>These only can chat with the bot.                       |    Yes    |               | 1234567890<br/>**OR**<br/>1234567890,0987654321, etc. |
| `INITMODEL` |                                                      Default LLM                                                      |    No     |   `llama2`    |        mistral:latest<br/>mistral:7b-instruct         |

## Credits
+ [Ollama](https://github.com/jmorganca/ollama)

## Libraries used
+ [Aiogram 3.x](https://github.com/aiogram/aiogram)
