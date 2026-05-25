import logging
from collections import deque
from datetime import datetime

_ERROR_WINDOW_SECONDS = 60
_ERROR_WINDOW_LIMIT = 10


class ErrorHandler:
    def __init__(self, logger):
        self.logger = logger
        self._error_times: deque[datetime] = deque()

    def _prune_old_errors(self, current_time: datetime) -> None:
        while self._error_times and (
            current_time - self._error_times[0]
        ).total_seconds() > _ERROR_WINDOW_SECONDS:
            self._error_times.popleft()

    def handle_error(self, error_type: str, error: Exception, context: str = None):
        """统一错误处理，60 秒滑动窗口内超过阈值则建议停止操作。"""
        current_time = datetime.now()
        self._prune_old_errors(current_time)
        self._error_times.append(current_time)

        error_msg = f"{error_type}: {str(error)}"
        if context:
            error_msg = f"{error_msg} | Context: {context}"

        self.logger.error(error_msg)

        if len(self._error_times) > _ERROR_WINDOW_LIMIT:
            self.logger.critical("Too many errors occurring! Consider stopping operations.")
            return False

        return True

    def reset_error_count(self):
        """重置错误计数。"""
        self._error_times.clear()

    def get_error_status(self) -> tuple[int, datetime | None]:
        """返回当前窗口内错误次数与最近一次错误时间。"""
        current_time = datetime.now()
        self._prune_old_errors(current_time)
        last_time = self._error_times[-1] if self._error_times else None
        return len(self._error_times), last_time
