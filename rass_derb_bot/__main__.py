"""Run the bot with ``python -m rass_derb_bot``."""

from __future__ import annotations

import logging

from rass_derb_bot.bot import RassDerbBot
from rass_derb_bot.config import Settings


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    settings = Settings.from_environment()
    bot = RassDerbBot(settings)
    bot.run(settings.token, log_handler=None)


if __name__ == "__main__":
    main()
