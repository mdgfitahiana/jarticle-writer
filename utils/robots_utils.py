import urllib.robotparser as robotparser
from urllib.parse import urlparse
from config import HEADERS

_robot_cache: dict = {}

def get_robot_parser_for(url: str):
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    if base in _robot_cache:
        return _robot_cache[base]
    rp = robotparser.RobotFileParser()
    try:
        rp.set_url(base + "/robots.txt")
        rp.read()
        _robot_cache[base] = rp
    except Exception:
        _robot_cache[base] = None
    return _robot_cache[base]

def allowed_by_robots(url: str) -> bool:
    rp = get_robot_parser_for(url)
    if not rp:
        return True
    try:
        return rp.can_fetch(HEADERS["User-Agent"], url)
    except Exception:
        return True
