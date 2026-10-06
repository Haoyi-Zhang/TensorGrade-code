"""Optional POSIX resource accounting for the bounded local runners."""
from __future__ import annotations

import os

try:
    import resource
except ImportError:
    resource = None


def apply_limits():
    if resource is not None:
        resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
        resource.setrlimit(resource.RLIMIT_CPU, (105, 110))
    if hasattr(os, 'sched_getaffinity'):
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})


def peak_rss_kib():
    if resource is None:
        return None
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return value / 1024 if os.uname().sysname == 'Darwin' else value


def child_usage():
    if resource is None:
        return None
    value = resource.getrusage(resource.RUSAGE_CHILDREN)
    rss = value.ru_maxrss / 1024 if os.uname().sysname == 'Darwin' else value.ru_maxrss
    return value.ru_utime + value.ru_stime, rss


def enforced_limits():
    return {
        'address_space_bytes': 2 * 1024**3 if resource is not None else None,
        'process_cpu_soft_seconds': 105 if resource is not None else None,
        'process_cpu_hard_seconds': 110 if resource is not None else None,
        'posix_resource_available': resource is not None,
    }
