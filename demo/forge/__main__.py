import os

import uvicorn
from dotenv import load_dotenv

import forge.sdk.forge_log

LOG = forge.sdk.forge_log.ForgeLogger(__name__)


if __name__ == "__main__":
    port = os.getenv("PORT", 8000)
    LOG.info(f"Agent server starting on http://localhost:{port}")
    load_dotenv()
    forge.sdk.forge_log.setup_logger()
    uvicorn.run(
        "forge.app:app", host="0.0.0.0", port=port, log_level="error", reload=True
    )
