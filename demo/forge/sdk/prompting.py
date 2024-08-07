import glob
import os
from difflib import get_close_matches
from typing import List

from jinja2 import Environment, FileSystemLoader

from .forge_log import ForgeLogger

LOG = ForgeLogger(__name__)


class PromptEngine:
    def __init__(self, model: str, debug_enabled: bool = False):

        self.model = model
        self.debug_enabled = debug_enabled
        if self.debug_enabled:
            LOG.debug(f"Initializing PromptEngine for model: {model}")

        try:
            # Get the list of all model directories
            models_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "../prompts")
            )
            model_names = [
                os.path.basename(os.path.normpath(d))
                for d in glob.glob(os.path.join(models_dir, "*/"))
                if os.path.isdir(d) and "techniques" not in d
            ]

            self.model = self.get_closest_match(self.model, model_names)

            if self.debug_enabled:
                LOG.debug(f"Using the closest match model for prompts: {self.model}")

            self.env = Environment(loader=FileSystemLoader(models_dir))
        except Exception as e:
            LOG.error(f"Error initializing Environment: {e}")
            raise

    @staticmethod
    def get_closest_match(target: str, model_dirs: List[str]) -> str:
        try:
            matches = get_close_matches(target, model_dirs, n=1, cutoff=0.1)
            if matches:
                matches_str = ", ".join(matches)
                LOG.debug(matches_str)
            for m in matches:
                LOG.info(m)
            return matches[0]
        except Exception as e:
            LOG.error(f"Error finding closest match: {e}")
            raise

    def load_prompt(self, template: str, **kwargs) -> str:
        try:
            template = os.path.join(self.model, template)
            if self.debug_enabled:
                LOG.debug(f"Loading template: {template}")
            template = self.env.get_template(f"{template}.j2")
            if self.debug_enabled:
                LOG.debug(f"Rendering template: {template} with args: {kwargs}")
            return template.render(**kwargs)
        except Exception as e:
            LOG.error(f"Error loading or rendering template: {e}")
            raise
