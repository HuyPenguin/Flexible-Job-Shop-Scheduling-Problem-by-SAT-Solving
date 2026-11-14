from dataclasses import dataclass


@dataclass
class ScheduleEntry:
    """Một dòng trong bảng lịch trình."""
    job: int
    operation: int
    machine: int
    start: int
    end: int

    @property
    def duration(self) -> int:
        return self.end - self.start


def get_makespan(schedule: list[ScheduleEntry]) -> int:
    """Trả về makespan (thời gian hoàn thành muộn nhất)."""
    return max(e.end for e in schedule) if schedule else 0

