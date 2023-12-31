<div align="center">
  <br>
  <a href="">
    <img src="res/github/ollama-telegram-readme.png" width="200" height="200">
  </a>
  <h1>🦙 Ollama Telegram Bot</h1>
  <p>
    <b>Chat with your LLM, using Telegram bot!</b><br>
    <b>Feel free to contribute!</b><br>
  </p>
</div>

## Features
Here's features that you get out of the box:

- [x] Fully dockerized bot
- [x] Response streaming without ratelimit with **SentenceBySentence** method
- [x] Mention [@] bot in group to receive answer

## Roadmap
- [x] Docker Config by [StanleyOneG](https://github.com/StanleyOneG)
- [x] History and `/reset` by [ShrirajHegde](https://github.com/ShrirajHegde)
- [ ] Add more API-related functions [System Prompt Editor, Ollama Version fetcher, etc.]
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
python3 run.py
```
## Installation (Docker-Compose)
+ Clone Repository
```
git clone https://github.com/ruecat/ollama-telegram
```

+ Enter all values in .env.example

+ Rename .env.example -> .env

+ Run ONE of the following docker compose commands to start:
    1. To run ollama in docker container (optionally: uncomment GPU part of docker-compose.yml file to enable Nvidia GPU)
    ```
    docker compose up --build -d
    ```

    2. To run ollama from locally installed instance (mainly for **MacOS**, since docker image doesn't support Apple GPU acceleration yet):
    ```
    docker compose up --build -d ollama-telegram
    ```

## Environment Configuration
|     Parameter     |                                                      Description                                                      | Required? | Default Value |                        Example                        |
|:-----------------:|:---------------------------------------------------------------------------------------------------------------------:|:---------:|:-------------:|:-----------------------------------------------------:|
|      `TOKEN`      | Your **Telegram bot token**.<br/>[[How to get token?]](https://core.telegram.org/bots/tutorial#obtain-your-bot-token) |    Yes    |  `yourtoken`  |             MTA0M****.GY5L5F.****g*****5k             |
|    `ADMIN_IDS`    |                     Telegram user IDs of admins.<br/>These can change model and control the bot.                      |    Yes    |               | 1234567890<br/>**OR**<br/>1234567890,0987654321, etc. |
|    `USER_IDS`     |                       Telegram user IDs of regular users.<br/>These only can chat with the bot.                       |    Yes    |               | 1234567890<br/>**OR**<br/>1234567890,0987654321, etc. |
|    `INITMODEL`    |                                                      Default LLM                                                      |    No     |   `llama2`    |        mistral:latest<br/>mistral:7b-instruct         |
| `OLLAMA_BASE_URL` |                                                  Your OllamaAPI URL                                                   |    No     |               |          localhost<br/>host.docker.internal           |


## Credits
+ [Ollama](https://github.com/jmorganca/ollama)

## Libraries used
+ [Aiogram 3.x](https://github.com/aiogram/aiogram)
