# SETUP — Live AIS Data Pipeline

Connect the Strait Watch dashboard to real AIS vessel data via Google Sheets.

## Overview

AIS API -> Google Apps Script (scheduled) -> Google Sheet -> Published CSV -> Dashboard fetches CSV

## Step 1: Create the Google Sheet

1. Go to Google Sheets and create a new spreadsheet named "Strait Watch — AIS Feed"
2. In Row 1, add these headers: name, imo, flag, type, status, speed, heading, lat, lng, last_seen

## Step 2: Add the Apps Script

1. In the Sheet, go to Extensions > Apps Script
2. Replace the code with the fetchAIS function that calls your AIS API
3. Save the script

Free AIS API options: AISstream.io, Datalastic, VesselFinder API

## Step 3: Set a Timed Trigger

1. In Apps Script, click the Triggers icon
2. Add Trigger: fetchAIS, Time-driven, Every 5 minutes

## Step 4: Publish the Sheet as CSV

1. File > Share > Publish to web
2. Choose Entire Document > CSV
3. Copy the published URL

## Step 5: Connect the Dashboard

Edit the CONFIG block in strait-watch-dashboard.html:

LIVE_MODE: true
SHEET_CSV_URL: your published CSV URL
REFRESH_MS: 300000

## Advanced: SMS Alerts via Twilio + IFTTT

Add a checkAlert function to Apps Script that triggers an IFTTT webhook when queued vessels exceed 30.
