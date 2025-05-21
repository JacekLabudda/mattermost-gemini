#!/bin/bash

source ./.venv/bin/activate

export MATTERMOST_URL=http://127.0.0.1
export MATTERMOST_PORT=8065
export MATTERMOST_API_PATH=/api/v4
export BOT_TOKEN=

export GEMINI_MODEL=gemini-2.0-flash
export GEMINI_API_KEY=

python3 gemini.py