"""Settings package for SimTrack.

Import development settings for compatibility with older local run
configurations that still use DJANGO_SETTINGS_MODULE=simtrack.settings.
Production deployments should use simtrack.settings.prod explicitly.
"""

from .dev import *  # noqa: F403
