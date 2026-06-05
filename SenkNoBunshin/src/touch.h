#pragma once
#include <Arduino.h>

/**
 * Touch detection task — runs on Core 0.
 * Sets touchWake = true on any valid tap.
 */
void touchTaskCode(void* pv);

// Shared flag: set by touch task, cleared by main loop
extern volatile bool touchWake;
