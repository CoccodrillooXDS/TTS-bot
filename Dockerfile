FROM coccoxds/coccodrillooxds-tts-bot:latest
CMD /bin/sh -c 'cd /ds-tts-bot/ && exec python3 -u bot.py'