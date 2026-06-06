#pragma once
#include <Arduino.h>

/**
 * GIF player task — runs on Core 0.
 *
 * Fetches frames from GET /senku/gif/{name}/frame/{n}
 * and writes each as a full RGB565 bitmap to the TFT.
 *
 * Control:
 *   gifPlayerSetGif("stare")    — switch GIF immediately
 *   gifPlayerSetGif("")         — pause (blank / no drawing)
 *   gifPlayerStop()             — kill task (call once on shutdown)
 */

// GIFs to cycle through on touch (idle mode)
#define GIF_SLEEP     "senku-sleeping"

// Cycle order for touch
static const char* GIF_CYCLE[] = { "stare", "laugh", "flattered", "savage", "stunned" };
static const int   GIF_CYCLE_LEN = 5;

void gifPlayerStart();
void gifPlayerSetGif(const char* name);  // "" = pause
void gifPlayerCycleNext();               // advance to next GIF in cycle
void gifPlayerStop();

// Internal — do not call directly
void gifPlayerTask(void* pv);
