"""Market-aware pre-market report scheduler and manual run manager."""
import os
import time
from datetime import datetime, timezone, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from app.config import settings
from app.services.pipeline_orchestrator import PipelineOrchestrator
from app.utils.logging_config import logger


class MarketScheduler:
    """Schedules pre-market report generation based on exchange timezones and trading calendars."""

    def __init__(self, demo_mode: bool = False):
        self.demo_mode = demo_mode
        self.orchestrator = PipelineOrchestrator(demo_mode=self.demo_mode)
        self.timezone_name = settings.DEFAULT_TIMEZONE
        self.market_open_hour = settings.MARKET_OPEN_HOUR
        self.market_open_minute = settings.MARKET_OPEN_MINUTE
        self.last_run_date: Optional[str] = None

    def is_market_day(self, target_date: datetime) -> bool:
        """Determines if the given date is a weekday (Monday=0 to Friday=4)."""
        return target_date.weekday() < 5

    def should_run_premarket(self) -> bool:
        """Evaluates whether current local exchange time is within pre-market window and hasn't run yet."""
        try:
            tz = ZoneInfo(self.timezone_name)
        except Exception:
            tz = timezone.utc

        now_local = datetime.now(tz)
        today_str = now_local.strftime("%Y-%m-%d")

        # Skip weekends
        if not self.is_market_day(now_local):
            return False

        # Avoid duplicate runs for the same date
        if self.last_run_date == today_str:
            return False

        # Target pre-market run is 30 minutes before market open
        target_minutes = (self.market_open_hour * 60) + self.market_open_minute - 30
        now_minutes = (now_local.hour * 60) + now_local.minute

        # If current time is within or after the premarket window on a trading day
        return now_minutes >= target_minutes

    def trigger_run(self) -> dict:
        """Manually triggers report generation with state logging."""
        logger.info(f"Triggering scheduled or manual pipeline run for {self.timezone_name}")
        try:
            result = self.orchestrator.run_pipeline()
            today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            self.last_run_date = today_str
            logger.info(f"Scheduled report generated successfully with ID: {result['report'].report_id}")
            return result
        except Exception as e:
            logger.error(f"Scheduled run failed: {e}", exc_info=True)
            raise e


def run_scheduler_loop(poll_interval_seconds: int = 60):
    """Local loop checking pre-market criteria. Note: only active while script is executing."""
    scheduler = MarketScheduler(demo_mode=settings.DEMO_MODE)
    logger.info(f"Starting local scheduler loop for {settings.DEFAULT_EXCHANGE} ({settings.DEFAULT_TIMEZONE})...")
    logger.info("NOTE: The local scheduler only executes while this terminal process remains running.")

    try:
        while True:
            if scheduler.should_run_premarket():
                logger.info("Pre-market window reached! Generating daily intelligence report...")
                scheduler.trigger_run()
            time.sleep(poll_interval_seconds)
    except KeyboardInterrupt:
        logger.info("Scheduler loop terminated by user.")


if __name__ == "__main__":
    run_scheduler_loop()
