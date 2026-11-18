# Rass Derb Cup Discord Bot

Modular `discord.py` bot foundation for the Rass Derb Cup and Esports PUBG
MOBILE MEA community. The first feature is an admin-only `/embed` command for
posting validated custom JSON messages.

## Run

1. Add the Discord bot token as a Replit Secret named `TOKEN`. The bot reads it
   from the environment and never stores it in source files.
2. In the Discord Developer Portal, enable **Message Content Intent** for the
   application. This code enables that privileged intent.
3. Invite the bot to your server with the `bot` and `applications.commands`
   scopes. Grant it View Channel, Send Messages, and Embed Links permissions in
   channels where it will post.
4. Start the **Rass Derb Cup Discord Bot** workflow.

The bot syncs slash commands globally by default. To make commands appear
immediately in one development server, set the non-secret `GUILD_ID` environment
variable to that server's numeric ID before starting the workflow.

## `/embed`

Use `/embed` with a JSON object and optionally choose a destination text channel.
If no channel is selected, it posts in the current channel. The command is
restricted to members with Manage Server permission. Mentions are disabled for
the sent message to prevent accidental mass pings.

Example:

```json
{
  "content": "The Rass Derb Cup is live!",
  "embeds": [
    {
      "title": "Match day",
      "description": "Follow the PUBG MOBILE MEA tournament.",
      "color": "#2E86DE",
      "fields": [
        { "name": "Stage", "value": "Finals", "inline": true },
        { "name": "Status", "value": "Live", "inline": true }
      ],
      "footer": { "text": "Rass Derb Cup" },
      "image": { "url": "https://example.com/animated-banner.gif" }
    }
  ]
}
```

For a single embed, top-level `title`, `description`, `color`, `fields`,
`footer`, `author`, `image`, `image_url`, `thumbnail`, `url`, or `timestamp`
fields are also accepted. Colors can be integers or six-digit hex strings.
Image URLs must use `http` or `https`; GIF URLs are supported.

## Project layout

- `rass_derb_bot/bot.py` — intents, extension loading, command sync, and the
  persistent-view registration hook for future interactive modules.
- `rass_derb_bot/cogs/` — one Discord command module per feature.
- `rass_derb_bot/services/` — reusable validation and business logic.
- `tests/` — standard-library unit tests.

Add upcoming commands as separate cogs and register them in
`RassDerbBot.EXTENSIONS`. Persistent button views should use `timeout=None` and
be registered through `register_persistent_view` so `Client.add_view()` restores
them after restarts.

## Checks

Run the parser tests with:

```sh
python -m unittest discover -s tests -v
```
