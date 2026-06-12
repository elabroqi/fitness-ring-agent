# Cova

Cova is a fitness ring that is AI-powered for wellness and rewards platform that connects smart ring activity data to personalized insights and reward recommendations.

The project uses a COLMI smart ring, a Python BLE sync pipeline, MongoDB Atlas, FastAPI, a SwiftUI iOS app, Gemini, Google Cloud Agent Builder, and MongoDB MCP.

## Partner Track

MongoDB

## Features

Cova is a SwiftUI smart-ring rewards app backed by a hosted FastAPI agent API. The iOS app is demonstrated in the video, while the hosted Render URL exposes interactive API docs for judges to test the dashboard, device binding, rewards, and AI agent endpoints.

- Smart ring activity sync from a COLMI ring
- MongoDB Atlas storage for steps, calories, heart rate, SpO2, HRV, stress, rewards, and device metadata
- SwiftUI iOS dashboard for activity, ring status, rewards, and account state
- FastAPI backend for dashboard and device binding APIs
- AI agent that answers user questions using health and reward data
- MongoDB MCP integration for structured agent access to user telemetry
- Gemini and Google Cloud Agent Builder integration for AI reasoning

## Tech Stack

- SwiftUI
- Python
- FastAPI
- MongoDB Atlas
- MongoDB MCP
- Google Gemini
- Google Cloud Agent Builder
- CoreBluetooth
- COLMI R02/R10 BLE client
- Uvicorn

## Architecture

```txt
Smart Ring
↓
Python BLE Sync Service
↓
MongoDB Atlas
↓
FastAPI Backend
↓
SwiftUI iOS App
↓
Gemini + Google Cloud Agent Builder + MongoDB MCP Agent
```

# sync

python ring_client/sync_ring_to_mongo.py --user-id aurela

┌─────────────┐ ┌─────────────────┐ ┌────────────────────────┐
│ iOS Client │ ─────────────► │ FastAPI Backend │ ─────────────► │ Background BLE Worker │
└─────────────┘ (App Opens) └─────────────────┘ (Trigger Sync)└────────────────────────┘
▲ │ │
│ ▼ ▼
└─────────────────────── [MongoDB Atlas] ◄─────────────────────────────┘
(Returns Fresh Data)
