from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import json
from crew import run_crew
import threading
import uuid

app = Flask(__name__)
CORS(app)

# Store job status and conversation history
jobs = {}

import logging

def process_idea_prd_only(job_id, user_idea):
    """Start Q&A chat for Product Discovery Agent. Initialize conversation history."""
    try:
        logging.info(f"[Job {job_id}] Starting Product Discovery Agent Q&A for idea: {user_idea}")
        jobs[job_id]['status'] = 'agent_qa'
        jobs[job_id]['message'] = 'Product Discovery Agent is ready to chat.'
        # Initialize conversation: agent asks first question
        conversation_history = [
            {"role": "user", "content": user_idea}
        ]
        from crew import create_product_discovery_task
        task = create_product_discovery_task(conversation_history)
        from crewai import Crew, Process
        crew = Crew(
            agents=[task.agent],
            tasks=[task],
            process=Process.sequential,
            verbose=True
        )
        result = crew.kickoff()
        agent_response = result[0] if isinstance(result, list) and result else str(result)
        conversation_history.append({"role": "agent", "content": agent_response})
        jobs[job_id]['conversation_history'] = conversation_history
        jobs[job_id]['qa_turn'] = True
        jobs[job_id]['qa_last'] = agent_response
        jobs[job_id]['message'] = 'Agent: ' + agent_response
        # If agent_response looks like a PRD (markdown), skip to PRD approval
        if agent_response.strip().lower().startswith('#') or '##' in agent_response:
            with open("prd.md", "w") as f:
                f.write(agent_response)
            jobs[job_id]['status'] = 'awaiting_user_prd_approval'
            jobs[job_id]['result'] = {'prd.md': agent_response}
            jobs[job_id]['message'] = 'PRD generated. Awaiting user approval.'
            jobs[job_id]['qa_turn'] = False
    except Exception as e:
        jobs[job_id]['status'] = 'error'
        jobs[job_id]['message'] = f'Error: {str(e)}'
        jobs[job_id]['error'] = str(e)
        logging.exception(f"[Job {job_id}] Exception during Product Discovery Agent.")

def process_idea_rest(job_id, prd_content):
    """Run the rest of the pipeline after user PRD approval."""
    try:
        logging.info(f"[Job {job_id}] Running remaining agents with approved PRD.")
        jobs[job_id]['status'] = 'processing_rest'
        jobs[job_id]['message'] = 'Continuing with PRD Improvement, Task Breakdown, and Prompt Generator...'
        result = run_crew(None, mode="rest", prd_override=prd_content)
        # Validate and read generated files
        files_content = {}
        required_files = ['prd.md', 'tasks.md', 'prompt.md']
        missing_files = []
        empty_files = []
        for filename in required_files:
            if not os.path.exists(filename):
                missing_files.append(filename)
                logging.error(f"[Job {job_id}] Missing output file: {filename}")
            else:
                with open(filename, 'r') as f:
                    content = f.read()
                    if not content.strip():
                        empty_files.append(filename)
                        logging.error(f"[Job {job_id}] Output file is empty: {filename}")
                    files_content[filename] = content
        if missing_files or empty_files:
            error_message = ""
            if missing_files:
                error_message += f"Missing output files: {', '.join(missing_files)}. "
            if empty_files:
                error_message += f"Empty output files: {', '.join(empty_files)}. "
            jobs[job_id]['status'] = 'error'
            jobs[job_id]['message'] = f'Error: {error_message}Check your agent pipeline and LLM output.'
            jobs[job_id]['error'] = error_message
            logging.error(f"[Job {job_id}] {error_message}")
            return
        jobs[job_id]['status'] = 'completed'
        jobs[job_id]['result'] = {'files': files_content}
        jobs[job_id]['message'] = 'All files generated!'
        logging.info(f"[Job {job_id}] All output files generated and validated.")
    except Exception as e:
        jobs[job_id]['status'] = 'error'
        jobs[job_id]['message'] = f'Error: {str(e)}'
        jobs[job_id]['error'] = str(e)
        logging.exception(f"[Job {job_id}] Exception during rest of pipeline.")

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/process', methods=['POST'])
def process():
    data = request.json
    user_idea = data.get('idea', '')
    if not user_idea:
        return jsonify({'error': 'No idea provided'}), 400
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        'id': job_id,
        'status': 'queued',
        'message': 'Your request has been queued...'
    }
    thread = threading.Thread(target=process_idea_prd_only, args=(job_id, user_idea))
    thread.start()
    return jsonify({'job_id': job_id})

@app.route('/api/agent_qa', methods=['POST'])
def agent_qa():
    data = request.json
    job_id = data.get('job_id')
    user_message = data.get('message')
    if not job_id or not user_message:
        return jsonify({'error': 'Missing job_id or message'}), 400
    if job_id not in jobs:
        return jsonify({'error': 'Invalid job_id'}), 400
    try:
        conversation_history = jobs[job_id].get('conversation_history', [])
        conversation_history.append({"role": "user", "content": user_message})
        from crew import create_product_discovery_task
        task = create_product_discovery_task(conversation_history)
        from crewai import Crew, Process
        crew = Crew(
            agents=[task.agent],
            tasks=[task],
            process=Process.sequential,
            verbose=True
        )
        result = crew.kickoff()
        agent_response = result[0] if isinstance(result, list) and result else str(result)
        conversation_history.append({"role": "agent", "content": agent_response})
        jobs[job_id]['conversation_history'] = conversation_history
        jobs[job_id]['qa_turn'] = True
        jobs[job_id]['qa_last'] = agent_response
        jobs[job_id]['message'] = 'Agent: ' + agent_response
        # If agent_response looks like a PRD (markdown), skip to PRD approval
        if agent_response.strip().lower().startswith('#') or '##' in agent_response:
            with open("prd.md", "w") as f:
                f.write(agent_response)
            jobs[job_id]['status'] = 'awaiting_user_prd_approval'
            jobs[job_id]['result'] = {'prd.md': agent_response}
            jobs[job_id]['message'] = 'PRD generated. Awaiting user approval.'
            jobs[job_id]['qa_turn'] = False
            return jsonify({'status': 'awaiting_user_prd_approval', 'prd': agent_response})
        return jsonify({'status': 'agent_qa', 'message': agent_response})
    except Exception as e:
        jobs[job_id]['status'] = 'error'
        jobs[job_id]['message'] = f'Error: {str(e)}'
        jobs[job_id]['error'] = str(e)
        return jsonify({'error': str(e)}), 500

@app.route('/api/approve_prd', methods=['POST'])
def approve_prd():
    data = request.json
    job_id = data.get('job_id')
    prd_content = data.get('prd_content')
    if not job_id or not prd_content:
        return jsonify({'error': 'Missing job_id or prd_content'}), 400
    if job_id not in jobs:
        return jsonify({'error': 'Invalid job_id'}), 400
    thread = threading.Thread(target=process_idea_rest, args=(job_id, prd_content))
    thread.start()
    return jsonify({'status': 'processing_rest'})

@app.route('/api/status/<job_id>')
def get_status(job_id):
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    return jsonify(jobs[job_id])

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    # Ensure OPENAI_API_KEY is set
    if not os.getenv('OPENAI_API_KEY'):
        print("Warning: OPENAI_API_KEY not set in environment")
    
    app.run(debug=True, port=5000)
