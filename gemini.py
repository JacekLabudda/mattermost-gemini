import json
import logging
import os
import re
import signal
import sys
import time
import traceback

import google.generativeai as genai
from mmpy_bot import (
    Bot,
    Message,
    Plugin,
    Settings,
    listen_to
)

log = logging.getLogger("gemini-chat-bot")

def handler(signum, frame):
    print(f"Signal {signum} received.")
    sys.exit(0)


class ChatBot(Plugin):
    def __init__(self):
        super().__init__()
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))
        self.model = genai.GenerativeModel(os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"))
    @listen_to("")
    def respond(self, message: Message):
        if self.driver is None or self.settings is None:
            raise ValueError("Driver or settings is None")

        thread = self.driver.get_post_thread(message.id)

        if not self.is_reply_required(thread, message.sender_name):
            return

        context = self.driver.channels.get_channel(message.channel_id)["header"]

        request_messages = self.build_request_messages(
            thread, self.driver.user_id, context
        )

        log.info("API Request: " + json.dumps(request_messages, ensure_ascii=False))

        try:
            reply = self.driver.reply_to(message, "")
            reply_id = reply["id"]

            response = self.model.generate_content(request_messages)
            response_text = getattr(response, "text", "")
            if not response_text and hasattr(response, "candidates"):
                response_text = response.candidates[0].content.parts[0].text

            log.info("API Response: " + response_text)

            self.driver.posts.update_post(
                post_id=reply_id,
                options={
                    "id": reply_id,
                    "message": response_text
                }
            )

        except Exception:
            stacktrace = traceback.format_exc()
            log.error(f"Exception:\n{stacktrace}")
            self.driver.create_post(
                message.channel_id, f"Exception occurred.\n```{stacktrace}```"
            )

    def is_reply_required(self, thread, sender_name: str) -> bool:
        if sender_name.startswith("ai-"):
            return False

        username_escaped = self.driver.username.replace(".", "\\.")
        pattern = fr"(^|\s)@{username_escaped}(?=$|\s)"

        for post_id in thread["order"]:
            if re.search(pattern, thread["posts"][post_id]["message"]):
                return True

        return False

    def build_request_messages(self, thread, bot_id, context) -> list:
        messages = []

        for post_id in thread["order"]:
            post = thread["posts"][post_id]
            message = post["message"].replace("@" + self.driver.username, "")
            role = "model" if post["user_id"] == bot_id else "user"

            if role == "user" and len(messages) == 0:
                messages.append({
                    "role": "user",
                    "parts": [f"{context}\n---\n{message}"]
                })
            else:
                messages.append({
                    "role": role,
                    "parts": [message]
                })

        return messages

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, handler)
    bot = Bot(settings=Settings(), plugins=[ChatBot()])
    bot.run()