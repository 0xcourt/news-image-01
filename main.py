#!/usr/bin/env python3
"""news-image-01 v2: a broadsheet summing up Friday 13 November 2026.

Draws the whole front page from scratch with the Python standard library
only: an embedded 5x7 bitmap font, a stylised world map with numbered,
region-coloured markers, a lead story, and 26 numbered stories in two
columns. No network, no files read, no randomness: the same bytes come
out on every run.

Layout (1024x1024): masthead, lead banner (FAA ground stop), numbered
world map with a region legend, then the day's stories in two columns.
Every story below is one of the day's verified reports; claims are
labelled CLAIMED and the one pending item is labelled PENDING. 27
stories in all: the lead plus 26 numbered stories across 5 regions.
"""

import os
import struct
import zlib

W, H = 1024, 1024
PAPER = (250, 246, 236)
INK = (20, 20, 20)
RED = (176, 30, 30)
GREY = (74, 74, 74)
OCEAN = (203, 221, 233)
LAND = (233, 224, 196)
MAPGREY = (96, 96, 96)
LEADBG = (244, 226, 220)
WHITE = (255, 255, 255)
# region colours (map markers; grid discs stay red)
REG_EUROPE = (38, 84, 160)
REG_ASIA = (34, 139, 60)
REG_AFRICA = (176, 122, 20)
REG_MIDEAST = (122, 62, 140)
REG_AMERICAS = RED

# ---------------------------------------------------------------- font: 5x7
# Each glyph is 7 rows of 5 cells ('#' = on). Uppercase, digits and the
# punctuation the page needs; draw_text() upper-cases everything.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "00000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ";": ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00010", "00100", "00000", "00100"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    '"': ("01010", "01010", "01010", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "+": ("00000", "00100", "00100", "01110", "00100", "00100", "00000"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    "*": ("00000", "01010", "00100", "11111", "00100", "01010", "00000"),
    "•": ("00000", "00000", "01110", "01110", "01110", "00000", "00000"),
}


def text_width(s, scale):
    """Advance width in pixels of s at the given scale."""
    return len(s) * (5 * scale + scale)


# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)
        self.fill_rect(0, 0, w, h, bg)

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i], self.px[i + 1], self.px[i + 2] = c

    def fill_rect(self, x, y, w, h, c):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                self.px[i], self.px[i + 1], self.px[i + 2] = c
                i += 3

    def hline(self, x, y, w, c):
        self.fill_rect(x, y, w, 1, c)

    def vline(self, x, y, h, c):
        self.fill_rect(x, y, 1, h, c)

    def line(self, x0, y0, x1, y1, c):
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            self.set(x0, y0, c)
            if x0 == x1 and y0 == y1:
                return
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def disc(self, cx, cy, r, c):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                if (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r:
                    self.set(xx, yy, c)

    def ring(self, cx, cy, r, c):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                d = (xx - cx) ** 2 + (yy - cy) ** 2
                if (r - 1) ** 2 <= d <= r * r:
                    self.set(xx, yy, c)

    def star(self, cx, cy, r, c):
        # 5-point star from 10 vertices (outer/inner), filled by scanlines.
        import math
        pts = []
        for k in range(10):
            ang = -math.pi / 2 + k * math.pi / 5
            rr = r if k % 2 == 0 else r * 0.45
            pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
        for yy in range(int(cy - r), int(cy + r) + 1):
            xs = []
            for k in range(10):
                x0, y0 = pts[k]
                x1, y1 = pts[(k + 1) % 10]
                if (y0 <= yy < y1) or (y1 <= yy < y0):
                    t = (yy - y0) / (y1 - y0)
                    xs.append(x0 + t * (x1 - x0))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                for xx in range(int(xs[k]), int(xs[k + 1]) + 1):
                    self.set(xx, yy, c)

    def text(self, s, x, y, scale, color, align="l"):
        s = s.upper()
        if align == "c":
            x -= text_width(s, scale) // 2
        elif align == "r":
            x -= text_width(s, scale)
        cx = x
        for ch in s:
            g = FONT.get(ch)
            if g is None:
                cx += 5 * scale + scale
                continue
            for row in range(7):
                bits = g[row]
                for col in range(5):
                    if bits[col] == "1":
                        self.fill_rect(cx + col * scale, y + row * scale,
                                       scale, scale, color)
            cx += 5 * scale + scale
        return cx


# ---------------------------------------------------------------- PNG encoder
def _chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


def png_bytes(cv):
    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    raw = bytearray()
    stride = cv.w * 3
    for y in range(cv.h):
        raw.append(0)
        raw += cv.px[y * stride:(y + 1) * stride]
    return (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr)
            + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + _chunk(b"IEND", b""))


# ---------------------------------------------------------------- world map
# Map area: x 24..1000, y 222..462. Equirectangular: lon -180..180,
# lat 78..-56. Continents are unions of lon/lat rectangles (stylised
# block map, no smears); extra small boxes sharpen the coasts of the
# British Isles, Japan, Korea, Taiwan, the Philippines, Sri Lanka,
# Indonesia, Cuba and Iceland.
MAP_X0, MAP_Y0, MAP_W, MAP_H = 24, 222, 976, 240
MAP_LON0, MAP_LAT0 = -180.0, 78.0


def lonlat_to_xy(lon, lat):
    x = MAP_X0 + (lon - MAP_LON0) / 360.0 * MAP_W
    y = MAP_Y0 + (MAP_LAT0 - lat) / 134.0 * MAP_H
    return int(round(x)), int(round(y))


# (lon_min, lon_max, lat_min, lat_max)
LAND_RECTS = [
    # North America
    (-168, -140, 58, 70), (-140, -60, 48, 70), (-125, -66, 25, 49),
    (-117, -83, 8, 30), (-92, -77, 8, 15), (-58, -20, 60, 78),
    (-85, -74, 20, 23), (-61, -60, 12, 14),
    # South America
    (-78, -52, 0, 10), (-75, -42, -15, 0), (-70, -55, -35, -15),
    (-70, -62, -52, -35),
    # Europe
    (-10, 3, 36, 44), (-5, 30, 44, 58), (5, 30, 55, 70),
    (-5, 2, 50, 58), (8, 28, 36, 45), (-10, -6, 51, 55),
    (-22, -14, 63, 66),
    # Africa
    (-10, 35, 15, 32), (-8, 42, 0, 15), (12, 33, -18, 0),
    (16, 32, -35, -18), (43, 50, -25, -12),
    # Asia
    (30, 180, 50, 72), (45, 130, 42, 52), (78, 125, 20, 42),
    (68, 88, 8, 32), (95, 105, 5, 28), (35, 58, 12, 30),
    (130, 142, 30, 45), (140, 145, 41, 45), (95, 140, -8, 5),
    (131, 147, -9, -1), (126, 130, 34, 40), (120, 122, 22, 25),
    (120, 122, 6, 18), (80, 82, 6, 9),
    # Australia / NZ
    (113, 130, -25, -12), (128, 148, -38, -12), (146, 153, -39, -30),
    (166, 178, -47, -34),
]

MAP_LABELS = [  # (text, lon, lat)
    ("NORTH AMERICA", -100, 60), ("SOUTH AMERICA", -60, -20),
    ("EUROPE", 20, 63), ("AFRICA", 20, 5), ("ASIA", 92, 58),
    ("AUSTRALIA", 134, -28), ("PACIFIC", -150, 8), ("ATLANTIC", -35, 22),
    ("INDIAN OCEAN", 78, -32),
]

# (number, lon, lat, label_dx, label_dy, region)
# Region colours: AMERICAS red, EUROPE blue, ASIA green, AFRICA gold,
# MIDDLE EAST purple. The lead story (1) is the red star.
MARKERS = [
    (1, -102, 43, 16, -8, REG_AMERICAS),   # FAA ground stop (star)
    (2, 30, 50, 8, -7, REG_EUROPE),       # Ukraine talks
    (3, 37, 55, 10, -18, REG_EUROPE),     # prisoner swap
    (4, 121, 23, 8, -7, REG_ASIA),        # Taiwan drill
    (5, 56, 26, 8, -14, REG_MIDEAST),     # Hormuz tankers
    (6, 50, 26, -30, 16, REG_MIDEAST),    # Iran radar claim
    (7, -122, 37, -28, -6, REG_AMERICAS), # Nvidia
    (8, -77, 39, 26, -12, REG_AMERICAS),  # chip curbs (DC)
    (9, -122, 47, -28, -6, REG_AMERICAS), # Microsoft outage
    (10, 34, 31, 10, -10, REG_MIDEAST),   # Gaza hospital (label sits
    # beside its dot with no leader line, so no line strikes the "1")
    (11, -77, 39, 26, 6, REG_AMERICAS),   # Van Hollen (DC)
    (12, -97, 37, 6, 20, REG_AMERICAS),   # Kansas
    (13, 2, 48, -30, 12, REG_EUROPE),     # IEA oil (Paris)
    (14, -74, 41, 30, -30, REG_AMERICAS), # Brooklyn (NYC)
    (15, -77, 39, 26, 24, REG_AMERICAS),  # DOJ crypto (DC)
    (16, -77, -12, 8, -7, REG_AMERICAS),  # Pope in Peru
    (17, -118, 35, -28, 12, REG_AMERICAS),# Google (nudged: shares the
    # Silicon Valley dot with 7, so it gets its own dot just inland)
    (18, -2, 52, -34, -6, REG_EUROPE),     # England v Croatia (nudged
    # west so its dot does not merge with the Dutch dot, 23)
    (19, -81, 27, 8, 8, REG_AMERICAS),    # Pegula
    (20, -9, 38, -34, 10, REG_EUROPE),    # Storm Charles (Lisbon)
    (21, -103, 29, -30, 14, REG_AMERICAS),# measles review (US-Mexico)
    (22, 31, 37, -34, 16, REG_ASIA),      # COP31 draft text (Antalya)
    (23, 7, 53, 10, 12, REG_EUROPE),      # Dutch coalition crisis
    # (nudged east so its dot does not merge with the England dot, 18)
    (24, 37, -1, 8, -7, REG_AFRICA),      # Nairobi collapse
    (25, -72, 19, 8, 8, REG_AMERICAS),    # Haiti stadium
    (26, 70, 30, 8, -7, REG_ASIA),        # Pakistan raids
    (27, 107, -6, 8, -7, REG_ASIA),       # Indonesia VP quits
]

LEGEND = [  # (label, colour) — marker colours on the map
    ("AMERICAS", REG_AMERICAS), ("EUROPE", REG_EUROPE),
    ("AFRICA", REG_AFRICA), ("MIDDLE EAST", REG_MIDEAST),
    ("ASIA", REG_ASIA),
]

# ---------------------------------------------------------------- stories
# (number, headline, summary) — headlines/summaries kept short so they
# stay legible at small size. Number matches the map marker.
STORIES = [
    (2, "EU JOINS UKRAINE TALKS",
     "KUSHNER, WITKOFF MET PUTIN"),
    (3, "PRISONER SWAP IN THE WORKS",
     "WAR'S LARGEST EXCHANGE BEGINS"),
    (4, "CHINA'S BIG PACIFIC DRILL",
     "TAIWAN: DRILL AROUND ISLAND"),
    (5, "FOUR TANKERS HIT AT HORMUZ",
     "LNG TANKER STRUCK A MINE"),
    (6, "IRAN CLAIMS US RADAR HIT",
     "CLAIMED: BAHRAIN, UNVERIFIED"),
    (7, "NVIDIA CHIEF QUITS, SHARES -16%",
     "HUANG OUT; KRESS INTERIM CEO"),
    (8, "US SPLIT OVER CHIP CURBS",
     "TREASURY VS COMMERCE CLASH"),
    (9, "MICROSOFT 365 DOWN WORLDWIDE",
     "MAIL AND TEAMS OUT GLOBALLY"),
    (10, "STRIKE ON GAZA HOSPITAL KILLS 6",
     "NASSER HOSPITAL; SURGEON DEAD"),
    (11, "SENATE LEADERSHIP CHALLENGE",
     "VAN HOLLEN SEEKS SENATE POST"),
    (12, "DEMOCRAT WINS KANSAS RACE",
     "TWO-DAY COUNT ENDS IN WIN"),
    (13, "OIL GLUT LOOMS, IEA SAYS",
     "SUPPLY 105M B/D, +1.7M OVER"),
    (14, "BROOKLYN COLLAPSE: 8 DEAD",
     "2 CHILDREN, 2 WORKERS DEAD"),
    (15, "US SEIZES $1.2BN IN CRYPTO",
     "BINANCE HACK; N. KOREA BLAMED"),
    (16, "POPE MEETS ABUSE SURVIVORS",
     "RECORD CROWDS GREET LEO"),
    (17, "GOOGLE UNVEILS GEMINI 4",
     "NEW MODEL; GLASSES ON PREORDER"),
    (18, "ENGLAND BEAT CROATIA",
     "INTO NATIONS LEAGUE LAST 8"),
    (19, "PEGULA SAVES MATCH POINT",
     "AMERICAN INTO WTA SEMIS"),
    (20, "STORM CHARLES HITS PORTUGAL",
     "SCHOOLS CLOSED IN MAINLAND"),
    (21, "MEASLES RULING STILL PENDING",
     "PAHO REVIEWS YEAR OF CASES"),
    (22, "COP31 DRAFT DEAL TEXT OUT",
     "FIRST COVER TEXT IN ANTALYA"),
    (23, "DUTCH GOVT ON THE BRINK",
     "CRISIS TALKS OVER WEALTH TAX"),
    (24, "NAIROBI BUILDING COLLAPSE",
     "6 DEAD AS 8 STOREYS FALL"),
    (25, "HAITI RETAKES ITS STADIUM",
     "GANGS HELD IT FOR 2 YEARS"),
    (26, "PAKISTAN KILLS 74 MILITANTS",
     "RAIDS NEAR AFGHAN BORDER"),
    (27, "INDONESIA VP QUITS IN ROW",
     "GIBRAN OUT OVER SCHOOL PAPERS"),
]


# ---------------------------------------------------------------- build
def build():
    cv = Canvas(W, H, PAPER)
    # frame
    cv.fill_rect(8, 8, W - 16, 3, INK)
    cv.fill_rect(8, H - 11, W - 16, 3, INK)
    cv.fill_rect(8, 8, 3, H - 16, INK)
    cv.fill_rect(W - 11, 8, 3, H - 16, INK)

    # ---- masthead
    cv.text("THE WORLD IN ONE PICTURE", 512, 22, 5, INK, align="c")
    cv.hline(24, 64, 976, INK)
    cv.hline(24, 67, 976, INK)
    cv.text("FRIDAY 13 NOVEMBER 2026  •  27 STORIES  •  6 CONTINENTS",
            512, 74, 2, GREY, align="c")

    # ---- lead banner
    cv.fill_rect(24, 100, 976, 96, LEADBG)
    cv.fill_rect(24, 100, 8, 96, RED)
    cv.text("LEAD STORY  •  3RD NATIONWIDE GROUND STOP IN US HISTORY",
            48, 106, 2, RED)
    cv.text("US GROUNDS ALL FLIGHTS", 48, 122, 5, INK)
    cv.text("FAA HALTS EVERY DEPARTURE FOR ABOUT 4 HOURS",
            48, 158, 3, INK)
    cv.text("TELECOM OUTAGE: 10,000+ DELAYS, 2,000+ CANCELLED. "
            "DHS: NO CYBERATTACK", 48, 182, 2, GREY)

    # ---- map
    cv.text("THE WORLD, NUMBERED - FOLLOW THE NUMBERS",
            24, 206, 2, INK)
    cv.text("STAR 1 IS THE LEAD STORY", 1000, 206, 2, RED, align="r")
    cv.fill_rect(MAP_X0, MAP_Y0, MAP_W, MAP_H, OCEAN)
    # graticule every 30 degrees
    for lon in range(-150, 181, 30):
        x, _ = lonlat_to_xy(lon, 0)
        cv.vline(x, MAP_Y0, MAP_H, (190, 208, 222))
    for lat in range(-30, 61, 30):
        _, y = lonlat_to_xy(0, lat)
        cv.hline(MAP_X0, y, MAP_W, (190, 208, 222))
    for (lo0, lo1, la0, la1) in LAND_RECTS:
        x0, y1 = lonlat_to_xy(lo0, la0)
        x1, y0 = lonlat_to_xy(lo1, la1)
        cv.fill_rect(x0, y0, x1 - x0, y1 - y0, LAND)
    cv.fill_rect(MAP_X0, MAP_Y0, MAP_W, 2, INK)
    cv.fill_rect(MAP_X0, MAP_Y0 + MAP_H - 2, MAP_W, 2, INK)
    cv.fill_rect(MAP_X0, MAP_Y0, 2, MAP_H, INK)
    cv.fill_rect(MAP_X0 + MAP_W - 2, MAP_Y0, 2, MAP_H, INK)
    for (label, lon, lat) in MAP_LABELS:
        x, y = lonlat_to_xy(lon, lat)
        cv.text(label, x, y, 2, MAPGREY, align="c")
    for (num, lon, lat, dx, dy, region) in MARKERS:
        x, y = lonlat_to_xy(lon, lat)
        if num == 1:
            cv.star(x, y, 13, RED)
            cv.ring(x, y, 13, INK)
        else:
            cv.disc(x, y, 4, region)
            cv.ring(x, y, 4, INK)
        lx, ly = x + dx, y + dy
        if abs(dx) > 12 or abs(dy) > 12:
            cv.line(x, y, lx, ly, region)
        cv.text(str(num), lx, ly, 2, INK if num == 1 else region)

    # ---- region legend under the map
    lx = 222
    for (label, colour) in LEGEND:
        cv.fill_rect(lx, 470, 10, 10, colour)
        lx += 16
        lx = cv.text(label, lx, 469, 2, INK)
        lx += 20

    # ---- stories
    cv.hline(24, 492, 976, INK)
    cv.text("THE DAY IN STORIES", 24, 500, 3, INK)
    cv.text("NUMBERS MATCH THE MAP", 1000, 502, 2, GREY, align="r")
    col_x = (24, 512)
    row_y0, row_h = 526, 35
    for i, (num, head, summ) in enumerate(STORIES):
        col = i // 13
        row = i % 13
        x = col_x[col]
        y = row_y0 + row * row_h
        if row < 12:
            cv.hline(x, y + 33, 488, (214, 209, 194))
        cv.disc(x + 10, y + 8, 10, RED)
        cv.text(str(num), x + 10, y + 1, 2, WHITE, align="c")
        cv.text(head, x + 28, y, 2, INK)
        cv.text(summ, x + 28, y + 17, 2, GREY)

    # ---- footer
    cv.hline(24, 990, 976, INK)
    cv.text("EVERY STORY ABOVE HAPPENED OR WAS FIRST REPORTED ON "
            "FRIDAY 13 NOVEMBER 2026", 512, 996, 2, GREY, align="c")
    return cv


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    data = png_bytes(build())
    with open(os.path.join(out_dir, "entry.png"), "wb") as f:
        f.write(data)


if __name__ == "__main__":
    main()
