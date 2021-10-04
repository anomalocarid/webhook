This is a simple Python application to scrape reddit and RSS feeds and post
the entries to a Discord webhook. It supports simple filtering capabilities
to restrict what gets posted based on a combination of regular expressions
as well.

# Config File

For now, the config file format is documented in the [JSON Schema](https://json-schema.org/) format
in the file [schema.json](https://github.com/anomalocarid/webhook/blob/main/schema.json).

# Running

Once you have created a `config.json` file, on the command line run
```
python webhook.py
```
to start the application. Just kill the main process (Ctrl+C) to stop it.
For now, it will print which posts are filtered or posted. I plan on adding more logging capabilities
to improve debugging in the future.
