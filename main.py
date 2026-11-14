#!/usr/bin/env python3
"""news-image-01 v1: a broadsheet summing up Friday 13 November 2026.

Draws the whole front page from scratch with the Python standard library
only: an embedded 5x7 bitmap font, a blocky world map, a lead story, and
20 numbered stories. No network, no files read, no randomness: the same
bytes come out on every run.

Layout (1024x1024): masthead, lead banner (FAA ground stop), numbered
world map, then the day's stories in two columns. Every story below is
one of the day's verified reports; claims are labelled CLAIMED and the
one pending item is labelled PENDING.
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
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
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
# Map area: x 24..1000, y 256..546. Equirectangular: lon -180..180,
# lat 78..-56. Continents are unions of lon/lat rectangles (blocky on
# purpose: a clean stylised map, no smears).
MAP_X0, MAP_Y0, MAP_W, MAP_H = 24, 256, 976, 290
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
    # South America
    (-78, -52, 0, 10), (-75, -42, -15, 0), (-70, -55, -35, -15),
    (-70, -62, -52, -35),
    # Europe
    (-10, 3, 36, 44), (-5, 30, 44, 58), (5, 30, 55, 70),
    (-5, 2, 50, 58), (8, 28, 36, 45),
    # Africa
    (-10, 35, 15, 32), (-8, 42, 0, 15), (12, 33, -18, 0),
    (16, 32, -35, -18), (43, 50, -25, -12),
    # Asia
    (30, 180, 50, 72), (45, 130, 42, 52), (78, 125, 20, 42),
    (68, 88, 8, 32), (95, 105, 5, 28), (35, 58, 12, 30),
    (130, 142, 30, 45), (95, 140, -8, 5),
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

# (number, lon, lat, label_dx, label_dy) — label offset in px from the dot.
MARKERS = [
    (1, -102, 43, 16, -8),    # FAA ground stop (star)
    (2, 30, 50, 8, -7),       # Ukraine talks
    (3, 37, 55, 10, -18),     # prisoner swap
    (4, 121, 23, 8, -7),      # Taiwan drill
    (5, 56, 26, 8, -14),      # Hormuz tankers
    (6, 50, 26, -26, 10),     # Iran radar claim
    (7, -122, 37, -28, -6),   # Nvidia
    (8, -77, 39, 26, -12),    # chip curbs (DC)
    (9, -122, 47, -28, -6),   # Microsoft outage
    (10, 34, 31, 8, -7),      # Gaza hospital
    (11, -77, 39, 26, 6),     # Van Hollen (DC)
    (12, -97, 37, 6, 20),     # Kansas
    (13, 2, 48, -30, 12),     # IEA oil (Paris)
    (14, -74, 41, 30, -30),   # Brooklyn (NYC)
    (15, -77, 39, 26, 24),    # DOJ crypto (DC)
    (16, -77, -12, 8, -7),    # Pope in Peru
    (17, -122, 37, -28, 12),  # Google
    (18, 0, 51, -34, -6),     # England v Croatia
    (19, -81, 27, 8, 8),      # Pegula
    (20, -9, 38, -34, 10),    # Storm Charles (Lisbon)
    (21, -103, 29, -30, 14),  # measles review (US-Mexico)
]

# ---------------------------------------------------------------- stories
# (number, headline, summary) — headlines/summaries kept short so they
# stay legible at small size. Number matches the map marker.
STORIES = [
    (2, "RUSSIA AGREES TO EUROPE AT TALKS",
     "KUSHNER, WITKOFF MET PUTIN IN MOSCOW"),
    (3, "BIGGEST PRISONER SWAP IN WORKS",
     "WORK BEGINS ON WAR'S LARGEST EXCHANGE"),
    (4, "CHINA'S BIG PACIFIC DRILL",
     "TAIWAN: LARGE DRILL AROUND ISLAND"),
    (5, "FOUR TANKERS HIT AT HORMUZ",
     "LNG TANKER STRUCK A NAVAL MINE"),
    (6, "IRAN CLAIMS US RADAR DESTROYED",
     "CLAIMED STRIKE IN BAHRAIN - UNVERIFIED"),
    (7, "NVIDIA CHIEF QUITS, SHARES -16%",
     "HUANG RESIGNS; KRESS INTERIM CEO"),
    (8, "US SPLIT OVER CHIP CURBS",
     "TREASURY VS COMMERCE IN PUBLIC CLASH"),
    (9, "MICROSOFT 365 DOWN WORLDWIDE",
     "MAIL AND TEAMS OUT ACROSS THE GLOBE"),
    (10, "STRIKE ON GAZA HOSPITAL KILLS 6",
     "NASSER HOSPITAL; SURGEON AMONG DEAD"),
    (11, "DEMOCRAT CHALLENGES SCHUMER",
     "VAN HOLLEN SEEKS SENATE LEADERSHIP"),
    (12, "DEMOCRAT WINS KANSAS GOVERNOR",
     "TWO-DAY COUNT ENDS IN DEMOCRATIC WIN"),
    (13, "OIL GLUT LOOMS, IEA SAYS",
     "Q4 SUPPLY 105M B/D, +1.7M OVER DEMAND"),
    (14, "BROOKLYN COLLAPSE: 8 DEAD",
     "2 CHILDREN, 2 WORKERS DEAD; 18 HURT"),
    (15, "US SEIZES $1.2BN IN CRYPTO",
     "BINANCE HACK FUNDS; N. KOREA BLAMED"),
    (16, "POPE MEETS ABUSE SURVIVORS",
     "RECORD CROWDS GREET LEO IN LIMA"),
    (17, "GOOGLE UNVEILS GEMINI 4",
     "NEW SEARCH MODEL; GLASSES ON PREORDER"),
    (18, "ENGLAND BEAT CROATIA",
     "ENGLAND REACH NATIONS LEAGUE LAST 8"),
    (19, "PEGULA SAVES MATCH POINT",
     "AMERICAN INTO WTA SEMI-FINALS"),
    (20, "STORM CHARLES HITS PORTUGAL",
     "SEVERE WEATHER; SCHOOLS CLOSED"),
    (21, "MEASLES RULING STILL PENDING",
     "PAHO REVIEWS YEAR OF US, MEXICO CASES"),
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
    cv.text("THE WORLD IN ONE PICTURE", 512, 28, 6, INK, align="c")
    cv.hline(24, 82, 976, INK)
    cv.text("FRIDAY 13 NOVEMBER 2026  •  21 STORIES  •  6 CONTINENTS",
            512, 90, 2, GREY, align="c")

    # ---- lead banner
    cv.fill_rect(24, 116, 976, 112, LEADBG)
    cv.fill_rect(24, 116, 8, 112, RED)
    cv.text("LEAD STORY  •  3RD NATIONWIDE GROUND STOP IN US HISTORY",
            48, 124, 2, RED)
    cv.text("US GROUNDS ALL FLIGHTS", 48, 142, 6, INK)
    cv.text("FAA HALTS EVERY DEPARTURE FOR ABOUT 4 HOURS",
            48, 188, 3, INK)
    cv.text("TELECOM OUTAGE IN AIR-TRAFFIC CONTROL: 10,000+ DELAYS, "
            "2,000+ CANCELLED", 48, 210, 2, GREY)

    # ---- map
    cv.text("THE WORLD, NUMBERED - FOLLOW THE NUMBERS",
            24, 238, 2, INK)
    cv.text("RED STAR 1 IS THE LEAD STORY", 1000, 238, 2, RED, align="r")
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
    for (num, lon, lat, dx, dy) in MARKERS:
        x, y = lonlat_to_xy(lon, lat)
        if num == 1:
            cv.star(x, y, 14, RED)
            cv.ring(x, y, 14, INK)
        else:
            cv.disc(x, y, 4, RED)
            cv.ring(x, y, 4, INK)
        lx, ly = x + dx, y + dy
        if abs(dx) > 12 or abs(dy) > 12:
            cv.line(x, y, lx, ly, RED)
        cv.text(str(num), lx, ly, 2, RED if num != 1 else INK)

    # ---- stories
    cv.hline(24, 556, 976, INK)
    cv.text("THE DAY IN STORIES", 24, 564, 3, INK)
    cv.text("NUMBERS MATCH THE MAP", 1000, 566, 2, GREY, align="r")
    col_x = (24, 524)
    row_y0, row_h = 592, 41
    for i, (num, head, summ) in enumerate(STORIES):
        col = i // 10
        row = i % 10
        x = col_x[col]
        y = row_y0 + row * row_h
        cv.disc(x + 11, y + 8, 11, RED)
        cv.text(str(num), x + 11, y + 1, 2, WHITE, align="c")
        cv.text(head, x + 30, y, 2, INK)
        cv.text(summ, x + 30, y + 18, 2, GREY)

    # ---- footer
    cv.hline(24, 994, 976, INK)
    cv.text("EVERY STORY ABOVE HAPPENED OR WAS FIRST REPORTED ON "
            "FRIDAY 13 NOVEMBER 2026", 512, 999, 2, GREY, align="c")
    return cv


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    data = png_bytes(build())
    with open(os.path.join(out_dir, "entry.png"), "wb") as f:
        f.write(data)


if __name__ == "__main__":
    main()
