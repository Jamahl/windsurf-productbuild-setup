# AI Dev Crew

A multi-agent system powered by CrewAI that transforms software ideas into complete execution packages.

## Overview

AI Dev Crew uses four specialized AI agents working in sequence to:
1. **Product Discovery Agent** - Gathers requirements through structured Q&A
2. **PRD Improvement Agent** - Refines and optimizes the PRD
3. **Task Breakdown Agent** - Creates granular, testable tasks
4. **System Prompt Generator** - Builds prompts for LLM execution

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
```

3. Run the application:
```bash
python app.py
```

4. Open your browser to `http://localhost:5000`

## Usage

1. Enter your software idea in the text area
2. Click "Generate Development Plan"
3. Wait for the AI agents to process your idea
4. View the generated files:
   - `prd.md` - Product Requirements Document
   - `tasks.md` - Task breakdown
   - `prompt.md` - System prompt for implementation

## Tech Stack

- **Backend**: Python, Flask, CrewAI
- **Frontend**: Vanilla JavaScript, HTML, CSS
- **AI**: OpenAI GPT-4 via LangChain

## Files Generated

- **prd.md**: Complete product requirements with features, tech stack, and scope
- **tasks.md**: Granular development tasks organized by phase
- **prompt.md**: System prompt to guide LLM-based implementation
