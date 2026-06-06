#include "display.h"
#include <SPI.h>

// ── Singleton definitions ────────────────────────────────────
Adafruit_ST7735 tft(TFT_CS, TFT_DC, TFT_RST);
StreamState     ss;

// ============================================================
//  INIT
// ============================================================
void displayInit() {
    SPI.begin();
    tft.initR(INITR_BLACKTAB);
    tft.setRotation(3);        // landscape 180°: 160 wide × 128 tall
    tft.fillScreen(C_BG);
    tft.setTextWrap(false);
}

// ============================================================
//  INTERNAL HELPERS
// ============================================================

// ── FACE GEOMETRY (160×128 landscape) ──────────────────────
// Face centre: cx=80, cy=72  |  hair top: ~y=10
static const int FCX = 80;
static const int FCY = 72;
static const int FR  = 36;   // face circle radius

// Spiky anime hair — filled triangles + a base rect
static void _drawHair() {
    // Base hair block
    tft.fillRect(FCX - 30, FCY - FR - 10, 60, 14, C_HAIR);

    // 5 spikes: {tip-x-offset-from-centre, tip-y, base-half-width}
    struct { int8_t ox, ty, hw; } spikes[] = {
        {-28, 10,  6},
        {-14,  3,  8},
        {  0, -2, 10},
        { 14,  3,  8},
        { 28, 10,  6},
    };
    int baseY = FCY - FR - 4;
    for (auto& s : spikes) {
        int sx = FCX + s.ox;
        tft.fillTriangle(sx - s.hw, baseY, sx + s.hw, baseY, sx, s.ty, C_HAIR);
        tft.drawLine(sx, s.ty, sx - s.hw, baseY, C_GOLD);
        tft.drawLine(sx, s.ty, sx + s.hw, baseY, C_GOLD);
    }
}

// Reflow full text inside [x, x+maxW] starting at y=startY
// Returns the final y after the last character
static int _reflowText(const String& text, int x, int startY, int maxW,
                        uint16_t color, uint8_t sz = 1) {
    tft.setTextColor(color);
    tft.setTextSize(sz);
    int cw = 6 * sz, lh = 9 * sz;
    int cx = x, cy = startY;
    for (char c : text) {
        if (c == '\n' || cx + cw > x + maxW) { cx = x; cy += lh; }
        if (c == '\n') continue;
        tft.setCursor(cx, cy);
        tft.print(c);
        cx += cw;
    }
    return cy + lh;
}

// ============================================================
//  FACES
// ============================================================
void drawSenkuFace(FaceExpr expr, bool blink) {
    tft.fillScreen(C_BG);

    // ── Hair ─────────────────────────────────────────────────
    _drawHair();

    // ── Face circle ───────────────────────────────────────────
    tft.fillCircle(FCX, FCY, FR, C_SKIN);

    // Ear bumps
    tft.fillCircle(FCX - FR + 2, FCY - 4, 7, C_SKIN);
    tft.fillCircle(FCX + FR - 2, FCY - 4, 7, C_SKIN);

    // Hair covers top of face circle so hair looks attached
    tft.fillRect(FCX - 30, FCY - FR - 4, 60, 10, C_HAIR);

    // ── Eyebrows ─────────────────────────────────────────────
    int browY = FCY - 16;
    switch (expr) {
        case SMUG:   // V-shape / menacing
            tft.drawLine(FCX-22, browY-3, FCX-8, browY+3, C_HAIR);
            tft.drawLine(FCX+ 8, browY+3, FCX+22, browY-3, C_HAIR);
            // second line for thickness
            tft.drawLine(FCX-22, browY-2, FCX-8, browY+4, C_HAIR);
            tft.drawLine(FCX+ 8, browY+4, FCX+22, browY-2, C_HAIR);
            break;
        case TIRED:
            tft.drawLine(FCX-22, browY+2, FCX-8, browY,   C_HAIR);
            tft.drawLine(FCX+ 8, browY,   FCX+22, browY+2, C_HAIR);
            break;
        case EXCITED:
            // High arched brows
            tft.drawLine(FCX-22, browY-2, FCX-8, browY-5, C_HAIR);
            tft.drawLine(FCX+ 8, browY-5, FCX+22, browY-2, C_HAIR);
            tft.drawLine(FCX-22, browY-1, FCX-8, browY-4, C_HAIR);
            tft.drawLine(FCX+ 8, browY-4, FCX+22, browY-1, C_HAIR);
            break;
        default:  // NORMAL — flat slightly inward
            tft.drawLine(FCX-22, browY,   FCX-8, browY-2, C_HAIR);
            tft.drawLine(FCX+ 8, browY-2, FCX+22, browY,  C_HAIR);
            tft.drawLine(FCX-22, browY+1, FCX-8, browY-1, C_HAIR);
            tft.drawLine(FCX+ 8, browY-1, FCX+22, browY+1, C_HAIR);
            break;
    }

    // ── Eyes ─────────────────────────────────────────────────
    int eyeY = FCY - 8;
    if (blink) {
        // Closed — single horizontal line
        tft.drawFastHLine(FCX - 22, eyeY + 4, 16, C_HAIR);
        tft.drawFastHLine(FCX +  6, eyeY + 4, 16, C_HAIR);
    } else if (expr == SMUG) {
        // Left eye: half-closed
        tft.fillRoundRect(FCX-22, eyeY,   16, 12, 3, C_WHITE);
        tft.fillRoundRect(FCX+ 6, eyeY,   16, 12, 3, C_WHITE);
        tft.fillCircle(FCX-14, eyeY+6, 4, C_BG);   // pupil
        tft.fillCircle(FCX+14, eyeY+6, 4, C_BG);
        tft.fillRect(FCX-22, eyeY, 16, 5, C_HAIR);  // heavy lid
        tft.fillRect(FCX+ 6, eyeY, 16, 5, C_HAIR);
        tft.fillCircle(FCX-12, eyeY+4, 1, C_WHITE); // gleam
        tft.fillCircle(FCX+16, eyeY+4, 1, C_WHITE);
    } else {
        // Open eyes — bold white box + pupil
        tft.fillRoundRect(FCX-22, eyeY,   16, 14, 3, C_WHITE);
        tft.fillRoundRect(FCX+ 6, eyeY,   16, 14, 3, C_WHITE);
        tft.fillCircle(FCX-14, eyeY+7, 5, C_BG);
        tft.fillCircle(FCX+14, eyeY+7, 5, C_BG);
        tft.fillCircle(FCX-12, eyeY+5, 2, C_WHITE); // gleam
        tft.fillCircle(FCX+16, eyeY+5, 2, C_WHITE);
        if (expr == EXCITED) {
            tft.drawCircle(FCX-14, eyeY+7, 6, C_ACCENT); // glow ring
            tft.drawCircle(FCX+14, eyeY+7, 6, C_ACCENT);
        }
    }

    // ── Nose ─────────────────────────────────────────────────
    tft.drawPixel(FCX-2, FCY+8, C_HAIR);
    tft.drawPixel(FCX+2, FCY+8, C_HAIR);

    // ── Mouth ────────────────────────────────────────────────
    int mouthY = FCY + 18;
    switch (expr) {
        case EXCITED:
            // Wide open smile
            tft.drawLine(FCX-12, mouthY-2, FCX,     mouthY+4, C_HAIR);
            tft.drawLine(FCX,    mouthY+4, FCX+12,  mouthY-2, C_HAIR);
            tft.drawLine(FCX-12, mouthY-1, FCX,     mouthY+5, C_HAIR);
            tft.drawLine(FCX,    mouthY+5, FCX+12,  mouthY-1, C_HAIR);
            break;
        case SMUG:
            // Side smirk — Senku's signature
            tft.drawLine(FCX-4, mouthY+2, FCX+14, mouthY-2, C_HAIR);
            tft.drawLine(FCX-4, mouthY+3, FCX+14, mouthY-1, C_HAIR);
            tft.drawPixel(FCX+14, mouthY-2, C_HAIR);
            break;
        case TIRED:
            tft.drawFastHLine(FCX-10, mouthY, 20, C_HAIR);
            tft.drawFastHLine(FCX-10, mouthY+1, 20, C_HAIR);
            break;
        default:  // NORMAL — small neutral
            tft.drawLine(FCX-8, mouthY, FCX,    mouthY+3, C_HAIR);
            tft.drawLine(FCX,   mouthY+3, FCX+8, mouthY,  C_HAIR);
            break;
    }

    // ── Status bar ───────────────────────────────────────────
    tft.drawFastHLine(0, 120, 160, C_ACCENT);
    tft.setTextSize(1);
    tft.setTextColor(C_ACCENT);
    tft.setCursor(2, 122);
    tft.print("SENKU");
    tft.setTextColor(C_DIM);
    tft.setCursor(38, 122);
    tft.print("| type query > Serial");
}

void drawSleepFace() {
    tft.fillScreen(C_BG);

    _drawHair();
    tft.fillCircle(FCX, FCY, FR, C_SKIN);
    tft.fillCircle(FCX - FR + 2, FCY - 4, 7, C_SKIN);
    tft.fillCircle(FCX + FR - 2, FCY - 4, 7, C_SKIN);
    tft.fillRect(FCX - 30, FCY - FR - 4, 60, 10, C_HAIR);

    // Closed droopy eyes
    int eyeY = FCY - 8;
    tft.drawLine(FCX-20, eyeY+2, FCX-8, eyeY+6, C_HAIR);
    tft.drawLine(FCX-20, eyeY+3, FCX-8, eyeY+7, C_HAIR);
    tft.drawLine(FCX+ 8, eyeY+6, FCX+20, eyeY+2, C_HAIR);
    tft.drawLine(FCX+ 8, eyeY+7, FCX+20, eyeY+3, C_HAIR);

    // Relaxed flat mouth
    tft.drawFastHLine(FCX-8, FCY+18, 16, C_HAIR);

    // ZZZ
    tft.setTextColor(C_DIM);
    tft.setTextSize(2);
    tft.setCursor(FCX + 22, FCY - 28);
    tft.print("z");
    tft.setTextSize(1);
    tft.setCursor(FCX + 34, FCY - 38);
    tft.print("z");

    tft.drawFastHLine(0, 120, 160, C_DIM);
    tft.setTextColor(C_DIM);
    tft.setTextSize(1);
    tft.setCursor(20, 122);
    tft.print("touch or type to wake");
}

// ============================================================
//  TRANSIENT SCREENS
// ============================================================
void showBoot(const char* msg) {
    tft.fillScreen(C_BG);
    tft.setTextColor(C_ACCENT); tft.setTextSize(1);
    tft.setCursor(4, 4); tft.print("[ SENKU ONLINE ]");
    tft.drawFastHLine(0, 14, 160, C_ACCENT);
    tft.setTextColor(C_WHITE);
    _reflowText(String(msg), 4, 20, 152, C_WHITE);
}

void showQuery(const String& q) {
    tft.fillScreen(C_BG);
    tft.setTextColor(C_GOLD); tft.setTextSize(1);
    tft.setCursor(2, 2); tft.print("YOU:");
    tft.drawFastHLine(0, 12, 160, C_GOLD);
    _reflowText(q, 2, 16, 156, C_WHITE);
    tft.setTextColor(C_ACCENT);
    tft.setCursor(2, 113); tft.print("Thinking...");
}

void showError(const char* msg) {
    tft.fillScreen(C_BG);
    tft.setTextColor(0xF800); tft.setTextSize(1);
    tft.setCursor(4, 4); tft.print("! ERROR");
    tft.drawFastHLine(0, 14, 160, 0xF800);
    _reflowText(String(msg), 2, 20, 156, C_WHITE);
}

void showDone() {
    tft.drawFastHLine(0, 121, 160, C_ACCENT);
    tft.setTextColor(C_DIM); tft.setTextSize(1);
    tft.setCursor(2, 123);
    tft.print("Done  |  2min = new thread");
}

// ============================================================
//  STREAMING DISPLAY
// ============================================================
void streamScreenHeader(const String& q) {
    tft.fillScreen(C_BG);
    tft.setTextColor(C_GOLD); tft.setTextSize(1);
    tft.setCursor(2, 2);
    String qShort = (q.length() > 26) ? q.substring(0, 26) + "..." : q;
    tft.print(qShort);
    tft.drawFastHLine(0, 12, 160, C_ACCENT);
    ss.fullText    = "";
    ss.headerDrawn = true;
}

void appendToken(const String& token) {
    ss.fullText += token;

    // Reflow entire accumulated text from y=16
    tft.fillRect(0, 16, 160, 105, C_BG);
    tft.setTextColor(C_WHITE);
    tft.setTextSize(1);

    const int X0 = 2, MAXX = 158, LH = 9, MAXY = 120;
    int cx = X0, cy = 16;

    for (int i = 0; i < (int)ss.fullText.length(); i++) {
        char c = ss.fullText[i];

        // Word-wrap
        if (c == '\n' || cx + 6 > MAXX) {
            cx = X0; cy += LH;
        }
        if (c == '\n') continue;

        // Screen full — drop first visual line from fullText
        if (cy + LH > MAXY) {
            int lineChars = (MAXX - X0) / 6;
            int drop = 0;
            for (int j = 0; j < (int)ss.fullText.length(); j++) {
                if (ss.fullText[j] == '\n') { drop = j + 1; break; }
                if (j == lineChars)         { drop = j;     break; }
            }
            ss.fullText = ss.fullText.substring(drop);
            // Restart render
            tft.fillRect(0, 16, 160, 105, C_BG);
            cx = X0; cy = 16; i = -1;
            continue;
        }

        tft.setCursor(cx, cy);
        tft.print(c);
        cx += 6;
    }
}
