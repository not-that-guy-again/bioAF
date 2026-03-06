"""Slack notification channel adapter using webhook POST."""

import asyncio
import logging

import httpx

logger = logging.getLogger("bioaf.notifications.slack")

MAX_RETRIES = 3
BACKOFF_BASE = 2  # seconds: 2, 8, 32

SEVERITY_COLORS = {
    "info": "#36a64f",  # green
    "warning": "#f2c744",  # yellow
    "critical": "#e01e5a",  # red
}


class SlackChannel:
    @staticmethod
    async def deliver(
        webhook_url: str,
        title: str,
        message: str,
        severity: str,
    ) -> bool:
        color = SEVERITY_COLORS.get(severity, "#36a64f")
        payload = {
            "attachments": [
                {
                    "color": color,
                    "title": title,
                    "text": message,
                    "footer": "bioAF Platform",
                    "fields": [
                        {
                            "title": "Severity",
                            "value": severity.capitalize(),
                            "short": True,
                        }
                    ],
                }
            ]
        }

        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(webhook_url, json=payload)
                    response.raise_for_status()
                logger.info("Slack notification sent: %s", title)
                return True
            except Exception as e:
                backoff = BACKOFF_BASE ** (attempt * 2 + 1)
                logger.warning(
                    "Slack attempt %d/%d failed: %s (backoff %ds)",
                    attempt + 1,
                    MAX_RETRIES,
                    e,
                    backoff,
                )
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(backoff)

        logger.error("Slack delivery failed after %d attempts", MAX_RETRIES)
        return False
