import asyncio
import configparser
import datetime
import json
import logging
import os
import random
import re
import shutil
import string
import sys
import time
from tokenize import Name
import traceback
import discord
import nest_asyncio
import requests
import ibm_boto3
from ibm_botocore.client import Config, ClientError
from discord.commands import Option
from discord.ext import commands, tasks, bridge
from discord.ui import Button, InputText, Modal, Select, View
from gtts import gTTS, lang
from waiting import wait

nest_asyncio.apply()
if os.name == 'nt':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

intents = discord.Intents.all()

bot = bridge.Bot(
    command_prefix=commands.when_mentioned_or('>'),
    description="A bot to convert text to speech in a voice channel using Google TTS APIs.",
    intents=intents,
    auto_sync_commands=True,
)

bot_version = "v3.1.2"

# --------------------------------------------------
# Folders
# --------------------------------------------------

root = os.path.dirname(os.path.abspath(__file__))
temp = os.path.join(os.path.dirname(os.path.abspath(__file__)),'temp')
configs = os.path.join(os.path.dirname(os.path.abspath(__file__)),'configs')
langfolder = os.path.join(os.path.dirname(os.path.abspath(__file__)),'lang')

# --------------------------------------------------
# Variables
# --------------------------------------------------

supported_languages_message = ""
lang_list = []
allroles = []
installed_langs = []
conf = {'role': 'TTS', 'lang': 'en', 'autosaychan': '[]', 'defvoice': 'en'}
punctuation = ['!', '"', '#', '$', '%', '&', "'", '*', '+', '-', '.', ',', ':', ';', '=', '?', '[', ']', '^', '_', '|', '~']

TOKEN = ""

use_ibm = False

# --------------------------------------------------
# Internal functions
# --------------------------------------------------

async def check_installed_languages():
    global installed_langs
    for lang in os.listdir(langfolder):
        installed_langs.append(lang)

def return_language_string(lang, string):
    global langfolder
    config = configparser.ConfigParser()
    if not os.path.exists(os.path.join(langfolder, lang)):
        print(f"-> Language '{lang}' not found, defaulting to 'en'")
        lang = "en"
    config.read(os.path.join(langfolder, lang))
    try:
        config['DEFAULT']
        config['DEFAULT'][string].isspace()
    except KeyError:
        print(f"-> String '{string}' not found in language '{lang}', defaulting to 'en'")
        lang = "en"
        config.read(os.path.join(langfolder, lang))
        return config['DEFAULT'][string]
    return config['DEFAULT'][string]

def get_guild_language(ctx, string):
    config = configparser.ConfigParser()
    try:
        config.read(os.path.join(configs, str(ctx.guild.id)))
    except:
        config.read(os.path.join(configs, str(ctx.id)))
    return return_language_string(config['DEFAULT']['lang'], string)

def showlangs(ctx: discord.AutocompleteContext):
    global lang_list
    return [lang for lang in lang_list if lang.startswith(ctx.value.lower())]

async def loadroles(bot):
    global allroles
    for guild in bot.guilds:
        config = configparser.ConfigParser()
        config.read(os.path.join(configs, str(guild.id)))
        if not discord.utils.get(guild.roles, name=config['DEFAULT']['role']):
            await guild.create_role(name=config['DEFAULT']['role'])
            print(f"-> Role '{config['DEFAULT']['role']}' created in {guild.name}")
        else:
            print(f"-> Role '{config['DEFAULT']['role']}' found in {guild.name}")
        allroles.append(config['DEFAULT']['role'])
    allroles = list(dict.fromkeys(allroles))

async def resettimer(ctx):
    config = configparser.ConfigParser()
    if os.path.exists(os.path.join(temp, str(ctx.guild.id),'.clock')):
        config.read(os.path.join(temp, str(ctx.guild.id)))
    config['DEFAULT'] = {'time': time.time()}
    with open(os.path.join(temp, str(ctx.guild.id),'.clock'), 'w') as configfile:
        config.write(configfile)

async def check_role(ctx):
    config = configparser.ConfigParser()
    config.read(os.path.join(configs, str(ctx.guild.id)))
    role = discord.utils.get(ctx.guild.roles, name=config['DEFAULT']['role'])
    if role in ctx.author.roles:
        return True
    else:
        config = configparser.ConfigParser()
        config.read(os.path.join(configs, str(ctx.guild.id)))
        embed=discord.Embed(title=eval("f" + get_guild_language(ctx, 'errtitle')), description=eval("f" + get_guild_language(ctx, 'errrole')), color=0xFF0000)
        embed.set_thumbnail(url="https://upload.wikimedia.org/wikipedia/commons/thumb/8/8e/Antu_dialog-error.svg/1024px-Antu_dialog-error.svg.png")
        await ctx.respond(embed=embed, delete_after=5)
        return False

def get_bot_uptime():
    now = datetime.datetime.utcnow()
    delta = now - bot.uptime
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    days, hours = divmod(hours, 24)
    if days:
        fmt = '{d} days, {h} hours, {m} minutes, and {s} seconds'
    else:
        fmt = '{h} hours, {m} minutes, and {s} seconds'
    return fmt.format(d=days, h=hours, m=minutes, s=seconds)

async def ensure_voice(ctx):
    embed=discord.Embed(title=eval(get_guild_language(ctx, 'errtitle')), description=eval(get_guild_language(ctx, 'erruvc')), color=0xff0000)
    embed.set_thumbnail(url="https://upload.wikimedia.org/wikipedia/commons/thumb/8/8e/Antu_dialog-error.svg/1024px-Antu_dialog-error.svg.png")
    if ctx.voice_client is None:
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
            return True
        else:
            await ctx.respond(embed=embed, delete_after=5)
            return False
    else:
        return True

def ran():
        a = ""
        a = ''.join(random.choice(string.ascii_letters + string.digits) for i in range(20))
        return a

def noplay(ctx):
    if ctx.voice_client is None:
        return False
    if ctx.guild.voice_client.is_playing():
        return False
    else:
        return True

# --------------------------------------------------
# IBM Cloud Internal functions
# --------------------------------------------------

def create_bucket():
    global use_ibm, bucket_name
    print(f"Creating a new bucket called: {bucket_name}")
    try:
        cos.Bucket(bucket_name).create(
            CreateBucketConfiguration={
                "LocationConstraint": 'eu-de-flex'
            }
        )
        print(f"Bucket: {bucket_name} created!")
    except ClientError as be:
        print("IBM CLIENT ERROR: {0}\n".format(be))
        use_ibm = False
    except Exception as e:
        print("Unable to create bucket: {0}".format(e))
        use_ibm = False

def get_bucket():
    global bucket_name, use_ibm
    print("Loading buckets...")
    try:
        buckets = cos.buckets.all()
        for bucket in buckets:
            if bucket.name == bucket_name:
                print(f"Bucket: {bucket_name} found!")
                return True
        return False
    except ClientError as be:
        print("IBM CLIENT ERROR: {0}\n".format(be))
        use_ibm = False
    except Exception as e:
        print("Unable to retrieve the list of buckets: {0}".format(e))
        use_ibm = False

def upload_version():
    global bucket_name, root, use_ibm
    upload_version = os.path.join(root, 'version.ini')
    object_name = 'version.ini'
    try:
        cos.Object(bucket_name, object_name).upload_file(upload_version)
    except ClientError as be:
        print("IBM CLIENT ERROR: {0}\n".format(be))
    except Exception as e:
        print("Unable to upload {0}: {1}".format(object_name, e))

def download_version():
    global bucket_name, root, use_ibm
    object_name = 'version.ini'
    download_version = os.path.join(root, 'version.ini')
    try:
        files = cos.Bucket(bucket_name).objects.all()
        for file in files:
            if file.key == object_name:
                cos.Object(bucket_name, object_name).download_file(download_version)
    except ClientError as be:
        print("IBM CLIENT ERROR: {0}\n".format(be))
    except Exception as e:
        print("Unable to download {0}: {1}".format(object_name, e))

def upload_configs():
    global bucket_name, use_ibm, configs
    local_upload_directory = configs
    remote_dir = 'configs'
    for root, dirs, files in os.walk(local_upload_directory):
        for file in files:
            local_file = os.path.join(root, file)
            remote_file = remote_dir + "\\" + file
            try:
                cos.Object(bucket_name, remote_file).upload_file(local_file)
            except ClientError as be:
                print("IBM CLIENT ERROR: {0}\n".format(be))
            except Exception as e:
                print("Unable to upload {0}: {1}".format(remote_file, e))

def download_configs():
    global bucket_name, use_ibm, configs
    remote_dir = 'configs'
    try:
        files = cos.Bucket(bucket_name).objects.all()
        for file in files:
            if file.key.startswith(remote_dir):
                remote_file = file.key
                local_file = os.path.join(configs, file.key[len(remote_dir)+1:])
                cos.Object(bucket_name, file.key).download_file(local_file)
    except ClientError as be:
        print("IBM CLIENT ERROR: {0}\n".format(be))
    except Exception as e:
        print("Unable to download {0}: {1}".format(remote_file, e))

def delete_config(item):
    global bucket_name, use_ibm
    item = f"configs\\{item}"
    try:
        cos.Object(bucket_name, item).delete()
        print(f"Configuration for {item} deleted!")
    except ClientError as be:
        print("IBM CLIENT ERROR: {0}\n".format(be))
    except Exception as e:
        print("Unable to delete object: {0}".format(e))

# --------------------------------------------------
# Languages available
# --------------------------------------------------

@bot.bridge_command(name="langs", description="List all available languages")
async def langs(ctx):
    global supported_languages_message
    """ List all available languages """
    embed=discord.Embed(title=eval("f" + get_guild_language(ctx, 'avlang')), description=supported_languages_message, color=0x37ff00)
    await ctx.respond(embed=embed)

# --------------------------------------------------
# Convert text to speech and play it in the voice channel
# --------------------------------------------------

@bot.command(name="say", description="Convert text to speech", default_permissions=False)
@commands.check(check_role)
async def _say(ctx, *, args=None):
    if await ensure_voice(ctx):
        await ctx.defer()
        author = ctx.author.id
        if not args:
            embed=discord.Embed(title=eval("f" + get_guild_language(ctx, 'errtitle')), description=eval("f" + get_guild_language(ctx, 'errnoarg')), color=0xFF0000)
            await ctx.respond(embed=embed, delete_after=5)
            await ctx.message.delete()
            return False
        lang = args[0:2]
        lang = lang.lower()
        text = args[3:]
        texta = text.lower()
        if not lang in lang_list:
            lang = "en"
        if "gg" in texta and "it" in lang:
            texta = re.sub(r"\bgg\b", "g g", texta)
        texta = "".join(texta)
        tts = gTTS(texta, lang=lang)
        if os.name == 'nt':
            source = f"{temp}\{ctx.guild.id}\{ran()}.mp3"
        else:
            source = f"{temp}/{ctx.guild.id}/{ran()}.mp3"
        tts.save(source)
        wait(lambda: noplay(ctx), timeout_seconds=300)
        source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(source))
        ctx.guild.voice_client.play(source, after=lambda e: print(f'Player error: {e}') if e else None)
        embed=discord.Embed(title=eval("f" + get_guild_language(ctx, 'done')), description=eval("f" + get_guild_language(ctx, 'saylangmess')), color=0x1eff00)
        await ctx.send(embed=embed, delete_after=1)
        await resettimer(ctx)

@bot.slash_command(name="say", description="Convert text to speech", default_permissions=False)
@commands.check(check_role)
async def say(ctx, lang: Option(str, "Choose a language", autocomplete=showlangs), text: Option(str, "Enter text to convert to speech")):
    if await ensure_voice(ctx):
        await ctx.defer()
        author = ctx.author.id
        lang = lang.lower()
        texta = text.lower()
        if not lang in lang_list:
            lang = "en"
        if "gg" in texta and "it" in lang:
            texta = re.sub(r"\bgg\b", "g g", texta)
        texta = "".join(texta)
        tts = gTTS(texta, lang=lang)
        if os.name == 'nt':
            source = f"{temp}\{ctx.guild.id}\{ran()}.mp3"
        else:
            source = f"{temp}/{ctx.guild.id}/{ran()}.mp3"
        tts.save(source)
        wait(lambda: noplay(ctx), timeout_seconds=300)
        source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(source))
        ctx.guild.voice_client.play(source, after=lambda e: print(f'Player error: {e}') if e else None)
        embed=discord.Embed(title=eval("f" + get_guild_language(ctx, 'done')), description=eval("f" + get_guild_language(ctx, 'saylangmess')), color=0x1eff00)
        await ctx.respond(embed=embed, allowed_mentions=discord.AllowedMentions(replied_user=False))
        await resettimer(ctx)

async def hidsay(ctx, lang, text):
    if await ensure_voice(ctx):
        await ctx.defer()
        author = ctx.author.id
        lang = lang.lower()
        texta = text.lower()
        if not lang in lang_list:
            lang = "en"
        if "gg" in texta and "it" in lang:
            texta = re.sub(r"\bgg\b", "g g", texta)
        texta = "".join(texta)
        tts = gTTS(texta, lang=lang)
        if os.name == 'nt':
            source = f"{temp}\{ctx.guild.id}\{ran()}.mp3"
        else:
            source = f"{temp}/{ctx.guild.id}/{ran()}.mp3"
        tts.save(source)
        wait(lambda: noplay(ctx), timeout_seconds=300)
        source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(source))
        ctx.guild.voice_client.play(source, after=lambda e: print(f'Player error: {e}') if e else None)
        embed=discord.Embed(title=eval("f" + get_guild_language(ctx, 'done')), description=eval("f" + get_guild_language(ctx, 'saylangmess')), color=0x1eff00)
        await ctx.respond(embed=embed, allowed_mentions=discord.AllowedMentions(replied_user=False), delete_after=1)
        await resettimer(ctx)

# --------------------------------------------------
# Disconnect the bot from the voice channel
# --------------------------------------------------

@bot.bridge_command(name="stop", description="Disconnect the bot from current channel", default_permissions=False)
@commands.check(check_role)
async def stop(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        embed=discord.Embed(title=eval("f" + get_guild_language(ctx, 'done')), description=eval("f" + get_guild_language(ctx, 'disconnected')), color=0x1eff00)
        await ctx.respond(embed=embed, delete_after=3)
        if ctx.voice_client.is_playing():
            ctx.voice_client.stop()
    else:
        embed=discord.Embed(title=eval("f" + get_guild_language(ctx, 'errtitle')), description=eval("f" + get_guild_language(ctx, 'errnovc')), color=0xFF0000)
        await ctx.respond(embed=embed, delete_after=3)

@bot.bridge_command(name="disconnect", description="Disconnect the bot from current channel", default_permissions=False)
@commands.check(check_role)
async def disconnect(ctx):
    await stop(ctx)

# --------------------------------------------------
# Help command
# --------------------------------------------------

class Help(commands.HelpCommand):
    async def send_bot_help(self, mapping):
        allhelp = f"{eval(get_guild_language(self.context, 'helpprefix'))}\n{eval(get_guild_language(self.context, 'helpsay'))}\n{eval(get_guild_language(self.context, 'helplangs'))}\n{eval(get_guild_language(self.context, 'helpsettings'))}\n{eval(get_guild_language(self.context, 'helpstop'))}\n{eval(get_guild_language(self.context, 'helpabout'))}\n{eval(get_guild_language(self.context, 'helphelp'))}"
        embed=discord.Embed(title=eval("f" + get_guild_language(self.context, 'helptitle')), description=allhelp, color=0x1eff00)
        await self.context.respond(embed=embed)
       
    async def send_command_help(self, command):
        command = eval(get_guild_language(self.context, f'help{command}'))
        embed=discord.Embed(title=eval("f" + get_guild_language(self.context, 'helptitle')), description=command, color=0x1eff00)
        await self.context.respond(embed=embed)
      
    async def send_group_help(self, group):
        allhelp = f"{eval(get_guild_language(self.context, 'helpprefix'))}\n{eval(get_guild_language(self.context, 'helpsay'))}\n{eval(get_guild_language(self.context, 'helplangs'))}\n{eval(get_guild_language(self.context, 'helpsettings'))}\n{eval(get_guild_language(self.context, 'helpstop'))}\n{eval(get_guild_language(self.context, 'helpabout'))}\n{eval(get_guild_language(self.context, 'helphelp'))}"
        embed=discord.Embed(title=eval("f" + get_guild_language(self.context, 'helptitle')), description=allhelp, color=0x1eff00)
        await self.context.respond(embed=embed)
    
    async def send_cog_help(self, cog):
        allhelp = f"{eval(get_guild_language(self.context, 'helpprefix'))}\n{eval(get_guild_language(self.context, 'helpsay'))}\n{eval(get_guild_language(self.context, 'helplangs'))}\n{eval(get_guild_language(self.context, 'helpsettings'))}\n{eval(get_guild_language(self.context, 'helpstop'))}\n{eval(get_guild_language(self.context, 'helpabout'))}\n{eval(get_guild_language(self.context, 'helphelp'))}"
        embed=discord.Embed(title=eval("f" + get_guild_language(self.context, 'helptitle')), description=allhelp, color=0x1eff00)
        await self.context.respond(embed=embed)

@bot.slash_command(name="help", description="Get help with the bot")
async def help(ctx):
    allhelp = f"{eval(get_guild_language(ctx, 'helpprefix'))}\n{eval(get_guild_language(ctx, 'helpsay'))}\n{eval(get_guild_language(ctx, 'helplangs'))}\n{eval(get_guild_language(ctx, 'helpsettings'))}\n{eval(get_guild_language(ctx, 'helpstop'))}\n{eval(get_guild_language(ctx, 'helpabout'))}\n{eval(get_guild_language(ctx, 'helphelp'))}"
    embed=discord.Embed(title=eval("f" + get_guild_language(ctx, 'helptitle')), description=allhelp, color=0x1eff00)
    await ctx.respond(embed=embed)

# --------------------------------------------------
# About command
# --------------------------------------------------

@bot.bridge_command(name="about", description="About the bot")
async def about(ctx):
    global bot_version, punctuation
    punct = ' '.join(map(str, punctuation))
    embed=discord.Embed(title=eval("f" + get_guild_language(ctx, 'abouttitle')), description=eval("f" + get_guild_language(ctx, 'aboutdesc')), color=0x1eff00)
    await ctx.respond(embed=embed)

# --------------------------------------------------
# Settings command
# --------------------------------------------------

class setrole(Modal):
    def __init__(self, ctx, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.add_item(InputText(custom_id="role", label=eval("f" + get_guild_language(ctx, 'changerolemodal')), placeholder="TTS", value=""))
    async def callback(self, interaction: discord.Interaction):
        role = discord.utils.get(interaction.guild.roles, name=self.children[0].value)
        config = configparser.ConfigParser()
        config.read(os.path.join(configs, str(interaction.guild.id)))
        if not role:
            role = await interaction.guild.create_role(name=self.children[0].value)
        await interaction.user.add_roles(role)
        config['DEFAULT']['role'] = self.children[0].value
        with open(os.path.join(configs, str(interaction.guild.id)), 'w') as configfile:
            config.write(configfile)
        upload_configs()
        embed=discord.Embed(title=eval("f" + get_guild_language(interaction, 'done')), description=eval("f" + get_guild_language(interaction, 'rolechange')), color=0x1eff00)
        await interaction.response.send_message(embed=embed, delete_after=3, ephemeral=True)

@bot.bridge_command(name="settings", description="Edit bot configuration", default_permissions=False)
@commands.check(check_role)
async def settings(ctx):
    context = ctx
    await ctx.defer()
    await _settings(ctx, context)

@bot.bridge_command(name="config", description="Edit bot configuration", default_permissions=False)
@commands.check(check_role)
async def config(ctx):
    context = ctx
    await ctx.defer()
    await _settings(ctx, context)

async def _settings(ctx, context):
    global lang_list
    config = configparser.ConfigParser()
    config.read(os.path.join(configs, str(ctx.guild.id)))
    aj = json.loads(config["DEFAULT"]["autosaychan"])
    asc = ""
    for i in aj:
        asc += f"<#{i}>, "
    embed=discord.Embed(title=eval("f" + get_guild_language(ctx, 'currsettingstitle')), description=eval("f" + get_guild_language(ctx, 'currsettings')), color=0x1eff00)
    buttonclose = Button(custom_id="close", label=eval("f" + get_guild_language(ctx, 'close')), style=discord.ButtonStyle.danger)
    buttonchangelanguage = Button(custom_id="cl", label=eval("f" + get_guild_language(ctx, 'changelang')), style=discord.ButtonStyle.secondary, emoji="🏴‍☠️")
    buttonchangerole = Button(custom_id="cr", label=eval("f" + get_guild_language(ctx, 'changerole')), style=discord.ButtonStyle.secondary, emoji="🏷️")
    buttondefvoice = Button(custom_id="cdv", label=eval("f" + get_guild_language(ctx, 'changedefaultvoice')), style=discord.ButtonStyle.secondary, emoji="🗣️")
    buttonautosaychan = Button(custom_id="casc", label=eval("f" + get_guild_language(ctx, 'changeautosaychannel')), style=discord.ButtonStyle.secondary, emoji="#️⃣")
    view = View()
    view.add_item(buttonchangerole)
    view.add_item(buttonchangelanguage)
    view.add_item(buttondefvoice)
    view.add_item(buttonautosaychan)
    view.add_item(buttonclose)
    await ctx.respond(embed=embed, view=view, delete_after=20)
    async def defvoice(ctx):
        config.read(os.path.join(configs, str(ctx.guild.id)))
        dv = config['DEFAULT']['defvoice']
        embed=discord.Embed(title=eval("f" + get_guild_language(ctx, 'changedefaultvoice')), description=eval("f" + get_guild_language(ctx, 'changedefaultvoicedesc')), color=0x1eff00)
        options1 = []
        options2 = []
        options3 = []
        options4 = []
        for i in lang_list:
            if len(options1) < 25:
                options1.append(discord.SelectOption(label=i, value=i))
            elif len(options1) == 25 and len(options2) < 25:
                options2.append(discord.SelectOption(label=i, value=i))
            elif len(options1) == 25 and len(options2) == 25 and len(options3) < 25:
                options3.append(discord.SelectOption(label=i, value=i))
            elif len(options1) == 25 and len(options2) == 25 and len(options3) == 25 and len(options4) < 25:
                options4.append(discord.SelectOption(label=i, value=i))
        view = View()
        async def callback(ctx):
            try:
                if select.values:
                    config.set('DEFAULT', 'defvoice', select.values[0])
            except IndexError:
                config.set('DEFAULT', 'defvoice', dv)
            except NameError:
                pass
            try:
                if select2.values:
                    config.set('DEFAULT', 'defvoice', select2.values[0])
            except IndexError:
                config.set('DEFAULT', 'defvoice', dv)
            except NameError:
                pass
            try:
                if select3.values:
                    config.set('DEFAULT', 'defvoice', select3.values[0])
            except IndexError:
                config.set('DEFAULT', 'defvoice', dv)
            except NameError:
                pass
            try:
                if select4.values:
                    config.set('DEFAULT', 'defvoice', select4.values[0])
            except IndexError:
                config.set('DEFAULT', 'defvoice', dv)
            except NameError:
                pass
            with open(os.path.join(configs, str(ctx.guild.id)), 'w') as configfile:
                config.write(configfile)
            if use_ibm:
                upload_configs()
            embed=discord.Embed(title=eval("f" + get_guild_language(ctx, 'done')), color=0x1eff00)
            await ctx.message.delete()
            await ctx.response.send_message(embed=embed, delete_after=1)
            await _settings(context, context)
        if len(options1) > 0:
            select = Select(custom_id="defvoice", max_values=1, options=options1)
            view.add_item(select)
            select.callback = callback
        if len(options2) > 0:
            select2 = Select(custom_id="defvoice2", max_values=1, options=options2)
            view.add_item(select2)
            select2.callback = callback
        if len(options3) > 0:
            select3 = Select(custom_id="defvoice3", max_values=1, options=options3)
            view.add_item(select3)
            select3.callback = callback
        if len(options4) > 0:
            select4 = Select(custom_id="defvoice4", max_values=1, options=options4)
            view.add_item(select4)
            select4.callback = callback
        await ctx.message.delete()
        await ctx.response.send_message(embed=embed, view=view)
    buttondefvoice.callback = defvoice
    async def autosaychan(ctx):
        config.read(os.path.join(configs, str(ctx.guild.id)))
        ascj = json.loads(config['DEFAULT']['autosaychan'])
        embed=discord.Embed(title=eval("f" + get_guild_language(ctx, 'changeautosaychannel')), color=0x1eff00)
        options = []
        options2 = []
        options3 = []
        optsel = []
        optsel2 = []
        optsel3 = []
        for i in ctx.guild.text_channels:
            if len(options) < 25:
                if int(i.id) in ascj:
                    options.append(discord.SelectOption(label=i.name, value=str(i.id), default=True))
                    optsel.append(i.id)
                else:
                    options.append(discord.SelectOption(label=i.name, value=str(i.id)))
            elif len(options) == 25 and len(options2) < 25:
                if int(i.id) in ascj:
                    options2.append(discord.SelectOption(label=i.name, value=str(i.id), default=True))
                    optsel2.append(i.id)
                else:
                    options2.append(discord.SelectOption(label=i.name, value=str(i.id)))
            elif len(options) == 25 and len(options2) == 25 and len(options3) < 25:
                if int(i.id) in ascj:
                    options3.append(discord.SelectOption(label=i.name, value=str(i.id), default=True))
                    optsel3.append(i.id)
                else:
                    options3.append(discord.SelectOption(label=i.name, value=str(i.id)))
        lo1 = len(options)
        lo2 = len(options2)
        lo3 = len(options3)
        async def onlysel(ctx):
            try:
                await ctx.response.send_message(" ", ephemeral=True, delete_after=0)
            except:
                pass
        view = View()
        if lo1 > 25:
            lo1 = 25
        if not lo1 == 0:
            select = Select(custom_id="autosaychan", min_values=0, max_values=lo1, options=options)
            view.add_item(select)
            select.callback = onlysel
        if lo2 > 25:
            lo2 = 25
        if not lo2 == 0:
            select2 = Select(custom_id="autosaychan2", min_values=0, max_values=lo2, options=options2)
            view.add_item(select2)
            select2.callback = onlysel
        if lo3 > 25:
            lo3 = 25
        if not lo3 == 0:
            select3 = Select(custom_id="autosaychan3", min_values=0, max_values=lo3, options=options3)
            view.add_item(select3)
            select3.callback = onlysel
        buttonapply = Button(custom_id="apply", label=eval("f" + get_guild_language(ctx, 'apply')), style=discord.ButtonStyle.primary, emoji="✅")
        if optsel == [] and optsel2 == [] and optsel3 == []:
            buttondisable = Button(custom_id="disable", disabled=True, label=eval("f" + get_guild_language(ctx, 'disable')), style=discord.ButtonStyle.danger)
        else:
            buttondisable = Button(custom_id="disable", label=eval("f" + get_guild_language(ctx, 'disable')), style=discord.ButtonStyle.danger)
        view.add_item(buttonapply)
        view.add_item(buttondisable)
        await ctx.message.delete()
        await ctx.response.send_message(embed=embed, view=view)
        async def callback(ctx):
            channels = []
            try:
                for channel in select.values:
                    channels.append(int(channel))
                if not select.values:
                    channels.extend(optsel)
            except NameError:
                pass
            try:
                for channel in select2.values:
                    channels.append(int(channel))
                if not select2.values:
                    channels.extend(optsel2)
            except NameError:
                pass
            try:
                for channel in select3.values:
                    channels.append(int(channel))
                if not select3.values:
                    channels.extend(optsel3)
            except NameError:
                pass
            config.set('DEFAULT', 'autosaychan', str(channels))
            with open(os.path.join(configs, str(ctx.guild.id)), 'w') as configfile:
                config.write(configfile)
            if use_ibm:
                upload_configs()
            embed=discord.Embed(title=eval("f" + get_guild_language(ctx, 'done')), color=0x1eff00)
            await ctx.message.delete()
            await ctx.response.send_message(embed=embed, delete_after=1)
            await _settings(context, context)
        buttonapply.callback = callback
        async def disable(ctx):
            channels = []
            config.set('DEFAULT', 'autosaychan', str(channels))
            with open(os.path.join(configs, str(ctx.guild.id)), 'w') as configfile:
                config.write(configfile)
            if use_ibm:
                upload_configs()
            embed=discord.Embed(title=eval("f" + get_guild_language(ctx, 'disabledautosay')), color=0xe32222)
            await ctx.message.delete()
            await ctx.response.send_message(embed=embed, delete_after=3)
            await asyncio.sleep(2)
            await _settings(context, context)
        buttondisable.callback = disable
        await view.wait()
    buttonautosaychan.callback = autosaychan
    async def close(ctx):
        await ctx.message.delete()
    buttonclose.callback = close
    async def changerole(ctx):
        await ctx.message.delete()
        modal = setrole(ctx, title=eval("f" + get_guild_language(ctx, 'changerole')))
        await ctx.response.send_modal(modal)
        await _settings(context, context)
    buttonchangerole.callback = changerole
    async def changelanguage(ctx):
        global installed_langs
        language = config["DEFAULT"]["lang"]
        embed=discord.Embed(title=eval("f" + get_guild_language(ctx, 'changelang')), description=eval("f" + get_guild_language(ctx, 'changelangdrop')), color=0x1eff00)
        options = []
        for i in installed_langs:
            options.append(discord.SelectOption(label=i, value=i))
        select = Select(custom_id="selecta", max_values=1, placeholder=language, options=options)
        view = View()
        view.add_item(select)
        await ctx.message.delete()
        await ctx.response.send_message(embed=embed, view=view, ephemeral=True)
        async def callback(ctx):
            try:
                config.set('DEFAULT', 'lang', select.values[0])
            except IndexError:
                config.set('DEFAULT', 'lang', language)
            with open(os.path.join(configs, str(ctx.guild.id)), 'w') as configfile:
                config.write(configfile)
            embed=discord.Embed(title=eval("f" + get_guild_language(ctx, 'done')), description=eval("f" + get_guild_language(ctx, 'changedlang')), color=0x1eff00)
            await ctx.response.edit_message(embed=embed, view=None)
            if use_ibm:
                upload_configs()
            await _settings(context, context)
        select.callback = callback
    buttonchangelanguage.callback = changelanguage

# --------------------------------------------------
# Tasks
# --------------------------------------------------

@tasks.loop(seconds=120)
async def delete_mp3():
    for root, dirs, files in os.walk(temp):
        for file in files:
            if file.endswith(".mp3"):
                try:
                    os.remove(os.path.join(root, file))
                except PermissionError:
                    pass


@tasks.loop(seconds=1800)
async def check_update():
    try:
        r = requests.get('https://api.github.com/repos/CoccodrillooXDS/TTS-bot/releases/latest')
        if r.status_code == 200:
            with open(os.path.join(root, 'version.ini'), 'r') as f:
                    version = f.read()
            if int(version) > r.json()['id'] and bot_version != r.json()['tag_name']:
                print(f"-> Bot version ({bot_version}) is newer than the latest version ({r.json()['tag_name']})")
                return
            if bot_version != r.json()['tag_name'] and int(version) == r.json()['id']:
                print(f"-> Bot version ({bot_version}) is newer than the latest version ({r.json()['tag_name']})")
                return
            if r.json()['tag_name'] != bot_version:
                print(f"-> New version {r.json()['tag_name']} available!")
            if int(version) != r.json()['id'] and bot_version == r.json()['tag_name']:
                changelog = r.json()['body']
                id = r.json()['id']
                with open(os.path.join(root,'version.ini'), 'w') as versionfile:
                    versionfile.write(str(id))
                if use_ibm:
                    upload_version()
                print(f"-> A new version ({bot_version}) has been installed successfully!")
                for guild in bot.guilds:
                    ctx = guild
                    embed=discord.Embed(title=eval("f" + get_guild_language(ctx, 'updatetitle')), description=eval("f" + get_guild_language(ctx, 'updatedesc')), color=0x286fad)
                    try:
                        await guild.get_channel(guild.system_channel.id).send(embed=embed)
                    except AttributeError:
                        for channel in guild.text_channels:
                            if channel.permissions_for(guild.me).send_messages:
                                await channel.send(embed=embed)
                                break
        elif r.status_code == 403:
            print("-> Unable to check for bot updates! We have been rate limited by GitHub, checking for updates later...")
    except Exception as e:
        print("-> Unable to check for bot updates!")
        print(logging.error(traceback.format_exc()))

@tasks.loop(seconds=300)
async def check_timer(bot):
    for guild in bot.guilds:
        config = configparser.ConfigParser()
        if os.path.exists(os.path.join(temp, str(guild.id),'.clock')):
            config.read(os.path.join(temp, str(guild.id),'.clock'))
            if time.time() - float(config['DEFAULT']['time']) >= 240:
                try:
                    await guild.voice_client.disconnect()
                    print(f"-> Disconnected for inactivity from '{guild.name}'")
                except AttributeError:
                    pass
                os.remove(os.path.join(temp, str(guild.id),'.clock'))
        else:
            continue

# --------------------------------------------------
# Bot events
# --------------------------------------------------

@bot.event
async def on_ready():
    global supported_languages_message, lang_list, use_ibm, conf
    n = 5
    an = 1
    print(f"{bot.user} is finishing up loading...")
    guilds = []
    for guild in bot.guilds:
        guilds.append(f"{guild.id}")
    if use_ibm:
        print(f"Getting bucket infos from IBM...")
        if not get_bucket():
            if use_ibm:
                create_bucket()
            else:
                print(f"-> IBM credentials are invalid, skipping sync...")
    print(f"Checking for updates... (Step {str(an)}/{str(n)})")
    if use_ibm:
        download_version()
    if not os.path.exists(os.path.join(root,'version.ini')):
        with open(os.path.join(root,'version.ini'), 'w') as f:
            f.write("0")
    else:
        with open(os.path.join(root,'version.ini'), 'r') as f:
            if f.read() == "":
                with open(os.path.join(root,'version.ini'), 'w') as f:
                    f.write("0")
    if use_ibm:
        upload_version()
    check_update.start()
    langs = lang.tts_langs()
    for i in langs:
        if "zh-CN" in i:
            continue
        if "zh-TW" in i:
            continue
        supported_languages_message += f"{langs[i]} -> {i}\n"
        lang_list.append(i)
    await check_installed_languages()
    print(f"Internal updates completed (Step {str(an)}/{str(n)})")
    an += 1
    print(f"Cleaning cache... (Step {str(an)}/{str(n)})")
    if os.path.exists(temp):
            shutil.rmtree(temp)
    print(f"Cache cleaned (Step {str(an)}/{str(n)})")
    an += 1
    print(f"Creating directories... (Step {str(an)}/{str(n)})")
    os.makedirs(temp)
    for guild in guilds:
        new_fold = os.path.join(temp, guild)
        os.mkdir(new_fold)
    if not os.path.exists(configs):
        os.makedirs(configs)
    print(f"Directories created (Step {str(an)}/{str(n)})")
    an += 1
    print(f"Loading guild configs... (Step {str(an)}/{str(n)})")
    if use_ibm:
        download_configs()
    for guild in bot.guilds:
        if not os.path.exists(os.path.join(configs, str(guild.id))):
            config = configparser.ConfigParser()
            config['DEFAULT'] = conf
            with open(os.path.join(configs, str(guild.id)), 'w') as configfile:
                config.write(configfile)
        else:
            config = configparser.ConfigParser()
            config.read(os.path.join(configs, str(guild.id)))
            if not "DEFAULT" in config:
                config['DEFAULT'] = conf
                with open(os.path.join(configs, str(guild.id)), 'w') as configfile:
                    config.write(configfile)
            for key in conf:
                if not key in config['DEFAULT']:
                    config['DEFAULT'][key] = conf[key]
                with open(os.path.join(configs, str(guild.id)), 'w') as configfile:
                    config.write(configfile)
    if use_ibm:
        upload_configs()
    print(f"Guild configs loaded (Step {str(an)}/{str(n)})")
    an += 1
    print(f"Checking if all servers have the role specified in config... (Step {str(an)}/{str(n)})")
    await loadroles(bot)
    print(f"All servers have the specified role (Step {str(an)}/{str(n)})")
    await bot.change_presence(activity=discord.Game(name=f"/help | {len(bot.guilds)} servers"))
    bot.uptime = datetime.datetime.utcnow()
    print(f"{bot.user} has finished up loading!")
    check_timer.start(bot)
    delete_mp3.start()

@bot.event
async def on_message(message):
    global configs, lang_list, punctuation
    config = configparser.ConfigParser()
    if message.author.id == bot.user.id:
        return
    config.read(os.path.join(configs, str(message.guild.id)))
    ctx = await bot.get_context(message)
    a = json.loads(config['DEFAULT']['autosaychan'])
    if int(message.channel.id) in a:
        if message.content.startswith('>'):
            await bot.process_commands(message)
            return
        voice = config['DEFAULT']['defvoice']
        if message.content.startswith(tuple(punctuation)):
            voice = message.content[1:3]
            message = message.content[3:]
        else:
            message = message.content
        await hidsay(ctx, lang=voice, text=message)
    else:
        await bot.process_commands(message)

@bot.event
async def on_guild_join(guild):
    global configs, temp, conf
    embed=discord.Embed(title=f"{guild.name}", description=f"**Hi!**\nThank you for adding me to '_**{guild.name}**_'!\nI automatically created a role called '**TTS**' that allows the users to use this bot.\n\n**WARNING**: Without this role you **CAN'T** use the bot.\n\nYou can change the role name and the bot language with the **`/settings`** command", color=0x286fad)
    try:
        await guild.get_channel(guild.system_channel.id).send(embed=embed)
    except AttributeError:
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                await channel.send(embed=embed)
                break
    new_fold = os.path.join(temp, str(guild.id))
    os.mkdir(new_fold)
    if not discord.utils.get(guild.roles, name="TTS"):
        await guild.create_role(name="TTS")
    if not os.path.exists(os.path.join(configs, str(guild.id))):
        config = configparser.ConfigParser()
        config['DEFAULT'] = conf
        with open(os.path.join(configs, str(guild.id)), 'w') as configfile:
            config.write(configfile)
    print(f"New guild joined: {guild.name} ({guild.id})")
    await bot.change_presence(activity=discord.Game(name=f"/help | {len(bot.guilds)} servers"))
    print(f"-> Role 'TTS' created in {guild.name}")
    if use_ibm:
        upload_configs()

@bot.event
async def on_guild_remove(guild):
    global configs, temp
    shutil.rmtree(os.path.join(temp, str(guild.id)))
    os.remove(os.path.join(configs, str(guild.id)))
    await bot.change_presence(activity=discord.Game(name=f"/help | {len(bot.guilds)} servers"))
    if use_ibm:
        delete_config(str(guild.id))
    print(f"{guild.name} ({guild.id}) removed")

@bot.event
async def on_voice_state_update(member, before, after):
    voice_state = member.guild.voice_client
    if member.id == bot.user.id:
        if member.voice != None:
            try:
                await member.edit(deafen=True, mute=False)
            except:
                pass    
    if voice_state is None:
        try:
            os.remove(os.path.join(temp, str(member.guild.id),'.clock'))
        except FileNotFoundError:
            pass
    elif len(voice_state.channel.members) == 1:
        await voice_state.disconnect()
    return


# --------------------------------------------------
# Start process
# --------------------------------------------------

if os.environ.get('TOKEN') is None:
    print("Bot TOKEN not found. You can get one by creating a bot from https://discord.com/developers/applications/. Please set the TOKEN environment variable.")
    exit()
else:
    TOKEN = os.environ.get('TOKEN')

if os.environ.get('COS_ENDPOINT') is None or os.environ.get('COS_API_KEY_ID') is None or os.environ.get('COS_INSTANCE_CRN') is None:
    print("COS_ENDPOINT, COS_API_KEY_ID or COS_INSTANCE_CRN not found in environment variables")
    print("You have to set them to use the IBM Cloud Object Storage.")
    print("You can get them from https://cloud.ibm.com/docs/cloud-object-storage/getting-started.html")
    print("NOTE: If you use Heroku to host this bot, you need to set these variables because Heroku will REMOVE ALL DATA (including Server Configurations) on bot restart.")
    use_ibm = False
else:
    use_ibm = True
    COS_ENDPOINT = os.environ.get('COS_ENDPOINT')
    COS_API_KEY_ID = os.environ.get('COS_API_KEY_ID')
    COS_INSTANCE_CRN = os.environ.get('COS_INSTANCE_CRN')
    bucket_name = "tts-bot-data"
    cos = ibm_boto3.resource("s3", ibm_api_key_id=COS_API_KEY_ID, ibm_service_instance_id=COS_INSTANCE_CRN, config=Config(signature_version="oauth"), endpoint_url=COS_ENDPOINT)

bot.help_command = Help()

bot.run(TOKEN)