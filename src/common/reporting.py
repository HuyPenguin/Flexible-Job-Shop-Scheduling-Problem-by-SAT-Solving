from .schedule import ScheduleEntry


def print_schedule(schedule: list[ScheduleEntry]):
    """In bảng lịch trình ra console."""
    schedule_sorted = sorted(schedule, key=lambda e: (e.job, e.operation))

    print(f"\n{'Job':<6}{'Op':<6}{'Machine':<10}{'Start':<8}{'End':<8}{'Duration':<10}")
    print("-" * 48)
    for e in schedule_sorted:
        print(f"{e.job:<6}{e.operation:<6}M{e.machine:<9}{e.start:<8}{e.end:<8}{e.duration:<10}")

    # Gantt theo máy
    machine_map: dict[int, list[ScheduleEntry]] = {}
    for e in schedule:
        machine_map.setdefault(e.machine, []).append(e)

    print("\n--- Gantt theo máy ---")
    for k in sorted(machine_map):
        entries = sorted(machine_map[k], key=lambda e: e.start)
        parts = [f"J{e.job}.{e.operation}[{e.start}-{e.end}]" for e in entries]
        print(f"  M{k}: {', '.join(parts)}")


