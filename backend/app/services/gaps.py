from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.repositories.interfaces import MarketDataRepository

SUPPORTED_INTERVALS = {
    "1m": timedelta(minutes=1),
}


@dataclass(frozen=True)
class CandleGap:
    symbol: str
    interval: str
    start_time: datetime
    end_time: datetime
    missing_candle_count: int


@dataclass(frozen=True)
class GapDetectionResult:
    symbol: str
    interval: str
    scan_start: datetime | None
    scan_end: datetime | None
    expected_candle_count: int
    observed_candle_count: int
    missing_candle_count: int
    gaps: list[CandleGap]


class GapDetectionService:
    def __init__(self, repository: MarketDataRepository) -> None:
        self._repository = repository

    def detect_for_symbols(
        self,
        symbols: list[str],
        interval: str,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[GapDetectionResult]:
        return [
            self.detect_for_symbol(symbol=symbol, interval=interval, start=start, end=end)
            for symbol in symbols
        ]

    def detect_for_symbol(
        self,
        *,
        symbol: str,
        interval: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> GapDetectionResult:
        step = self._interval_step(interval)
        scan_start = self._normalize(start)
        scan_end = self._normalize(end) or self._runtime_scan_end(symbol, interval)

        if scan_start is None or scan_end is None or scan_start > scan_end:
            return GapDetectionResult(
                symbol=symbol,
                interval=interval,
                scan_start=scan_start,
                scan_end=scan_end,
                expected_candle_count=0,
                observed_candle_count=0,
                missing_candle_count=0,
                gaps=[],
            )

        candles = self._repository.list_candles_in_range(symbol, interval, scan_start, scan_end)
        observed_open_times = {self._normalize_required(candle.open_time) for candle in candles}
        expected_open_times = list(self._expected_open_times(scan_start, scan_end, step))
        gaps = self._build_gaps(
            symbol=symbol,
            interval=interval,
            expected_open_times=expected_open_times,
            observed_open_times=observed_open_times,
            step=step,
        )

        missing_count = sum(gap.missing_candle_count for gap in gaps)
        return GapDetectionResult(
            symbol=symbol,
            interval=interval,
            scan_start=scan_start,
            scan_end=scan_end,
            expected_candle_count=len(expected_open_times),
            observed_candle_count=len(observed_open_times),
            missing_candle_count=missing_count,
            gaps=gaps,
        )

    def _runtime_scan_end(self, symbol: str, interval: str) -> datetime | None:
        status = self._repository.get_runtime_status(symbol, interval)
        if status is None:
            return None
        return self._normalize(status.last_candle_open_time)

    @staticmethod
    def _interval_step(interval: str) -> timedelta:
        try:
            return SUPPORTED_INTERVALS[interval]
        except KeyError as exc:
            raise ValueError(f"Unsupported interval for gap detection: {interval}") from exc

    @staticmethod
    def _expected_open_times(
        start: datetime,
        end: datetime,
        step: timedelta,
    ) -> list[datetime]:
        values: list[datetime] = []
        current = start
        while current <= end:
            values.append(current)
            current += step
        return values

    @staticmethod
    def _build_gaps(
        *,
        symbol: str,
        interval: str,
        expected_open_times: list[datetime],
        observed_open_times: set[datetime],
        step: timedelta,
    ) -> list[CandleGap]:
        gaps: list[CandleGap] = []
        gap_start: datetime | None = None
        missing_count = 0

        for open_time in expected_open_times:
            if open_time in observed_open_times:
                if gap_start is not None:
                    gaps.append(
                        CandleGap(
                            symbol=symbol,
                            interval=interval,
                            start_time=gap_start,
                            end_time=open_time - step,
                            missing_candle_count=missing_count,
                        )
                    )
                    gap_start = None
                    missing_count = 0
                continue

            if gap_start is None:
                gap_start = open_time
            missing_count += 1

        if gap_start is not None:
            gaps.append(
                CandleGap(
                    symbol=symbol,
                    interval=interval,
                    start_time=gap_start,
                    end_time=expected_open_times[-1],
                    missing_candle_count=missing_count,
                )
            )

        return gaps

    @staticmethod
    def _normalize(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return GapDetectionService._normalize_required(value)

    @staticmethod
    def _normalize_required(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
