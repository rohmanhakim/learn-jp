#!/usr/bin/env python3
"""Convert hh:mm:ss format to seconds."""

import sys


def hhmmss_to_seconds(time_str: str) -> int:
    """Convert hh:mm:ss or mm:ss to seconds."""
    parts = time_str.strip().split(":")
    
    if len(parts) == 3:
        hours, minutes, seconds = map(int, parts)
        return hours * 3600 + minutes * 60 + seconds
    elif len(parts) == 2:
        minutes, seconds = map(int, parts)
        return minutes * 60 + seconds
    else:
        return int(parts[0])


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python hhmmss_to_seconds.py <time>")
        print("Example: python hhmmss_to_seconds.py 01:30:00")
        sys.exit(1)
    
    time_str = sys.argv[1]
    seconds = hhmmss_to_seconds(time_str)
    print(f"{time_str} = {seconds} seconds")
