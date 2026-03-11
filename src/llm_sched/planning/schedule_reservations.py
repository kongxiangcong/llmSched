"""Shared interval reservation helpers for SPEC-10/11 schedulers."""

from __future__ import annotations

from bisect import bisect_left, insort
from collections import defaultdict

ReservationWindow = tuple[int, int]
ReservationRequest = tuple[str, int, int]
ReservationTimeline = dict[str, list[ReservationWindow]]


def build_reservation_timeline() -> ReservationTimeline:
    """Create an empty timeline keyed by scheduler resource."""

    return defaultdict(list)


def find_earliest_issue_slot(
    *,
    ready_slot: int,
    reservations_by_resource: ReservationTimeline,
    requested_reservations: list[ReservationRequest],
) -> int:
    """Find the earliest issue slot that does not overlap any requested window."""

    issue_slot = max(0, ready_slot)
    normalized_requests = [
        (resource_key, start_offset, reservation_duration)
        for resource_key, start_offset, reservation_duration in requested_reservations
        if reservation_duration > 0
    ]
    if not normalized_requests:
        return issue_slot

    while True:
        next_issue_slot: int | None = None
        for resource_key, start_offset, reservation_duration in normalized_requests:
            window_start = issue_slot + start_offset
            window_end = window_start + reservation_duration
            intervals = reservations_by_resource.get(resource_key, [])
            interval_index = bisect_left(intervals, (window_start, -1))
            candidate_intervals: list[ReservationWindow] = []
            if interval_index > 0:
                candidate_intervals.append(intervals[interval_index - 1])
            if interval_index < len(intervals):
                candidate_intervals.append(intervals[interval_index])
            for reserved_start, reserved_end in candidate_intervals:
                if reserved_end <= window_start or reserved_start >= window_end:
                    continue
                candidate_issue_slot = reserved_end - start_offset
                next_issue_slot = (
                    candidate_issue_slot
                    if next_issue_slot is None
                    else max(next_issue_slot, candidate_issue_slot)
                )
                break
        if next_issue_slot is None:
            return issue_slot
        issue_slot = next_issue_slot


def reserve_resource_windows(
    *,
    reservations_by_resource: ReservationTimeline,
    issue_slot: int,
    requested_reservations: list[ReservationRequest],
) -> None:
    """Insert absolute reservation windows into the timeline."""

    for resource_key, start_offset, reservation_duration in requested_reservations:
        if reservation_duration <= 0:
            continue
        window = (issue_slot + start_offset, issue_slot + start_offset + reservation_duration)
        insort(reservations_by_resource[resource_key], window)
