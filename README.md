<h1 align="center">Text-to-Speech bot for Discord</h1>
<h3 align="center">Speak to your friends in a new way!</h2>
<p><p></p></p>
<p align="center">
<a href="https://python.org/downloads/"><img src="https://img.shields.io/badge/python-3.8%20%7C%203.9%20%7C%203.10-blue?style=for-the-badge&logo=python&logoColor=lightblue&color=red" alt="Python 3.8, 3.9, 3.10">
</a> <a href="https://github.com/CoccodrillooXDS/TTS-bot/releases/latest"><img src="https://img.shields.io/github/v/release/CoccodrillooXDS/TTS-bot?include_prereleases&style=for-the-badge&logo=github" alt="Latest Release"> <a href="https://discord.com/api/oauth2/authorize?client_id=832158681671532564&permissions=8&scope=applications.commands%20bot"><img src="https://img.shields.io/badge/Discord-Add%20bot%20to%20your%20server-yellow?style=for-the-badge&logo=discord&logoColor=lightblue&color=blue" alt="Add bot to your server"></p>


# Table of Contents
- [Table of Contents](#table-of-contents)
- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
  - [Steps](#steps)
  - [Getting your Discord id](#getting-your-discord-id)
  - [Self-hosting](#self-hosting)
  - [Heroku deployment](#heroku-deployment)
- [Contributing](#contributing)
- [License](#license)
- [TODO](#todo)

---
# Overview

TTS is a **Text-to-Speech** bot for Discord. It uses the **[gTTS](https://pypi.org/project/gTTS/)** library to generate audio files from text. The bot then plays the audio file in the voice channel so other people don't have to stop what they are doing to read what you wrote.

---
# Features

* Give your text a voice!
* Read your text aloud!
* Run on any platform!
* Easily self-hostable on any server (even on [Heroku](https://www.heroku.com))!
* Self-updating!
* Easy to use!
* It's free!

---
# Installation

**The officially supported platforms are:**
* Windows
* Most Linux distributions

(It may work on MacOS, but I haven't tested it)

**_Prequisites_**:
* Python 3.8+
* FFmpeg

## Steps

**To run the bot, you will need to do some steps**:

**1. First of all, clone the repository**

```git clone https://github.com/CoccodrillooXDS/TTS-bot.git```

**2. Install the dependencies**

```pip3 install -r requirements.txt``` or ```pip install -r requirements.txt```

**3. Create a Discord bot:**

To create a Discord bot, you will need to create a Discord application. You can do this by going to the [Discord Developer Portal](https://discord.com/developers/applications) and creating a new application.

After creating the application, you will need to create a bot account. You can do this by clicking on the application you created, "**Bot**" section on the left panel and the big blu button "**Add Bot**".

It will ask you if you want to continue, click "**Yes, do it!**".

You will now see a lot of informations and options about your application, you will have to turn all "**Privileged Gateway Intents**" on.

Next up, in the same page, you will have to click on "**Reset Token**"" and confirm the reset. If you have 2FA enabled, you will have to enter your 2FA code.

It will show you a token. Copy it and save it somewhere safe. **You will need this later**.

**4. Configuring System Envirorment Variables**

## Getting your Discord id

To get your Discord User id, refer to the [official Discord support page](https://support.discord.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID-)

## Self-hosting

If you decide to host the bot on your own server, you will have to export the token and your Discord id to a system envirorment variable:

```export TOKEN=<your token>```

```export OWNERID=<your Discord id>```

## Heroku deployment

If you decide to host the bot on Heroku, you will have to set the token and your Discord id in the Heroku environment variables with the CLI or from the web panel, in the "**Config Vars**" section in **Settings**.

**_CLI commands_**

```heroku config:set TOKEN=<your token>```
    
```heroku config:set OWNERID=<your Discord id>```

**5. Start the bot with ```python3 bot.py```**

The bot will automatically search and install updates every 30 minutes (you will soon have an option to change this).

The bot will also create automatically a role called "TTS" in every server you decide to add this bot into. That role is needed to use the bot. You can change the name of the role with /settings.

**6. Finally add the bot to your server**

To add the bot to your server you will need to have the permission to **Manage Server**.
You will be able to add your bot using this link:

```https://discord.com/api/oauth2/authorize?client_id=<your-bot-client-id>&permissions=8&scope=applications.commands%20bot```

**NOTE**: you have to change the ```<your-bot-client-id>``` to your client id. You can get it from the [developer portal](https://discord.com/developers/applications).

---
# Contributing
You can contribute to the project by making a pull request here or by creating an issue.

You can also contribute by translating the bot to your language. Make sure to follow the same format as the English version or the bot might not work as intended.

**Note** Some languages may have problems with the bot.

---
# License
This project is licensed under the [MIT license](LICENSE)


---
# TODO

- [ ] Implement Google Search Engine
- [ ] Implement Google Translate
- [ ] Implement new features!