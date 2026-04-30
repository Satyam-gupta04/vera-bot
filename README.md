# Vera Bot — magicpin AI Challenge

## Approach

I built a smart message composer that generates WhatsApp replies for merchants based on context. It uses a structured 4-context input (merchant details, trigger, category, etc.) and routes each trigger type to a specific prompt template.

The system then creates personalized, human-like messages using real merchant data, category-specific tone, and 10 high-quality reference examples. The goal is to keep responses consistent, relevant, and natural.

##  Architecture

* FastAPI server with 5 endpoints
* Loads 355 merchant contexts into memory at startup for fast access
* Uses deterministic AI generation (temperature = 0) for consistent outputs
* Handles 24 different trigger types with smart routing
* Includes auto-reply detection and smooth intent transitions

## Model

* Claude Sonnet (`claude-sonnet-4-20250514`)

## Tech Stack

* Python
* FastAPI
* Anthropic SDK
