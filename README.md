# Rass Derb Cup Discord Bot

Modular `discord.py` bot foundation for the Rass Derb Cup and Esports PUBG
MOBILE MEA community. The first feature is an admin-only `/embed` command for
posting validated custom JSON messages.

## Run

1. Keep the Discord bot token in the Replit Secret named `TOKEN`. The bot reads
   it from the environment and never stores it in source files.
2. Keep the project PostgreSQL connection in `DATABASE_URL`; form definitions
   and persistent button records are stored there.
3. In the Discord Developer Portal, enable **Message Content Intent** for the
   application. This code enables that privileged intent.
4. Invite the bot to each server with the `bot` and `applications.commands`
   scopes. Grant it View Channel, Send Messages, and Embed Links permissions in
   channels where it will post.
5. Start the **Rass Derb Cup Discord Bot** workflow.

The bot syncs slash commands globally by default. Set the Developer Portal's
**Public Bot** option and invite it separately to each server where it should be
used. Global commands may take a while to appear.

Discord only lists `/embed` for members with Manage Server permission because it
is an admin command. The application must be installed with both the `bot` and
`applications.commands` scopes.

Mention the bot in a server message to receive its current gateway heartbeat
latency in milliseconds.

## Forms

1. `/form-section` creates a section with a short slug and display title.
2. `/form-question` adds a short or paragraph question. Each section supports up
   to five questions because Discord limits modal forms to five inputs.
3. `/setup-form` selects a staff text channel. The command refuses channels that
   are visible to `@everyone`; grant the bot View Channel, Send Messages, and
   Embed Links there.
4. `/embed` posts the public announcement. `/button-form` attaches a persistent
   button to a link for an embed message authored by this bot.
5. Members click the button, answer the modal, and receive an ephemeral
   confirmation. Staff receive an embed with the member's avatar, mention, ID,
   answers, selected color, and large image. Answers are delivered to the staff
   channel and are not stored in the database.
6. `/edit-form` opens an ephemeral editor to add, edit, or remove questions;
   change their response type or required setting; update the submission embed's
   hex color or image URL; or remove a section. Removing a section first asks
   for confirmation and disables its buttons.

The provided banner is stored locally so its image does not expire with the
original Discord CDN link. Leave the image URL blank in `/edit-form` to use that
banner. Custom URLs should be permanent `http` or `https` links.

Discord button colors are limited to Blue, Grey, Green, or Red; custom hex colors
apply to the submission embed, not to the button itself.

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
- `rass_derb_bot/services/` — reusable validation, ping formatting, and business logic.
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
